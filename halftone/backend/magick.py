# Copyright 2023, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from wand.image import Image

from halftone.backend.utils.image import calculate_height
from halftone.backend.model.output_options import OutputOptions


class HalftoneImageMagick:
    """
    Class for performing color quantization and dithering operations on images
    based on Wand Python library (bindings for ImageMagick API).
    """

    def __init__(self):
        pass

    def dither_image(self, blob: bytes, output_options: OutputOptions) -> bytes:
        with Image(blob=blob) as img:
            img_width = img.size[0]
            img_height = img.size[1]

            if not output_options.width:
                output_options.width = img_width

            width = output_options.width
            height = output_options.height
            color_amount = output_options.color_amount
            algorithm = output_options.algorithm
            output_format = output_options.output_format

            new_width = int(width)
            if not height:
                new_height = calculate_height(img_width, img_height, new_width)
            else:
                new_height = int(height)

            with img.clone() as clone:
                clone.resize(width=new_width, height=new_height)
                # Available error correction dither algorithms: floyd_steinberg, riemersma (More info: https://docs.wand-py.org/en/0.6.11/wand/image.html#wand.image.DITHER_METHODS)
                # Available ordered dithers: https://docs.wand-py.org/en/0.6.11/wand/image.html#wand.image.BaseImage.ordered_dither
                if algorithm == "ordered":
                    clone.ordered_dither("o4x4")
                    clone.quantize(color_amount)
                else:
                    clone.quantize(color_amount, dither=algorithm)

                image_blob = clone.make_blob(format=output_format)

        return image_blob

    def save_image(self, blob: bytes, output_filename: str, output_options: OutputOptions) -> None:
        with Image(blob=blob) as img:
            try:
                output_image = img.convert(output_options.output_format)
            except ValueError:
                raise
            else:
                output_image.save(filename=output_filename)
