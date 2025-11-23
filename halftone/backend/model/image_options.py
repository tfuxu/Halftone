# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass


# TODO: Rename this class to something more correct, e.g. `ImageOptions`
@dataclass
class ImageOptionsModel:
    width: int = 0
    height: int = 0
    contrast: int = 0
    brightness: int = 0
    color_amount: int = 10
    algorithm: str = "floyd_steinberg"
    output_format: str = "png"
