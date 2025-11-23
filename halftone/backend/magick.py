# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from wand.image import Image

from halftone.backend.model.image_options import ImageOptionsModel
from halftone.backend.utils.image import calculate_height
from halftone.backend.utils.temp import create_temp_file


class HalftoneImageMagick:
    """
    Class for performing color quantization and dithering operations on images
    based on Wand Python library (bindings for ImageMagick API).
    """

    def __init__(self):
        pass

    # TODO: We should somehow decouple every image operation to a seperate function,
    # so that only the latest change made by user is applied to the image.
    def dither_image(self, path: str, image_options: ImageOptionsModel) -> str:
        with Image(filename=path) as img:
            img_width = img.size[0]
            img_height = img.size[1]

            if not image_options.width:
                image_options.width = img_width

            width = image_options.width
            height = image_options.height
            contrast = image_options.contrast
            brightness = image_options.brightness
            color_amount = image_options.color_amount
            algorithm = image_options.algorithm

            new_width = int(width)
            if not height:
                new_height = calculate_height(img_width, img_height, new_width)
            else:
                new_height = int(height)

            # TODO: Remove `colorspace_type` parameter on Wand 0.7.0 release.
            # See: https://github.com/emcconville/wand/issues/644
            with img.convert("PNG").clone() as clone:
                clone.resize(width=new_width, height=new_height)
                clone.brightness_contrast(float(brightness), float(contrast))
                # Available error correction dither algorithms: floyd_steinberg, riemersma (More info: https://docs.wand-py.org/en/0.6.11/wand/image.html#wand.image.DITHER_METHODS)
                # Available ordered dithers: https://docs.wand-py.org/en/0.6.11/wand/image.html#wand.image.BaseImage.ordered_dither
                if algorithm == "ordered":
                    clone.ordered_dither("o4x4")
                    clone.quantize(color_amount, colorspace_type="undefined")
                else:
                    clone.quantize(
                        number_colors=color_amount,
                        colorspace_type="undefined",
                        dither=algorithm  # pyright: ignore
                    )

                temp_path = create_temp_file()
                clone.save(filename=temp_path)

        return temp_path

    def save_image(
        self,
        blob: bytes,
        output_filename: str,
        image_options: ImageOptionsModel
    ) -> None:
        with Image(blob=blob) as img:
            output_image = img.convert(image_options.output_format)
            output_image.save(filename=output_filename)
