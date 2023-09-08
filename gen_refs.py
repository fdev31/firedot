#!/bin/env python
import os
import cv2
import numpy as np
from firepoint import create_halftone

# Define the path to the source images and output directory
SOURCE_IMAGE_DIR = "images/"
from testconfig import GENERATED_OUTPUT_DIR as OUTPUT_DIR

# Create the output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Get a list of source images matching "images/ref*.png"
source_images = [file for file in os.listdir(SOURCE_IMAGE_DIR) if file.startswith("ref") and file.endswith(".png")]

# Test options (customize these based on your parameters)
options = {
    # Add other options here
}

# Loop through the source images and generate halftone images
for source_image in source_images:
    input_image_path = os.path.join(SOURCE_IMAGE_DIR, source_image)
    output_image_path = os.path.join(OUTPUT_DIR, source_image.replace(".png", "_output.png"))
    print(f"Generating {output_image_path}")

    # Call the function to generate halftone image
    create_halftone(input_image_path, output_image_path, **options)

print("Halftone images generated successfully.")
