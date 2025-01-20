import pytesseract
import boto3
from PIL import Image
from io import BytesIO

# Initialize S3 client
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    try:
        # Get bucket name and file name from the event
        bucket_name = event['bucket_name']
        image_key = event['file_name']
        
        # Fetch image from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=image_key)
        image_content = response['Body'].read()

        # Load image using PIL
        image = Image.open(BytesIO(image_content))

        # Extract text using pytesseract
        extracted_text = pytesseract.image_to_string(image)

        # Return extracted text
        return {
            'statusCode': 200,
            'body': {
                'extracted_text': extracted_text
            }
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': str(e)
            }
        }
