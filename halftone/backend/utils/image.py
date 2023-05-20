# Copyright 2023, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

def calculate_height(original_width: int, original_height: int, new_width: int) -> int:
    """
    Calculate new height based on original image size and new width value,
    keeping original image aspect ratio.
    """

    img_width = int(original_width)
    img_height = int(original_height)
    new_width = int(new_width)

    new_height = int((img_height / img_width) * new_width)  # Aspect ratio height formula
    return new_height

