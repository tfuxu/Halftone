# filters.py: supported filetypes and filter helpers
#
# Copyright (C) 2022 Khaleel Al-Adhami / adhami3310
# Copyright 2023, tfuxu <https://github.com/tfuxu>
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

from gi.repository import Gtk


""" Declare lists. """
#supported_input_formats = ['png', 'jpg', 'jpeg', 'webp', 'svg', 'heif', 'heic', 'bmp', 'avif', 'jxl', 'tiff', 'tif', 'gif']
supported_input_formats = ['png', 'jpg', 'jpeg', 'svg', 'bmp', 'avif', 'tiff', 'tif', 'gif']
supported_output_formats = sorted(['bmp', 'png', 'jpg', 'webp', 'heic', 'heif', 'avif', 'jxl', 'tiff', 'gif'])
popular_supported_output_formats = sorted(['bmp', 'png', 'jpg', 'webp', 'heic', 'avif', 'jxl', 'gif'])
#compressed_formats = sorted(['zip', 'tar.gz'])

extension_to_mime = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',
    'svg': 'image/svg+xml',
    'heic': 'image/heic',
    'heif': 'image/heif',
    'bmp': 'image/bmp',
    'avif': 'image/avif',
    'jxl': 'image/jxl',
    #'zip': 'application/zip',
    #'tar.gz': 'application/gzip',
    'tiff': 'image/tiff',
    'tif': 'image/tiff',
    'gif': 'image/gif'
}

def get_format_filters(filetype):
    """ Formats getter function. """

    if filetype == "input":
        return [extension_to_mime[image] for image in supported_input_formats]

    if filetype == "popular_output":
        return [extension_to_mime[image] for image in popular_supported_output_formats]

    if filetype == "output":
        return [extension_to_mime[image] for image in supported_output_formats]

    return None

def get_file_filter(name, formats):
    """ Formats setter function. """

    filefilter = Gtk.FileFilter()
    for fmt in formats:
        filefilter.add_mime_type(extension_to_mime[fmt.lower()])

    filefilter.set_name(name)
    return filefilter
