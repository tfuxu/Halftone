#
# Copyright (C) 2022 Khaleel Al-Adhami / adhami3310
# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from enum import StrEnum, auto
from typing import Optional, Self


class FileType(StrEnum):
    PNG  = auto()
    JPEG = auto()
    JPG  = auto()
    WEBP = auto()
    SVG  = auto()
    HEIF = auto()
    HEIC = auto()
    BMP  = auto()
    AVIF = auto()
    JXL  = auto()
    TIFF = auto()
    GIF  = auto()

    def as_mimetype(self) -> str:
        match self:
            case FileType.PNG:
                return "image/png"
            case FileType.JPEG:
                return "image/jpeg"
            case FileType.JPG:
                return "image/jpeg"
            case FileType.WEBP:
                return "image/webp"
            case FileType.SVG:
                return "image/svg+xml"
            case FileType.HEIF:
                return "image/heif"
            case FileType.HEIC:
                return "image/heic"
            case FileType.BMP:
                return "image/bmp"
            case FileType.AVIF:
                return "image/avif"
            case FileType.JXL:
                return "image/jxl"
            case FileType.TIFF:
                return "image/tiff"
            case FileType.GIF:
                return "image/gif"

    @classmethod
    def from_mimetype(cls, mimetype: str) -> Optional[Self]:
        match mimetype:
            case "image/png":
                return cls("png")
            case "image/jpeg":
                return cls("jpeg")
            case "image/jpg":
                return cls("jpg")
            case "image/webp":
                return cls("webp")
            case "image/svg+xml":
                return cls("svg")
            case "image/heif":
                return cls("heif")
            case "image/heic":
                return cls("heic")
            case "image/bmp":
                return cls("bmp")
            case "image/avif":
                return cls("avif")
            case "image/jxl":
                return cls("jxl")
            case "image/tiff":
                return cls("tiff")
            case "image/gif":
                return cls("gif")
            case _:
                return None

    def as_extension(self) -> str:
        match self:
            case FileType.PNG:
                return "png"
            case FileType.JPEG:
                return "jpeg"
            case FileType.JPG:
                return "jpg"
            case FileType.WEBP:
                return "webp"
            case FileType.SVG:
                return "svg"
            case FileType.HEIF:
                return "heif"
            case FileType.HEIC:
                return "heic"
            case FileType.BMP:
                return "bmp"
            case FileType.AVIF:
                return "avif"
            case FileType.JXL:
                return "jxl"
            case FileType.TIFF:
                return "tiff"
            case FileType.GIF:
                return "gif"

    @classmethod
    def from_extension(cls, extension: str) -> Optional[Self]:
        match extension:
            case "png":
                return cls("png")
            case "jpeg":
                return cls("jpeg")
            case "jpg":
                return cls("jpg")
            case "webp":
                return cls("webp")
            case "svg":
                return cls("svg")
            case "heif":
                return cls("heif")
            case "heic":
                return cls("heic")
            case "bmp":
                return cls("bmp")
            case "avif":
                return cls("avif")
            case "jxl":
                return cls("jxl")
            case "tiff":
                return cls("tiff")
            case "gif":
                return cls("gif")
            case _:
                return None

def get_input_formats() -> list[FileType]:
    filetypes = [
        FileType.PNG,
        FileType.JPEG,
        FileType.JPG,
        FileType.WEBP,
        FileType.SVG,
        FileType.HEIF,
        FileType.HEIC,
        FileType.BMP,
        FileType.AVIF,
        FileType.JXL,
        FileType.TIFF,
        FileType.GIF
    ]

    return filetypes
    
def get_output_formats(all_formats: bool) -> list[FileType]:
    all_filetypes = [
        FileType.PNG,
        FileType.JPG,
        FileType.WEBP,
        FileType.HEIF,
        FileType.HEIC,
        FileType.BMP,
        FileType.AVIF,
        FileType.JXL,
        FileType.TIFF,
        FileType.GIF
    ]
    popular_filetypes = [
        FileType.PNG,
        FileType.JPG,
        FileType.WEBP,
        FileType.HEIF,
        FileType.TIFF,
        FileType.GIF
    ]
    
    if all_formats:
        return all_filetypes

    return popular_filetypes
