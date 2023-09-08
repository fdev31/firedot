import os
import tempfile

import pytest
import cv2
import numpy as np
from firepoint import create_halftone

from testconfig import TEST_IMAGES_DIR, EXPECTED_OUTPUT_DIR, getOpt

TMP_IMAGE = "testimage.png"

# Create a list of test cases with input images, options, and expected output images

# (source, options, reference)
TEST_CASES: list[tuple[str, dict, str]] = [
    (
        os.path.join(TEST_IMAGES_DIR, name.replace("_output", "")),
        getOpt(name.replace("_output", "")),
        os.path.join(EXPECTED_OUTPUT_DIR, name),
    )
    for name in os.listdir(EXPECTED_OUTPUT_DIR)
    if name.startswith("ref") and name.endswith(".png")
]


@pytest.mark.parametrize("source_image, options, reference_image", TEST_CASES)
def test_create_halftone(source_image, options, reference_image):
    # Call the function to generate halftone image
    create_halftone(source_image, TMP_IMAGE, **options)

    # Perform assertions to check if the generated image matches the expected result
    assert_images_equal(reference_image, TMP_IMAGE)

    # Additional tests
    subtest_output_properties(TMP_IMAGE, options)


# Helper function for comparing images using NumPy and OpenCV
def assert_images_equal(image1_path, image2_path):
    # Load images using cv2
    image1 = cv2.imread(image1_path)
    image2 = cv2.imread(image2_path)

    # Assert image dimensions match
    assert image1.shape == image2.shape, "Image dimensions do not match."

    # Calculate the absolute difference between images
    diff = cv2.absdiff(image1, image2)

    # Ensure that the images are identical (all pixels are black)
    assert np.all(diff == 0), "Images are not identical."


def subtest_output_properties(image_path, options):
    # Load the output image using cv2
    output_image = cv2.imread(image_path)

    # Test that the number of unique colors in the image matches expected
    unique_colors = np.unique(output_image.reshape(-1, 3), axis=0)
    expected_num_colors = options.get(
        "num_colors", 3
    )  # Change "num_colors" to the actual parameter name
    assert (
        len(unique_colors) == expected_num_colors
    ), "Number of unique colors in the image does not match."


# More test functions and assertions can be added as needed

if __name__ == "__main__":
    pytest.main()
