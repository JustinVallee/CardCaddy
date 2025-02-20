import json
import boto3
import io

def save_image_to_s3(image, bucket_name, filename):
    """Saves an image to S3."""
    byte_stream = io.BytesIO()
    image.save(byte_stream, format='PNG')  # You can change the format (e.g., 'JPEG', 'PNG')
    byte_stream.seek(0)

    s3 = boto3.client('s3')
    s3.put_object(Bucket=bucket_name, Key=filename, Body=byte_stream, ContentType='image/png')

def delete_image_from_s3(bucket_name, filename):
    """Deletes an image from S3 after processing."""
    s3 = boto3.client('s3')
    s3.delete_object(Bucket=bucket_name, Key=filename)

def call_other_lambda(function_name, payload):
    # Set up the client for Lambda
    lambda_client = boto3.client('lambda')
    
    # Invoke LambdaB
    response = lambda_client.invoke(
        FunctionName= function_name,  # Lambda to call
        InvocationType='RequestResponse',  # Synchronous invocation
        Payload=json.dumps(payload) # Payload to send
    )
    
    # Parse the response from LambdaB
    response_payload = json.loads(response['Payload'].read().decode('utf-8'))
    return response_payload

def correct_ocr_text(text, confidence, confidence_threshold=98):
    """Corrects common OCR mistakes in the given text."""
    if len(text) < 3 and confidence < confidence_threshold:
        corrections = {
            "a": "2",
            "la": "12",
            ">": "7",
            "II": "11",
            "I": "1",
            "l": "1",
            ":": "8",
            "S": "5",
            "B": "8",
            "n0": "4"
        }
        
        for mistake, correction in corrections.items():
            text = text.replace(mistake, correction)
        return text
    else:
        return text

def build_html_table(tables, response, players_list, confidence_threshold=97.5):
    """Builds an HTML table based on relationships and detected tables."""
    # Define keywords for holes and par rows
    hole_keywords = ['Hole', 'trous', 'Hole number', 'TROU-HOLE']
    par_keywords = ['Par', 'Normale', 'par men', 'par homme', 'Normale / Par']
    
    html = "<table border='1'>"
    for table in tables:
        if 'Relationships' in table:
            cells = []
            for relationship in table['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for cell_id in relationship['Ids']:
                        cell = next((item for item in response["Blocks"] if item['Id'] == cell_id), None)
                        if cell and cell['BlockType'] == 'CELL':
                            cells.append(cell)

            rows = {}
            for cell in cells:
                row_index = cell.get('RowIndex', 0)
                if row_index not in rows:
                    rows[row_index] = []
                rows[row_index].append(cell)

            sorted_rows = sorted(rows.items(), key=lambda x: x[0])

            # First pass: identify which rows to keep
            rows_to_keep = set()
            for row_index, row_cells in sorted_rows:
                sorted_cells = sorted(row_cells, key=lambda x: x.get('ColumnIndex', 0))
                
                # Check first few cells of each row for identification
                for cell in sorted_cells[:2]:  # Check first two cells
                    cell_text = ''
                    if 'Relationships' in cell:
                        for relationship in cell['Relationships']:
                            if relationship['Type'] == 'CHILD':
                                for word_id in relationship['Ids']:
                                    word = next((item for item in response["Blocks"] if item['Id'] == word_id), None)
                                    if word and word['BlockType'] == 'WORD':
                                        cell_text += word['Text'] + ' '
                    
                    cell_text = cell_text.strip()
                    
                    # Keep row if it matches any criteria
                    if any(keyword.lower() in cell_text.lower() for keyword in hole_keywords):
                        rows_to_keep.add(row_index)
                    elif any(keyword.lower() in cell_text.lower() for keyword in par_keywords):
                        rows_to_keep.add(row_index)
                    elif any(player.lower() in cell_text.lower() for player in players_list):
                        rows_to_keep.add(row_index)

            # Second pass: build HTML only for kept rows
            for row_index, row_cells in sorted_rows:
                if row_index in rows_to_keep:
                    html += "<tr>"
                    sorted_cells = sorted(row_cells, key=lambda x: x.get('ColumnIndex', 0))
                    
                    for cell in sorted_cells:
                        cell_text = ''
                        low_confidence = False
                        
                        if 'Relationships' in cell:
                            for relationship in cell['Relationships']:
                                if relationship['Type'] == 'CHILD':
                                    for word_id in relationship['Ids']:
                                        word = next((item for item in response["Blocks"] if item['Id'] == word_id), None)
                                        if word and word['BlockType'] == 'WORD':
                                            corrected_text = correct_ocr_text(word['Text'], word.get('Confidence', 100))
                                            cell_text += corrected_text + ' '
                                            
                                            if word.get('Confidence', 100) < confidence_threshold:
                                                low_confidence = True

                        # Only apply red color if it's low confidence and length < 3
                        should_mark_red = (
                            low_confidence and 
                            len(cell_text.strip()) < 3
                        )

                        if should_mark_red:
                            html += f"<td style='color: red;'>{cell_text.strip()}</td>"
                        else:
                            html += f"<td>{cell_text.strip()}</td>"
                            
                    html += "</tr>"
        else:
            print("No relationships found for this table.")
            
    html += "</table>"
    return html

def ocr(bucket_name, filename, players_list):
    """Extracts text and tables using AWS Textract from an image stored in S3."""
    # Initialize AWS clients
    s3 = boto3.client('s3')
    textract = boto3.client('textract', region_name="us-east-2")

    # Retrieve image from S3
    try:
        response = s3.get_object(Bucket=bucket_name, Key=filename)
        img_bytes = response["Body"].read()
    except Exception as e:
        print(f"Error retrieving image from S3: {str(e)}")
        return {"error": "Failed to retrieve image from S3"}

    # Perform OCR using Textract
    try:
        response = textract.analyze_document(
            Document={"Bytes": img_bytes},
            FeatureTypes=["TABLES"]
        )
    except Exception as e:
        print(f"Error analyzing document with Textract: {str(e)}")
        return {"error": "Failed to analyze document with Textract"}

    tables = []
    # Extract tables
    for item in response["Blocks"]:
        if item["BlockType"] == "TABLE":
            tables.append(item)
    
    # Build HTML table based on the relationships and table blocks
    html_table = build_html_table(tables, response, players_list)

    return {
        "html_table": html_table
    }

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

        # !!!!!! Call the text detection funciton !!!!!!
        result = ocr(bucket, filename, players_list)

        # Save to dynamo
        '''response_payload = call_other_lambda('cardCaddy-upload-dynamodb',{
            'timestamp': timestamp,
            'condition': condition,
            'round_scores_obj': round_scores_obj
        })'''

        # Return success with CORS headers
        return {
            'statusCode': 200,
            'body': json.dumps({
                'bucket': bucket,
                'filename': filename,
                #'response_payload': response_payload
                'result': result
            }),
            'headers': { # CORS headers
                'Access-Control-Allow-Origin': '*',  # Allow any origin
                'Access-Control-Allow-Methods': 'GET, POST',  # Allow GET and POST methods
                'Access-Control-Allow-Headers': 'Content-Type',  # Allow specific headers
            }
        }
    except Exception as e:
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