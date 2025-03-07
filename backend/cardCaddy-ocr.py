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

def correct_ocr_text(text, confidence=0, confidence_threshold=98.7):
    """Corrects common OCR mistakes if text length is less than 3."""
    corrections = {
        "z": "2", "Z": "2", "A": "4", "n0": "4",
        "s": "5", "S": "5", "$": "5",
        "b": "6", "G": "6",
        "x": "7", ">": "7", "T": "7", "L": "7", "?": "7",
        "00": "8", "OO": "8", "oo": "8", ":": "8", "B": "8",
        "g": "9", "P": "9", "a": "9",
        "I": "11", "II": "11", "l": "11", "ll": "11",
        ")": "11", "(": "11", "))": "11", "((": "11", "()": "11",
        "la": "12"
    }

    text = text.strip()
    if len(text) < 3 and confidence < confidence_threshold:
        return corrections.get(text, text)  # Replace only if exact match
    return text

def sort_textract_table(table, block_dict):
    """ 
        Returns a sorted texract table array of tuples based on the Relationships of textract with no blank columns (Before returning, it calls remove_blank_columns). Each tuple is a row sorted by ColumnIndex.
        eg.
        [
            (1, [cell1, cell2, ...]),  # First row with cells sorted by column index
            (2, [cell3, cell4, ...]),  # Second row, etc.
            ...
        ]
    """

    def remove_blank_columns(sorted_textract_table):
        """Nested func. Takes sorted_textract_table. Returns no_blank_columns_textract_table (same format).
            Removes columns where all cells in the column are empty (no words).
            Returns the table in the same format without blank columns.
        """

        # Determine the number of columns (assuming all rows have the same number of cells)
        num_columns = len(sorted_textract_table[0][1])

        # Track which columns are blank
        is_column_blank = [True] * num_columns  # Assume all columns are blank initially

        # Check each column to see if it's blank
        for col_index in range(num_columns):
            for row_index, row_cells in sorted_textract_table:
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
        no_blank_columns_textract_table = []
        for row_index, row_cells in sorted_textract_table:
            new_row_cells = []
            for col_index, cell in enumerate(row_cells):
                if not is_column_blank[col_index]:  # Only keep non-blank columns
                    new_row_cells.append(cell)
            no_blank_columns_textract_table.append((row_index, new_row_cells))

        return no_blank_columns_textract_table

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

        sorted_no_blank_columns_textract_table = remove_blank_columns(sorted_table)

        return sorted_no_blank_columns_textract_table

    else:
        print("No relationships found for this table.")
        return []

def is_next_3_cells_hole_num(row_cells, block_dict, front_or_back):
    '''Some card have sometimes 2 holes one for the holes and the other for the time need for the hole'''
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
                            cell_text += corrected_text

        if cell_text.strip().isdigit() and int(cell_text.strip()) in hole_nums:
            found_nums_count += 1

    return True if found_nums_count == 3 else False 

def build_table(sorted_table, block_dict, players_names, confidence_threshold=96):
    """Builds a matrix (list of lists) representing the table data and a confidence matrix."""
    hole_keywords = ['Hole', 'Holes', 'Trou', 'Trous', 'Hole number', 'TROU-HOLE']
    par_keywords = ['Par', 'Pars', 'Normale', 'Mens par', 'Par men', 'Par homme', 'Normale / Par', 'Normale-Par']
    found_holes = False
    found_pars = False
    found_players = set()
    suggested_matches = {}  # Format: {player: (best_match_text, best_similarity_score)}
    table_matrix = []
    confidence_matrix = []  # Matrix to track low confidence cells

    for row_index, row_cells in sorted_table:
        keep_row = False
        is_suggested_row = False
        first_cell_row = row_cells[0]  # First cell of the row (header or player name)
        first_cell_text = ''

        # Extract text from the first cell
        if 'Relationships' in first_cell_row:
            for relationship in first_cell_row['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for word_id in relationship['Ids']:
                        word = block_dict.get(word_id)
                        if word and word['BlockType'] == 'WORD':
                            first_cell_text += word['Text'] + ' '
        first_cell_text = first_cell_text.strip()

        # Check for hole and par rows
        if not found_holes:
            if any(keyword.lower().strip() in first_cell_text.lower().strip() for keyword in hole_keywords):
                if is_next_3_cells_hole_num(row_cells, block_dict, 'front'):
                    found_holes = True
                    keep_row = True

        if not found_pars:
            if any(keyword.lower().strip() in first_cell_text.lower().strip() for keyword in par_keywords):
                found_pars = True
                keep_row = True

        # Check for players in the first cell text
        for player in players_names:
            if player.lower().strip() in first_cell_text.lower().strip():
                found_players.add(player)
                keep_row = True
            else:
                # Use fuzzy matching to find the closest match
                similarity = similarity_score(player.lower(), first_cell_text.lower())
                if similarity > 50:  # Threshold for suggesting a match
                    if player not in suggested_matches or similarity > suggested_matches[player][1]:
                        suggested_matches[player] = (first_cell_text, similarity)
                        keep_row = True
                        is_suggested_row = True

        # If the row should be kept, add it to the matrix
        if keep_row:
            row_data = []
            confidence_row = []  # Track low confidence for each cell in this row
            for cell in row_cells:
                cell_text = ''
                low_confidence = False
                if 'Relationships' in cell:
                    for relationship in cell['Relationships']:
                        if relationship['Type'] == 'CHILD':
                            for word_id in relationship['Ids']:
                                word = block_dict.get(word_id)
                                if word and word['BlockType'] == 'WORD':
                                    corrected_text = correct_ocr_text(word['Text'], word.get('Confidence', 100))
                                    cell_text += corrected_text
                                    if word.get('Confidence', 100) < confidence_threshold:
                                        low_confidence = True

                if len(cell_text) > 1:
                    cell_text = correct_ocr_text(cell_text) # for cases where the celltext is 2 words that need to be corrected like (0 0) 

                # Handle special cases for the first cell
                if cell == first_cell_row:
                    if any(keyword.lower().strip() in first_cell_text.lower().strip() for keyword in hole_keywords):
                        cell_text = "Hole"
                    elif any(keyword.lower().strip() in first_cell_text.lower().strip() for keyword in par_keywords):
                        cell_text = "Par"
                    elif is_suggested_row:
                        for player, (match_text, similarity) in suggested_matches.items():
                            if match_text == cell_text.strip():
                                cell_text = player
                                break

                row_data.append(cell_text.strip())
                confidence_row.append(low_confidence)  # Add low confidence flag to the confidence row

            table_matrix.append(row_data)
            confidence_matrix.append(confidence_row)  # Add the confidence row to the confidence matrix

    return table_matrix, confidence_matrix, found_players, suggested_matches

def clean_table(table_matrix):
    """
    Cleans the table matrix by:
    - Ensuring the "Hole" row is first and the "Par" row is second.
    - Removing unnecessary columns (between 9 and 10 if 10 is not immediately after 9, and after 18).
    - Cleaning mixed content in cells:
        - For the first cell of each row, remove digits if present.
        - For all other cells:
            - If the cell is mixed (digits and characters), keep only digits.
            - If the cell contains only characters, replace it with "99".
    """
    if not table_matrix:
        return table_matrix

    # Step 1: Ensure "Hole" and "Par" rows are at the top
    hole_row = None
    par_row = None
    other_rows = []

    for row in table_matrix:
        if "Hole" in row[0]:  # Check if the first cell contains "Hole"
            hole_row = row
        elif "Par" in row[0]:  # Check if the first cell contains "Par"
            par_row = row
        else:
            other_rows.append(row)

    # Ensure "Hole" and "Par" rows are present
    if not hole_row:
        raise ValueError("The table must contain a 'Hole' row.")
    if not par_row:
        raise ValueError("The table must contain a 'Par' row.")

    # Rebuild the table with "Hole" and "Par" rows at the top
    table_matrix = [hole_row, par_row] + other_rows

    # Step 2: Remove unnecessary columns
    # Find the index of "9" and "10" in the "Hole" row
    try:
        index_9 = hole_row.index("9")
        index_10 = hole_row.index("10")
    except ValueError:
        raise ValueError("The 'Hole' row must contain '9' and '10'.")

    # Track indexes to remove
    indexes_to_remove = set()

    # Check if "10" is not immediately after "9"
    if index_10 != index_9 + 1:
        # Add all indexes between "9" and "10" to the removal set
        indexes_to_remove.update(range(index_9 + 1, index_10))

    # Find the index of "18" in the "Hole" row
    try:
        index_18 = hole_row.index("18")
    except ValueError:
        raise ValueError("The 'Hole' row must contain '18'.")

    # Add all indexes after "18" to the removal set
    indexes_to_remove.update(range(index_18 + 1, len(hole_row)))

    # Remove the tracked indexes from all rows in the matrix
    cleaned_matrix = []
    for row in table_matrix:
        cleaned_row = [cell for i, cell in enumerate(row) if i not in indexes_to_remove]
        cleaned_matrix.append(cleaned_row)

    # Step 3: Clean mixed content in cells
    for row in cleaned_matrix:
        for i, cell in enumerate(row):
            # Remove all whitespace from the cell
            cell = ''.join(cell.split())

            if i == 0:  # First cell of the row
                # Remove digits if present
                row[i] = ''.join([char for char in cell if not char.isdigit()])
            else:  # All other cells
                if any(char.isdigit() for char in cell) and any(not char.isdigit() for char in cell):  # Mixed content
                    # Keep only digits
                    row[i] = ''.join([char for char in cell if char.isdigit()])
                elif (not any(char.isdigit() for char in cell)) or (cell.isdigit() and int(cell) > 45):  # Only characters or number higer than 45
                    row[i] = ""

    # Step 4: Hardcode Hole row numbers
    for i in range(1, len(cleaned_matrix[0])):  
        cleaned_matrix[0][i] = i  

    return cleaned_matrix  

# Final Step
def build_html_table(clean_matrix, confidence_matrix, found_players, suggested_matches, players_names):
    """Builds and returns a HTML table from the matrix."""
    
    html = """<div class="table-responsive" style="border-radius:5px"><table class="table table-bordered table-dark"><tbody>"""

    for row_index, row in enumerate(clean_matrix):
        if row_index == 0: 
            tr_style = "--bs-table-bg: #28a745; !important"  # Set green background for HOLE row
        elif row_index == 1:
            tr_style = "--bs-table-bg: #0d6efd; !important"  # Set blue background for PAR row
        else: tr_style = ''
        html += f'<tr style="{tr_style}">'
        for i, cell_text in enumerate(row):
            low_confidence = confidence_matrix[row_index][i] or (str(cell_text).isdigit() and int(cell_text) > 18)
            cell_style = 'color: red;' if (low_confidence and i !=0 and cell_text != "") or cell_text == '1' else ''
            cell_style = 'color: orange;' if cell_text in suggested_matches else cell_style # if suggested player
            cell_style = '' if row_index==0 else cell_style # if hole row, no color text (its harcoded so we dont need low confidence)
            if i == 0:  # First cell, make tr
                if cell_text in ['Hole', 'Par']:
                    html += f"<th><strong>{cell_text.upper()}</strong</th>"
                else:
                    html += f"<th style='{cell_style}'><strong>{cell_text.capitalize()}</strong</th>"
            else:  # Other cells make td
                if row_index==0: # first row (Hole row)
                    html += f"<td style='{cell_style}'>{cell_text}</td>"
                else:
                    html += f"<td style='{cell_style}'><input inputmode='numeric' value='{cell_text}' maxlength='2' placeholder=' ' required/></td>"

        html += "</tr>"

    # Check if all players have been found
    missing_players = set(players_names) - found_players
    if missing_players:
        colspan = len(clean_matrix[0]) if clean_matrix else 1

        # Filter out missing players that have suggestions
        missing_players_without_suggestions = missing_players - set(suggested_matches.keys())

        # Display a warning message only if there are missing players without suggestions
        if missing_players_without_suggestions:
            warning_message = f"<tr><td colspan='{colspan}' style='color: red;'>Players: {', '.join(missing_players_without_suggestions)} were not found. Rewrite the name on the card.</td></tr>"
            html += warning_message

        # Add suggested matches to the warning message (if any)
        suggestions = []
        for player, (match, similarity) in suggested_matches.items():
            if player in missing_players:
                suggestions.append(f"'{match}', {similarity:.0f}% similar to '{player}'")
        
        if suggestions:
            suggestions_message = f"<tr><td colspan='{colspan}' style='color: orange;'>OCR found: {', '.join(suggestions)}</td></tr>"
            html += suggestions_message

    html += """</tbody></table></div>"""
    return html

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

    if len(tables) == 1: # If there's only one table
        sorted_textract_table = sort_textract_table(tables[0], block_dict)
        table_matrix, confidence_matrix, found_players, suggested_matches = build_table(sorted_textract_table, block_dict, players_names)
        cleaned_matrix = clean_table(table_matrix)
        html_table = build_html_table(cleaned_matrix, confidence_matrix, found_players, suggested_matches, players_names)
        return {
            "html_table": html_table
        }

    # If there are multiple tables, merge them
    raw_1st_textract_table = tables[0]
    raw_2nd_textract_table = tables[1]

    # Sort both tables
    sorted_1st_textract_table = sort_textract_table(raw_1st_textract_table, block_dict)
    sorted_2nd_textract_table = sort_textract_table(raw_2nd_textract_table, block_dict)

    # Merge the tables by concatenating rows
    merged_table = merge_tables(sorted_1st_textract_table, sorted_2nd_textract_table)

    # Step 1: Build the table matrix
    table_matrix, confidence_matrix, found_players, suggested_matches = build_table(merged_table, block_dict, players_names)

    # Step 2: Clean the table matrix
    cleaned_matrix = clean_table(table_matrix)

    # Step 3: Generate the HTML table
    html_table = build_html_table(cleaned_matrix, confidence_matrix, found_players, suggested_matches, players_names)

    return {
        "players_names": players_names,
        "Raw table matrix": table_matrix,
        "Cleaned matrix": cleaned_matrix,
        "html_table": html_table
    }

def merge_tables(sorted_first_table, sorted_second_table):
    # Merge the tables horizontally by matching row indices
    merged_table = []
    first_table_rows = {row_index: cells for row_index, cells in sorted_first_table}
    second_table_rows = {row_index: cells for row_index, cells in sorted_second_table}

    # Iterate through all unique row indices
    all_row_indices = set(first_table_rows.keys()).union(set(second_table_rows.keys()))
    for row_index in sorted(all_row_indices):
        # Get cells from the first table (if they exist)
        first_table_cells = first_table_rows.get(row_index, [])
        # Get cells from the second table (if they exist)
        second_table_cells = second_table_rows.get(row_index, [])
        # Combine the cells, appending the second table's cells to the first table's row
        merged_cells = first_table_cells + second_table_cells
        # Add the merged row to the final table
        merged_table.append((row_index, merged_cells))

    return merged_table

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
        result = ocr(bucket, filename, players_list)

        # Return success with CORS headers
        return {
            'statusCode': 200,
            'body': json.dumps({
                'bucket': bucket,
                'filename': filename,
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