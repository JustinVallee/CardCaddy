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
    
def lambda_handler(event, context):
    try:
        # Extract path parameters
        try:
            bucket = event['pathParameters']['bucket']
            filename = event['pathParameters']['filename']
        except KeyError as e:
            return {
                'statusCode': 400,
                'body': f"Error extracting path parameters: {str(e)}",
                'headers': {
                    'Access-Control-Allow-Origin': '*',  # Allow any origin
                    'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
                    'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
                }
            }

        # Validate extracted parameters
        if not bucket or not filename:
            raise ValueError("Missing 'bucket' or 'filename' in the path parameters.")

        # Process the text detection (example placeholder function)
        text_count = detect_text(filename, bucket)
        print("Text detected: " + str(text_count))

        # Return success with CORS headers
        return {
            'statusCode': 200,
            'body': json.dumps({
                'textDetected': text_count,
                'bucket': bucket,
                'filename': filename
            }),
            'headers': {
                'Access-Control-Allow-Origin': '*',  # Allow any origin
                'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
                'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
            }
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)}),
            'headers': {
                'Access-Control-Allow-Origin': '*',  # Allow any origin
                'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
                'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
            }
        }
