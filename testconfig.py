import os

# Define the path to the test images and expected output directory
TEST_IMAGES_DIR = "images/"
EXPECTED_OUTPUT_DIR = "expected_output/"
GENERATED_OUTPUT_DIR = "generated_output/"

# Create the output directory if it doesn't exist
os.makedirs(GENERATED_OUTPUT_DIR, exist_ok=True)
os.makedirs(EXPECTED_OUTPUT_DIR, exist_ok=True)

RUN_OPTIONS = {
    "ref.png": {"output_width": 700, "randomize": False, "spread": False},
    "ref2.png": {"output_width": 700, "randomize": False},
    "ref3.png": {"output_width": 700},
}


def getOpt(name):
    return RUN_OPTIONS.get(name, {})
