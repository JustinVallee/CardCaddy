import os
from PIL import Image, ImageFilter
import numpy as np
from skimage import filters

def preprocess_image(image_path, output_path, block_size=31, offset=7):
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
    # Open the image using Pillow
    image = Image.open(image_path)

    # 1. Convert to grayscale
    image = image.convert("L")  # "L" mode is grayscale

    # 2. Reduce noise using a median filter
    image = image.filter(ImageFilter.MedianFilter(size=3))

    # Convert Pillow image to NumPy array for scikit-image
    image_np = np.array(image)

    # 3. Apply adaptive thresholding
    thresh = filters.threshold_local(image_np, block_size=block_size, offset=offset)
    binary = image_np > thresh

    # Convert back to Pillow image
    processed_image = Image.fromarray((binary * 255).astype(np.uint8))

    # Save the processed image
    processed_image.save(output_path)
    print(f"Processed image saved to {output_path}")

# Example usage
# Get the directory where the script is located
script_dir = os.path.dirname(os.path.realpath(__file__))

# Build the full path to the image file
image_name = 'unnamed.jpg'
input_image_path = os.path.join(script_dir, 'images-preprocess-input', image_name)
output_image_path = os.path.join(script_dir, 'images-preprocess-output', 'processed--'+image_name)

preprocess_image(input_image_path, output_image_path)