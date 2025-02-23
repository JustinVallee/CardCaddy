import json
import boto3
import io

# Fuzzy matching functions to get the closet player names
def levenshtein_distance(s1, s2):
    """Calculate the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def similarity_score(s1, s2):
    """Calculate the similarity score between two strings as a percentage."""
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 100  # Both strings are empty
    distance = levenshtein_distance(s1, s2)
    return (1 - distance / max_len) * 100
# End of Fuzzy funcs

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

def sort_response_table(table, block_dict):
    """
        Returns a sorted table array of tuples. Each tuple is a row sorted by ColumnIndex.
        eg.
        [
            (1, [cell1, cell2, ...]),  # First row with cells sorted by column index
            (2, [cell3, cell4, ...]),  # Second row, etc.
            ...
        ]
    """

    if 'Relationships' in table:  # Ensure the table has relationships
        cells = []
        for relationship in table['Relationships']:  
            if relationship['Type'] == 'CHILD':
                for cell_id in relationship['Ids']:
                    cell = block_dict.get(cell_id)
                    if cell and cell['BlockType'] == 'CELL':  
                        cells.append(cell)

        rows = {}
        for cell in cells:  
            row_index = cell.get('RowIndex', 0)
            if row_index not in rows:
                rows[row_index] = []
            rows[row_index].append(cell)

        # Sort rows
        sorted_rows = sorted(rows.items(), key=lambda x: x[0])  

        sorted_table = []  # Store all sorted rows properly
        for row_index, row_cells in sorted_rows:  
            sorted_cells = sorted(row_cells, key=lambda x: x.get('ColumnIndex', 0))
            sorted_table.append((row_index, sorted_cells))  # Append tuple (row_index, sorted row)

        no_bank_column_table = remove_blank_columns(sorted_table)

        return no_bank_column_table

    else:
        print("No relationships found for this table.")
        return []

def remove_blank_columns(sorted_table):
    """Takes sorted_table
    [
        (1, [cell1, cell2, ...]),  # First row with cells sorted by column index
        (2, [cell3, cell4, ...]),  # Second row, etc.
        ...
    ]
    Removes columns where all cells in the column are empty (no words).
    Returns the table in the same format without blank columns.
    """

    # Determine the number of columns (assuming all rows have the same number of cells)
    num_columns = len(sorted_table[0][1])

    # Track which columns are blank
    is_column_blank = [True] * num_columns  # Assume all columns are blank initially

    # Check each column to see if it's blank
    for col_index in range(num_columns):
        for row_index, row_cells in sorted_table:
            if col_index < len(row_cells):  # Ensure the column exists in this row
                cell = row_cells[col_index]
                if 'Relationships' in cell:
                    # Check if the cell has any words
                    for relationship in cell['Relationships']:
                        if relationship['Type'] == 'CHILD':
                            is_column_blank[col_index] = False  # Column is not blank
                            break
                    if not is_column_blank[col_index]:
                        break  # No need to check further rows for this column

    # Create a new table without blank columns
    no_blank_column_table = []
    for row_index, row_cells in sorted_table:
        new_row_cells = []
        for col_index, cell in enumerate(row_cells):
            if not is_column_blank[col_index]:  # Only keep non-blank columns
                new_row_cells.append(cell)
        no_blank_column_table.append((row_index, new_row_cells))

    return no_blank_column_table

def rearrange_table(html):
    """
    Rearranges the HTML table to ensure the "Hole" row is first and the "Par" row is second.
    """
    # Find the start and end of the <tbody> section
    start = html.find("<tbody>") + len("<tbody>")
    end = html.find("</tbody>")
    tbody_content = html[start:end]

    # Split the rows
    rows = tbody_content.split("</tr>")
    rows = [row.strip() for row in rows if row.strip()]

    # Separate "Hole", "Par", and other rows
    hole_row = None
    par_row = None
    other_rows = []

    for row in rows:
        if "Hole" in row:
            hole_row = row + "</tr>"
        elif "Par" in row:
            par_row = row + "</tr>"
        else:
            other_rows.append(row + "</tr>")

    # Rebuild the tbody content
    new_tbody_content = ""
    if hole_row:
        new_tbody_content += hole_row
    if par_row:
        new_tbody_content += par_row
    new_tbody_content += "".join(other_rows)

    # Rebuild the full HTML
    updated_html = html[:start] + new_tbody_content + html[end:]
    return updated_html

def is_next_3_cells_hole_num(row_cells, block_dict, front_or_back):
    hole_nums = [1, 2, 3] if front_or_back.lower() == "front" else [10, 11, 12]
    found_nums_count = 0

    for cell in row_cells[1:4]:  # look if the cells next to the hole is 1,2,3 (Some card have to rows holes)
        cell_text = ''
        if 'Relationships' in cell:
            for relationship in cell['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for word_id in relationship['Ids']:
                        word = block_dict.get(word_id)
                        if word and word['BlockType'] == 'WORD':
                            corrected_text = correct_ocr_text(word['Text'], word.get('Confidence', 100))
                            cell_text += corrected_text + ' '

        if cell_text.strip().isdigit() and int(cell_text.strip()) in hole_nums:
            found_nums_count += 1

    return True if found_nums_count == 3 else False 

def build_html_table(sorted_table, block_dict, players_names, confidence_threshold=97.5):
    """Builds an HTML table based on relationships and detected tables."""
    hole_keywords = ['Hole', 'Holes', 'Trou', 'Trous' 'Hole number', 'TROU-HOLE']
    found_holes = False
    par_keywords = ['Par', 'Pars', 'Normale', 'Par men', 'Par homme', 'Normale / Par', 'Normale-Par']
    found_pars = False
    # Initialize a set to track found players
    found_players = set()
    # Initialize a dictionary to track suggested matches
    suggested_matches = {}  # Format: {player: (best_match_text, best_similarity_score)}

    html = """<div class="table-responsive"><table class="table table-bordered table-dark"><tbody>"""

    for row_index, row_cells in sorted_table:
        # Check if the row should be kept
        keep_row = False
        is_suggested_row = False  # Flag to track if the row is kept due to a suggested match
        first_cell_row = row_cells[0] # Considering the first cell of the row is the column header

        first_cell_text = ''
        if 'Relationships' in first_cell_row:
            for relationship in first_cell_row['Relationships']:  # Loop over relationships in the first cell
                if relationship['Type'] == 'CHILD':
                    for word_id in relationship['Ids']:  # Loop over word IDs in each relationship
                        word = block_dict.get(word_id)
                        if word and word['BlockType'] == 'WORD':
                            first_cell_text += word['Text'] + ' '  # Append the OCR text from each word

        first_cell_text = first_cell_text.strip()
        print("DEBUG- cell text: ", first_cell_text)

        if not found_holes:
            if any(keyword.lower().strip() in first_cell_text.lower().strip() for keyword in hole_keywords):
                if is_next_3_cells_hole_num(row_cells,block_dict,'front'):
                    found_holes = True
                    keep_row = True

        if not found_pars:
            if any(keyword.lower().strip() in first_cell_text.lower().strip() for keyword in par_keywords):
                found_pars = True
                keep_row = True

        # Check for players in the first cell text
        for player in players_names:
            if player.lower().strip() in first_cell_text.lower().strip():
                found_players.add(player)  # Add the player to the found set
                keep_row = True
            else:
                # Use custom fuzzy matching to find the closest match
                similarity = similarity_score(player.lower(), first_cell_text.lower())
                if similarity > 50:  # Threshold for suggesting a match
                    # Track the best suggestion for each player
                    if player not in suggested_matches or similarity > suggested_matches[player][1]:
                        suggested_matches[player] = (first_cell_text, similarity)
                        keep_row = True
                        is_suggested_row = True  # Mark this row as a suggested match

        # If the row should be kept, build its HTML
        if keep_row:
            html += "<tr>"
            for cell in row_cells[:10]:  # Keep only the first 10 columns
                cell_text = ''
                low_confidence = False
                if 'Relationships' in cell:
                    for relationship in cell['Relationships']:
                        if relationship['Type'] == 'CHILD':
                            for word_id in relationship['Ids']:
                                word = block_dict.get(word_id)
                                if word and word['BlockType'] == 'WORD':
                                    corrected_text = correct_ocr_text(word['Text'], word.get('Confidence', 100))
                                    cell_text += corrected_text + ' '

                                    if word.get('Confidence', 100) < confidence_threshold:
                                        low_confidence = True

                make_red = low_confidence and len(cell_text.strip()) < 3

                if cell == first_cell_row:
                    if any(keyword.lower().strip() in first_cell_text.lower().strip() for keyword in hole_keywords):
                        cell_text = "Hole"
                    elif any(keyword.lower().strip() in first_cell_text.lower().strip() for keyword in par_keywords):
                        cell_text = "Par"
                    elif is_suggested_row:
                        # Find the player associated with the current cell_text
                        for player, (match_text, similarity) in suggested_matches.items():
                            if match_text == cell_text.strip():  # Check if the current cell_text matches the suggested match
                                cell_text = player  # Set cell_text to the player's name
                                break
                    cell_style = "color: orange;" if is_suggested_row else ""
                    html += f"<th contenteditable='true' style='{cell_style}'>{cell_text.strip()}</th>"
                    continue
                if make_red or not cell_text.strip().isdigit():
                    html += f"<td contenteditable='true' style='color: red;'>{cell_text.strip()}</td>"
                    continue
                elif cell_text.strip():  # Only create <td> if text is not empty
                    html += f"<td contenteditable='true'>{cell_text.strip()}</td>"

            html += "</tr>"

    # Check if all players have been found
    missing_players = set(players_names) - found_players
    if missing_players:
        warning_message = f"<tr><td colspan='10' style='color: red;'>Issue: The following players were not found: {', '.join(missing_players)}</td></tr>"
        html += warning_message

        # Add suggested matches to the warning message
        if suggested_matches:
            suggestions = []
            for player, (match, similarity) in suggested_matches.items():
                if player in missing_players:  # Only suggest for missing players
                    suggestions.append(f"'{match}', {similarity:.0f}% similar to '{player}'")
            if suggestions:
                suggestions_message = f"<tr><td colspan='10' style='color: orange;'>OCR found: {', '.join(suggestions)}</td></tr>"
                html += suggestions_message

    html += "</tbody></table></div>"
    html_rearrange = rearrange_table(html)
    return html_rearrange

def ocr(bucket_name, filename, players_list):
    """Extracts text and tables using AWS Textract from an image stored in S3."""
    # Initialize AWS clients
    s3 = boto3.client('s3')
    textract = boto3.client('textract', region_name="us-east-2")
    response_payload_players = call_other_lambda('cardCaddy-fetch-dynamodb', {'table':'cardcaddy_player','playersNamesOrId': players_list})
    players_names = response_payload_players['body']

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
    
    block_dict = {block['Id']: block for block in response["Blocks"]} # Extract Blocks from response, see https://docs.aws.amazon.com/textract/latest/dg/how-it-works-document-layout.html#hows-it-works-blocks-types.title

    tables = [block for block in block_dict.values() if block["BlockType"] == "TABLE"]

    html_tables = []
    # Build HTML tables based on the relationships and table blocks
    for table in tables:
        sorted_table = sort_response_table(table, block_dict)
        html_table = build_html_table(sorted_table, block_dict, players_names)
        html_tables.append(html_table)  # Append each HTML table to the list

    html_tables_str = "".join(html_tables)

    return {
        "html_table": html_tables_str
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