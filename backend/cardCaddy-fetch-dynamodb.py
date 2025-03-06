import boto3
import json

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Connect to DynamoDB tables
ROUND_TABLE = dynamodb.Table("cardcaddy_round")
PLAYER_TABLE = dynamodb.Table("cardcaddy_player")

def lambda_handler(event, context):
    try:
        table_param = event['pathParameters'].get('table', None) if 'pathParameters' in event else event.get('table', None)
        table = dynamodb.Table(table_param)
        wants_all_players = event['queryStringParameters'].get('want_all_players', None) if 'queryStringParameters' in event else None
        playersNamesOrId = event['queryStringParameters'].get('playersNamesOrId', None) if 'queryStringParameters' in event else event.get('playersNamesOrId', None)

        playerId = event['queryStringParameters'].get('playerId', None) if 'queryStringParameters' in event else None
        all_players_stats = event['queryStringParameters'].get('get_all_players_stats', None) if 'queryStringParameters' in event else None
        individual_all_stats = event['queryStringParameters'].get('get_individual_all_stats', None) if 'queryStringParameters' in event else None

        query = None
        if wants_all_players:
            query = get_all_players(table)
            query = json.dumps(query)  # Ensure the dictionary is converted to JSON string
        elif playersNamesOrId:
            query = get_players_names(table, playersNamesOrId)
        elif all_players_stats:
            query = get_all_players_stats(table) # this needs to be the players table
            query = json.dumps(query, default=str)  # Dictionary converted to JSON string and default str because it has Decimals
        elif individual_all_stats:
            if playerId:
                query = get_individual_all_stats(table, playerId) # table is round
            else: 
                query = "Need playerID"

        return {
            "statusCode": 200,
            "body": query,
            'headers': {  # CORS headers
                'Access-Control-Allow-Origin': '*',  # Allow any origin
                'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
                'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
            }
            
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": f"An error occurred: {e}",
            'headers': {  # CORS headers
                'Access-Control-Allow-Origin': '*',  # Allow any origin
                'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
                'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
            }
        }

def get_all_players(table):
    # Scan the DynamoDB table to get player_id and name
    response = table.scan(
        ProjectionExpression="player_id, #name",  # Use an alias for 'name'
        ExpressionAttributeNames={
            "#name": "name"  # Map the alias to the actual reserved keyword 'name'
        }
    )
    players_list = response['Items']  # Get the list of player items
    # Convert to a dictionary with player_id as the key and name as the value
    players_dict = {player['player_id']: player['name'] for player in players_list}

    return players_dict

def get_players_names(table, players_list):
    players_names = []
    for player in players_list:
        print('Player',player)
        if player.startswith("player_"):
            players_names.append(table.get_item(Key={'player_id': player})['Item']['name'])
        else:
            players_names.append(player)

    return players_names

def get_all_players_stats(table):
    # Scan the DynamoDB table to get player_id, name, and additional stats
    response = table.scan(
        ProjectionExpression="player_id, #name, average_score, handicap, average_pars, rounds_played",  # Include all desired fields
        ExpressionAttributeNames={
            "#name": "name"  # Map the alias to the actual reserved keyword 'name'
        }
    )
    
    players_list = response['Items']  # Get the list of player items
    
    # Convert to a dictionary with player_id as the key and a dictionary of stats as the value
    players_stats_dict = {
        player['player_id']: {
            "name": player.get('name', 'N/A'),  # Use .get() to handle missing fields gracefully
            "average_score": player.get('average_score', 'N/A'),
            "handicap": player.get('handicap', 'N/A'),
            "average_pars": player.get('average_pars', {}),  # Default to empty if missing
            "rounds_played": player.get('rounds_played', [])  # Default to empty if missing
        }
        for player in players_list
    }

    return players_stats_dict

def get_player_rounds(playerID):
    return PLAYER_TABLE.get_item(Key={'player_id': playerID})['Item']['rounds_played']

def get_individual_all_stats(table, playerID):
    rounds_ids = get_player_rounds(playerID)  # Fetch all round IDs for the player

    rounds_info = []
    for round_id in rounds_ids:
        response = table.get_item(Key={'round_id': round_id})
        
        if 'Item' in response:
            round_data = response['Item']

            # Extract the relevant data
            round_entry = {
                'round_id': round_data['round_id'],
                'golf_course': round_data['golf_course'],
                'player_stats': None  # Placeholder
            }

            # Filter the players list to keep only the matching playerID
            players = round_data.get('players', [])  # Get players list safely
            for player in players:
                if player.get('player_id') == playerID:
                    round_entry['player_stats'] = player  # Store player's data
                    break  # Stop searching once the player is found

            rounds_info.append(round_entry)

    return rounds_info