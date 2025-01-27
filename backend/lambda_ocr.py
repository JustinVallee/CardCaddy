import json
import boto3

def detect_text(photo, bucket):
    session = boto3.Session()
    client = session.client('rekognition')

    response = client.detect_text(Image={'S3Object': {'Bucket': bucket, 'Name': photo}})
    textDetections = response['TextDetections']
    print('Detected text\n----------')
    for text in textDetections:
        print('Detected text:' + text['DetectedText'])
        print('Confidence: ' + "{:.2f}".format(text['Confidence']) + "%")
        print('Id: {}'.format(text['Id']))
        if 'ParentId' in text:
            print('Parent Id: {}'.format(text['ParentId']))
        print('Type:' + text['Type'])
        print()
    return len(textDetections)

def Test_detect_text(players_list):
    # Initialize the round scores object with basic information
    round_scores_obj = {
        'par': 72,
        'full': 'yes',
        'holes': [3,4,3,5,5,4,4,5,3,3,4,3,5,5,4,4,5,3],
        'players': []  # This is where you'll store player information
    }
    
    # Loop over the players list to add each player's data
    for player in players_list:
        # Add each player as a dictionary with relevant information
        round_scores_obj['players'].append({
            'player_id': player,  # Player identifier
            'scores': [4,5,3,5,5,4,4,5,3,3,4,3,5,5,4,4,5,3],  # Example scores
            'total_score': 74,  # Example total score
            'handicap': 7,
            'par_avgs': {3: 4, 4: 4, 5: 6}  # Example average par for each hole type
        })
    
    return round_scores_obj

def call_other_lambda(payload):
    # Set up the client for Lambda
    lambda_client = boto3.client('lambda')
    
    # Invoke LambdaB
    response = lambda_client.invoke(
        FunctionName='cardCaddy-upload-dynamodb',  # Lambda to call
        InvocationType='RequestResponse',  # Synchronous invocation
        Payload=json.dumps(payload) # Payload to send
    )
    
    # Parse the response from LambdaB
    response_payload = json.loads(response['Payload'].read().decode('utf-8'))
    return response_payload
    

def lambda_handler(event, context):
    try:
        # Extract path parameters
        try:
            bucket = event['pathParameters']['bucket']
            filename = event['pathParameters']['filename']
            players_list = (event['queryStringParameters']['players']).split(',') # Parse the players
            timestamp = event['queryStringParameters'].get('timestamp', None)  # None if not provided
            condition = event['queryStringParameters'].get('condition', 'Unknown')  # Unknown if not provided

        except KeyError as e:
            return {
                'statusCode': 400,
                'body': f"Error extracting path parameters: {str(e)}",
                'headers': { # CORS headers
                    'Access-Control-Allow-Origin': '*',  # Allow any origin
                    'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
                    'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
                }
            }

        # Validate extracted parameters
        if not bucket or not filename or not players_list:
            raise ValueError("Missing 'bucket' or 'filename' in the path parameters. And must have at leat one player")

        # Call the text detection funciton
        #text_count = detect_text(filename, bucket)
        round_scores_obj = Test_detect_text(players_list)


        response_payload = call_other_lambda({
            'timestamp': timestamp,
            'condition': condition,
            'round_scores_obj': round_scores_obj
        })

        # Return success with CORS headers
        return {
            'statusCode': 200,
            'body': json.dumps({
                'bucket': bucket,
                'filename': filename,
                'response_payload': response_payload
            }),
            'headers': { # CORS headers
                'Access-Control-Allow-Origin': '*',  # Allow any origin
                'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
                'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
            }
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                "error": str(e),
                "Query": event.get('queryStringParameters', 'No query parameters found')
            }),
            'headers': { # CORS headers
                'Access-Control-Allow-Origin': '*',  # Allow any origin
                'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
                'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
            }
        }

