import json
import pytesseract
from PIL import Image
import base64
from io import BytesIO
import re

def lambda_handler(event, context):
    try:
        # Decode the base64 image data from the request body
        body = json.loads(event['body'])
        image_data = body['image']

        # Clean the base64 data (remove newlines)
        #image_data = image_data.replace('\n', '')

        # Decode the image from base64
        #image_bytes = base64.b64decode(image_data)
        #image = Image.open(BytesIO(image_bytes))  # Use Pillow to handle the image data

        # Perform OCR to extract text
        #text = pytesseract.image_to_string(image)

        # Extract numbers from the OCR result using regex
        #numbers = [int(num) for num in re.findall(r'\d+', text)]  # Extract numbers and convert them
        #total = sum(numbers)

        # Return the total sum
        return {
            'statusCode': 200,
            'body': json.dumps({
                'total': image_data
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Error processing image', 'error': str(e)}),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

