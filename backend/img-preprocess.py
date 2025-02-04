"""
Description: This script function is to use in lambda_ocr.py and is a ready version for cloud lambda deployment (accessing the image from the s3 bucket).

Lambda configuration: need a minimum of 512mb of RAM or 1Gb is recommended

"""

import json
import boto3
import io
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import uniform_filter

def preprocess_image(filename, block_size=31, offset=9):
    """
    Preprocesses an image for OCR:
    1. Converts to grayscale
    2. Reduces noise
    3. Applies adaptive thresholding

    Parameters:
        block_size (int): Size of the local neighborhood for adaptive thresholding.
        offset (int): Constant subtracted from the mean for thresholding.

        If the Text is Too Broken or Incomplete:
        -Decrease block_size (e.g., 25) to capture finer details.
        -Decrease offset (e.g., 2) to make the threshold less strict.
        If There's Too Much Background Noise:
        -Increase block_size (e.g., 51) to smooth out local variations.
        -Increase offset (e.g., 10) to make the threshold stricter.
    """
    s3 = boto3.resource('s3')  # Initialize S3 resource
    bucket = s3.Bucket('jv-image-processing-bucket')
    obj_img = bucket.Object(filename)
    response = obj_img.get()
    img_data = response['Body'].read()
    
    # Open image from binary data
    image = Image.open(io.BytesIO(img_data))

    # 1. Convert to grayscale
    image = image.convert("L")  # "L" mode is grayscale
    # 2. Reduce noise using a median filter
    image = image.filter(ImageFilter.MedianFilter(size=3))
    # Convert Pillow image to NumPy array
    image_np = np.array(image)
    # 3. Apply adaptive thresholding
    mean_filter = uniform_filter(image_np, size=block_size)
    binary = image_np > (mean_filter - offset)  # Direct thresholding comparison
    # Convert back to Pillow image
    preprocessed_image = Image.fromarray((binary * 255).astype(np.uint8))

    return preprocessed_image

def save_image_to_s3(image, bucket_name, filename):
    # Save the preprocessed image to a byte stream
    byte_stream = io.BytesIO()
    image.save(byte_stream, format='PNG')  # You can change the format (e.g., 'JPEG', 'PNG')
    byte_stream.seek(0)
    # Initialize S3 client
    s3 = boto3.client('s3')
    # Upload image to S3
    s3.put_object(Bucket=bucket_name, Key=filename, Body=byte_stream, ContentType='image/png')

def delete_image_from_s3(bucket_name, filename):
    """Deletes an image from S3 after processing."""
    s3 = boto3.client('s3')
    s3.delete_object(Bucket=bucket_name, Key=filename)

def lambda_handler(event, context):
    bucket_name = 'jv-image-processing-bucket'
    original_filename = 'IMG_1849.jpg'
    processed_filename = 'processed-'

    # Process the image
    preprocessed_img = preprocess_image(original_filename)
    
    # Save the processed image to S3
    save_image_to_s3(preprocessed_img, bucket_name, processed_filename+original_filename)

    # Delete the original image after processing
    delete_image_from_s3(bucket_name, original_filename)

    return {"statusCode": 200, "body": "Image processed, saved, and original deleted successfully"}