import boto3
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import re
from boto3.dynamodb.conditions import Key

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Table names
ROUND_TABLE_NAME = "cardcaddy_round"
PLAYER_TABLE_NAME = "cardcaddy_player"
# Connect to DynamoDB tables
ROUND_TABLE = dynamodb.Table(ROUND_TABLE_NAME)
PLAYER_TABLE = dynamodb.Table(PLAYER_TABLE_NAME)

def lambda_handler(event, context):
    try:
        
        # Extract round data from the event
        round_data = event["round_scores_obj"]
        golf_course = event["golf_course"]
        date = event["date"]
        condition = event["condition"]
        
        # Add round_id, timestamp and condition to round_data obj
        round_data["round_id"] = generate_id(ROUND_TABLE_NAME, "round")  # Auto-generated round_id
        round_data["golf_course"] = golf_course
        round_data["date"] = date if date not in [None, ""] else get_date() # Auto-generated timestamp
        round_data["condition"] = condition if condition not in [None, ""] else "Unknown"
        
        # Extract players from round_data
        players = round_data.get("players", [])
        # Update/insert the players into the players table, also updates round_data to add the names
        round_data = update_players_data(players, round_data)

        # Convert all numerical values in round_data to Decimal, dynamo only takes decimals
        round_data = convert_to_decimal(round_data)

        # Insert the round into the round table
        ROUND_TABLE.put_item(Item=round_data)

        return {
            "statusCode": 200,
            "body": {
                "message": "Round and players successfully populated!",
                "round_data": round_data
            },
            'headers': { # CORS headers
            'Access-Control-Allow-Origin': '*',  # Allow any origin
            'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
            'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
            }
        }
    
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": f"In uploadDynamo - An error occurred: {e}",
            'headers': { # CORS headers
                'Access-Control-Allow-Origin': '*',  # Allow any origin
                'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
                'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
            }
        }

def update_players_data(players, round_data):
# Insert each player into the Player table
    for index, player in enumerate(players):
        existing_player = True if player.get("player_id").startswith("player_") else False
        
        # Get the player_id
        player_id = player.get("player_id") if existing_player else generate_id(PLAYER_TABLE_NAME, "player")
        name = player.get("player_id") if not existing_player else get_player_name(player_id)
        
        if not existing_player: round_data["players"][index]["player_id"] = player_id

        round_data["players"][index]["name"] = name
        
        parAvgs = convert_to_decimal(player["par_avgs"])

        round_handicap = round_data["players"][index]["handicap"]

        # UPDATE db
        if existing_player:
            player_item = {
                "player_id": player_id,  # Primary key
                "total_score": calculate_avg_score(player_id, player["total_score"]),
                "handicap": calculate_avg_handicap(player_id, round_handicap), 
                "par_avgs": calculate_avg_pars(player_id, parAvgs)
            }
            PLAYER_TABLE.update_item(
                    Key={"player_id": player_item["player_id"]},
                    UpdateExpression="""
                        set #average_score = :average_score,
                            #average_pars = :average_pars,
                            #handicap = :handicap,
                            #rounds_played = list_append(#rounds_played, :new_round)
                    """,
                    ExpressionAttributeNames={
                        "#average_score": "average_score",
                        "#average_pars": "average_pars",
                        "#handicap": "handicap",
                        "#rounds_played": "rounds_played",
                    },
                    ExpressionAttributeValues={
                        ":average_score": player_item["total_score"],
                        ":average_pars": player_item["par_avgs"],
                        ":handicap": player_item["handicap"],
                        ":new_round": [round_data["round_id"]],  # Current round being passed
                    },
                )
        else:
            player_item = {
                "player_id": player_id,  # Primary key
                "cognito_id": str(uuid.uuid4()),  # Auto-generated UUID for Cognito ID
                "name": name,  # Player's name
                "average_score": player["total_score"],
                "average_pars":  convert_to_decimal(player["par_avgs"]),
                "handicap": round_handicap, 
                "rounds_played": [round_data["round_id"]]

            }
            # Insert the player into the Player table
            PLAYER_TABLE.put_item(Item=player_item)

    return round_data

def get_player_name(player_id):
    return PLAYER_TABLE.get_item(Key={'player_id': player_id})['Item']['name']

def generate_id(table_name, prefix):
    # Add a check for whether the table is 'round' to use a unique ID for each round
    if table_name == ROUND_TABLE_NAME:
        partition_key = "round_id"
        prefix = "round_"  # Keep the prefix for round IDs
    elif table_name == PLAYER_TABLE_NAME:
        partition_key = "player_id"
        prefix = "player_"
    else:
        raise ValueError(f"Unknown table name: {table_name}")

    # Scan the table for all items with the given partition key
    response = dynamodb.Table(table_name).scan(
        FilterExpression=Key(partition_key).begins_with(prefix),  # Ensure you're filtering by prefix
        ProjectionExpression=partition_key
    )

    # Extract all existing IDs and determine the next available round number
    if 'Items' not in response or not response['Items']:
        return f"{prefix}001"

    ids = [item[partition_key] for item in response.get("Items", [])]

    numeric_parts = []
    for item_id in ids:
        match = re.match(rf"{prefix}(\d+)", item_id)  # Extract the number from the ID
        if match:
            numeric_parts.append(int(match.group(1)))
    
    next_number = max(numeric_parts, default=0) + 1  # Increment the largest number
    return f"{prefix}{next_number:03}"

def get_date():
    current_time = datetime.now() # Get the current time
    eastern_time = current_time - timedelta(hours=5) # Subtract 5 hours to adjust for Eastern Standard Time (EST)
    return eastern_time.strftime('%Y-%m-%d %H:%M:%S')  # Format the datetime as a string

def convert_to_decimal(data):
    """
    Recursively converts all float values in a nested dictionary or list to Decimal.
    """
    if isinstance(data, dict):
        return {k: convert_to_decimal(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_decimal(i) for i in data]
    elif isinstance(data, float):  # Convert float to Decimal
        return Decimal(str(data))
    else:
        return data
    
def get_all_values_of_attribute_round(player_id, attribute):
    """
    Retrieve all values of a specific attribute (e.g., total_score, par_avgs) for all rounds played by a player.
    """

    # Fetch the rounds played by the player
    response = PLAYER_TABLE.get_item(Key={'player_id': player_id})
    if 'Item' not in response:
        raise ValueError(f"Player with ID {player_id} not found.")

    rounds_played = response['Item'].get('rounds_played', [])

    # Fetch the attribute value for each round and store in a list
    all_values_asked = []
    for round_id in rounds_played:
        round_data = ROUND_TABLE.get_item(Key={'round_id': round_id})
        if 'Item' not in round_data:
            print(f"Round with ID {round_id} not found. Skipping.")
            continue

        # Iterate through the players in the round data
        players_in_round = round_data['Item'].get('players', [])
        for player in players_in_round:
            if player.get('player_id') == player_id:
                # Found the player, now get the attribute
                if attribute in player:
                    all_values_asked.append(player[attribute])
                else:
                    print(f"Attribute {attribute} not found for player {player_id} in round {round_id}")  # Debugging
                break  # Stop searching for this player in this round

    #print(f"All values for {attribute}: {all_values_asked}")  # Debugging
    return all_values_asked

def calculate_avg_score(player_id, current_round_score):
    """
    Calculate the average score for a player, including the current round's score.
    """
    # Get all scores for the player
    all_scores = get_all_values_of_attribute_round(player_id, "total_score")

    # Add the current round's score to the list
    all_scores.append(current_round_score)

    # Calculate the average score
    avg_score = sum(all_scores) / len(all_scores)
    avg_score = convert_to_decimal(avg_score)
    avg_score = int(round(avg_score))
    return avg_score

def calculate_avg_pars(player_id, current_round_avg_pars):
    """
    Calculate the average par scores for a player, including the current round's par averages.
    """
    try:
        # Get all par averages for the player
        all_par_avgs = get_all_values_of_attribute_round(player_id, "par_avgs")

        # Add the current round's par averages to the list
        all_par_avgs.append(current_round_avg_pars)

        # Calculate the average for each par type (3, 4, 5)
        par_avgs = {"3": 0, "4": 0, "5": 0}
        count = {"3": 0, "4": 0, "5": 0}

        for par_avg in all_par_avgs:
            for par_type in par_avg:
                try:
                    value = float(par_avg[par_type])
                    par_avgs[par_type] += value
                    count[par_type] += 1
                except (KeyError, ValueError) as e:
                    print(f"Invalid value for par_type {par_type}: {par_avg[par_type]}")
                    continue

        # Calculate the average for each par type
        for par_type in par_avgs:
            if count[par_type] > 0:
                par_avgs[par_type] = round(par_avgs[par_type] / count[par_type],1)

        par_avgs = convert_to_decimal(par_avgs)
        return par_avgs

    except Exception as e:
        print(f"Error in calculate_avg_pars: {e}")
        raise  # Re-raise the exception after logging it

def calculate_avg_handicap(player_id, round_handicap):

    # Get all existing handicaps for the player
    all_handicaps = get_all_values_of_attribute_round(player_id, "handicap")

    # Add the current round's handicap to the list
    all_handicaps.append(round_handicap)

    # Calculate the average handicap
    avg_handicap = round(sum(all_handicaps) / len(all_handicaps),1)
    return avg_handicap
