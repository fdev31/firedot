#!/bin/env python
import math
import random
import argparse
import itertools

import cv2
import numpy as np

# grey pixels will be multiplied by this factor (1.0 = disabled)
ANTIALIASED_DARKENING = 1.0

default_values = {
    "downscale_factor": 1,
    "gamma": 1.0,
    "multiply": 1.0,
    "no-randomize": False,
    "no-spread": False,
    "no-dots": False,
    "max_diameter": 4,
    "spread_size": 2,
    "width": None,
    "use_squares": False,
    "normalize": 0.0,
    "sharpen": 0.5,
    "threshold": 30,
    "hypersample": 3.0,
}


def spread_dots(circle_radius, spread_size): # {{{
    height, width = circle_radius.shape
    for y in range(0, height, spread_size):
        for x in range(0, width, spread_size):
            block = circle_radius[y : y + spread_size, x : x + spread_size].ravel()
            coordinates = [
                (cx, cy)
                for cy in range(y, y + spread_size)
                for cx in range(x, x + spread_size)
            ]
            remain = 0.0
            for b in block:
                if b == -1:
                    continue
                remain += b - int(b)
            random.shuffle(coordinates)
            coord_iter = itertools.cycle(coordinates)
            while remain > 1:
                cx, cy = next(coord_iter)
                try:
                    if circle_radius[cy, cx] == -1:
                        continue
                except IndexError:
                    continue
                remain -= 1
                circle_radius[cy, cx] += 1
# }}}

def draw_circles(img, radiuses, max_diameter, randomize, use_squares): # {{{
    height, width = radiuses.shape

    offset = max_diameter // 2
    y_coords, x_coords = np.where(radiuses > 0.0)
    for y, x in zip(y_coords, x_coords):
        circle_radius = radiuses[y, x]
        pos = (int(x * max_diameter + offset), int(y * max_diameter + offset))
        if circle_radius > 0:
            # randomize positions
            rpos = (
                [
                    int(
                        float(i)
                        + ((max_diameter - circle_radius) * (random.random() - 0.4))
                    )
                    for i in pos
                ]
                if randomize
                else pos
            )
            if use_squares:
                cv2.rectangle(
                    img,
                    rpos,
                    [int(p + circle_radius) for p in rpos],
                    0,
                    thickness=-1,
                )
            else:
                cv2.circle(
                    img,
                    rpos,
                    int(math.sqrt(circle_radius**2)),
                    0,
                    thickness=-1,
                    lineType=cv2.LINE_AA,
                )
# }}}

def mean_removal(image, kernel_size=3, strength=1.0): # {{{
    """
    Apply mean removal filter to an input image.

    Args:
        image (numpy.ndarray): The input image (should be grayscale).
        kernel_size (int): Size of the neighborhood for local mean calculation.
        strength (float): Strength of the mean removal effect (0.0 to 1.0).

    Returns:
        numpy.ndarray: The processed image with mean removal applied.
    """
    if len(image.shape) == 3:
        raise ValueError("Input image should be grayscale.")

    # Ensure kernel_size is odd for proper local mean calculation
    if kernel_size % 2 == 0:
        kernel_size += 1

    # Apply the mean removal filter
    mean_kernel = np.ones((kernel_size, kernel_size), dtype=np.float32) / (
        kernel_size**2
    )
    mean_removed_image = cv2.filter2D(image.astype(np.float32), -1, mean_kernel)

    # Adjust the strength of the effect
    processed_image = image + strength * (image - mean_removed_image)

    # Clip values to stay within the valid range [0, 255]
    processed_image = np.clip(processed_image, 0, 255).astype(np.uint8)

    return processed_image
# }}}

def blend(image1, image2, factor=0.5):
    """Blend two images using a given factor"""
    return cv2.addWeighted(image1, 1 - factor, image2, factor, 0)


def create_halftone( # {{{
    input_image,
    output_image,
    downscale_factor=default_values["downscale_factor"],
    gamma=default_values["gamma"],
    multiply=default_values["multiply"],
    randomize=default_values["no-randomize"],
    spread=default_values["no-spread"],
    max_diameter=default_values["max_diameter"],
    spread_size=default_values["spread_size"],
    output_width=default_values["width"],
    use_squares=default_values["use_squares"],
    normalize=default_values["normalize"],
    sharpen=default_values["sharpen"],
    threshold=default_values["threshold"],
    no_dots=default_values["no-dots"],
    hypersample=default_values["hypersample"],
):
    f"""
    Create a halftone image from an input image
    :param input_image: Input image (path)
    :param output_image: Output halftone image (path)
    :param downscale_factor: Downscale factor (higher = smaller image) [default={downscale_factor}]
    :param gamma: Gamma correction [default={gamma}]
    :param multiply: Multiplication factor for radiuses [default={multiply}]
    :param randomize: Randomize positions of dots to break the visual distribution of dots [default={randomize}]
    :param spread: Spread the dots values for a larger dynamic range [default={spread}]
    :param max_diameter: Maximum diameter of the halftone dots (output image size will increase accordingly) [default={max_diameter}]
    :param spread_size: defines block size used in spreading (larger == more "blurry") [default={spread_size}]
    :param output_width: Output image width [default={output_width or "auto"}]
    :param use_squares: Use squares instead of circles [default={use_squares}]
    :param normalize: Normalization factor [default={normalize}]
    :param sharpen: Sharpening effect [default={sharpen}]
    :param threshold: Changes what is considered black or white [default={threshold}]
    :param no_dots: Do not draw dots [default={no_dots}]
    :param hypersample: Hyper-sampling factor [default={hypersample}]
    """
    # Load the input image as greyscale
    img = cv2.imread(input_image)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)[..., 2]
    grey_img = img  # keep an unprocessed reference for later

    if output_width is not None:
        downscale_factor = (max_diameter * img.shape[1]) / output_width
        print(f"Downscaled {downscale_factor:.1f}x")

    if not no_dots:
        img = cv2.resize(
            img,
            (0, 0),
            fx=hypersample / downscale_factor,
            fy=hypersample / downscale_factor,
            interpolation=cv2.INTER_AREA,
        )

    if sharpen:
        img = blend(img, mean_removal(img, strength=5*hypersample), sharpen)

    if normalize:
        img = blend(img, cv2.equalizeHist(img), normalize)

    if no_dots:
        cv2.imwrite(output_image, img)
        return

    big_img = cv2.resize(
        grey_img,
        (0, 0),
        fx=hypersample * max_diameter / downscale_factor,
        fy=hypersample * max_diameter / downscale_factor,
        interpolation=cv2.INTER_NEAREST,
    )
    del grey_img

    # Create an empty canvas for the halftone image with floating-point values
    halftone = np.ones(big_img.shape, dtype=np.uint8) * 255

    # make list of circle radiuses
    darkness = 1.0 - (img / 255.0) ** gamma
    intensity = np.where(darkness == 1.0, -1.0, darkness * max_diameter * multiply)

    if spread:
        spread_dots(intensity, spread_size)

    draw_circles(halftone, intensity, max_diameter, randomize, use_squares)

    # handle black & white masks {{{
    black_mask = (big_img < threshold).astype(np.uint8)
    white_mask = (big_img > 255 - threshold).astype(np.uint8)

    # Add fully black and fully white pixels to the halftone image
    halftone[black_mask > 0] = 0
    halftone[white_mask > 0] = 255
    # }}}

    if hypersample > 1.0:
        halftone = cv2.resize(
            cv2.cvtColor(halftone.astype(np.float32), cv2.COLOR_GRAY2RGB), (0, 0), fx=1.0/hypersample, fy=1.0/hypersample, interpolation=cv2.INTER_CUBIC)

        halftone[(threshold < halftone) & (halftone < 255 - threshold)] = 127

    # Save the halftone image
    cv2.imwrite(output_image, halftone)
# }}}

def main():
    # Argument handling {{{
    def add_argument(name, **kw):
        help = kw.pop("help")
        default = default_values[name]
        if default is None:
            default = "auto"
        parser.add_argument(
            "--" + name,
            default=default_values[name],
            help=help + f" (default: {default})",
            **kw,
        )

    parser = argparse.ArgumentParser(
        description="Generate a halftone image from an input image."
    )
    parser.add_argument("input_image", help="Input image filename")
    parser.add_argument("output_image", help="Output halftone image filename")
    add_argument("downscale_factor", type=int, help="Downscale factor")
    add_argument("gamma", type=float, help="Gamma correction")
    add_argument("multiply", type=float, help="Multiplication factor for diameters (0 = white image, >1 = darker image)")
    add_argument(
        "no-randomize", action="store_true", help="Do not randomize positions of dots"
    )
    add_argument(
        "no-spread",
        action="store_true",
        help="Do not spread the dots values for a larger dynamic range",
    )
    add_argument("max_diameter", type=int, help="Maximum radius of the halftone dots.\noutput image size will increase accordingly")
    add_argument("spread_size", type=int, help="defines block size used in spreading")
    add_argument("width", type=int, help="Output image width - autocompute 'downscale_factor' to respect 'max_diameter'")
    add_argument(
        "use_squares", action="store_true", help="Use squares instead of circles"
    )
    add_argument("normalize", type=float, help="Normalization factor")
    add_argument("sharpen", type=float, help="Sharpening effect")
    add_argument(
        "threshold", type=int, help="Changes what is considered black or white"
    )
    add_argument(
        "no-dots",
        action="store_true",
        help="Do not draw B&W dots (only process the image)",
    )
    add_argument("hypersample", type=float, help="Hyper-sampling factor")

    args = parser.parse_args()  # }}}

    create_halftone(
        args.input_image,
        args.output_image,
        args.downscale_factor,
        args.gamma,
        args.multiply,
        not args.no_randomize,
        not args.no_spread,
        args.max_diameter,
        args.spread_size,
        args.width,
        args.use_squares,
        args.normalize,
        args.sharpen,
        args.threshold,
        args.no_dots,
        args.hypersample,
    )


if __name__ == "__main__":
    main()
