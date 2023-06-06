# Copyright 2023, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass


@dataclass
class OutputOptions:
    width: int = None
    height: int = None
    contrast: int = 0
    brightness: int = 0
    color_amount: int = 10
    algorithm: str = "floyd_steinberg"
    output_format: str = "png"
