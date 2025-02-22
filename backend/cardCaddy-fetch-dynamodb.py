import boto3
import json

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    try:
        table_param = event['pathParameters'].get('table', None) if 'pathParameters' in event else event.get('table', None)
        table = dynamodb.Table(table_param)
        wants_all_players = event['queryStringParameters'].get('want_all_players', None) if 'queryStringParameters' in event else None
        playersNamesOrId = event['queryStringParameters'].get('playersNamesOrId', None) if 'queryStringParameters' in event else event.get('playersNamesOrId', None)
        query = None
        
        if wants_all_players:
            query = get_all_players(table)
            query = json.dumps(query)  # Ensure the dictionary is converted to a JSON string
        elif playersNamesOrId:
            query = get_players_names(table, playersNamesOrId)

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