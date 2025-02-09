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

def ocr(bucket_name, filename):
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
    response = textract.analyze_document(
        Document={"Bytes": img_bytes},
        FeatureTypes=["TABLES"]
    )

    extracted_data = []
    tables = []

    print("\n### 🏌️ DETECTED TEXT (With Confidence) ###\n")

    for item in response["Blocks"]:
        if item["BlockType"] == "LINE":
            text = item["Text"]
            confidence = item["Confidence"]

            # Auto-correct common OCR mistakes
            text = text.replace("a", "2").replace("la", "12").replace("n0", "4")\
                       .replace(">", "7").replace("II", "11").replace(":", "8")\
                       .replace("S", "5").replace("B", "8")

            extracted_data.append((text, confidence))

        elif item["BlockType"] == "TABLE":
            tables.append(item)

    # Print extracted text
    print("\n| Detected Text | Confidence |")
    print("|--------------|------------|")
    for text, conf in extracted_data:
        print(f"| {text:<12} | {conf:.1f}%  |")

    # Print extracted tables
    if tables:
        print("\n### 📊 DETECTED TABLES ###\n")
        for table in tables:
            print(json.dumps(table, indent=2))

    return {
        "text": extracted_data,
        "tables": tables
    }

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    bucket_name = 'jv-image-processing-bucket'
    filename = event.get("filename")

    if not filename:
        return {"statusCode": 400, "body": "Filename is required"}

    result = ocr(bucket_name, filename)
    return {"statusCode": 200, "body": json.dumps(result)}