# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk

from halftone.backend.utils.filetypes import FileType


def get_file_filter(filter_name: str, filetypes: list[FileType]) -> Gtk.FileFilter:
    file_filter = Gtk.FileFilter(name=filter_name)

    for filetype in filetypes:
        file_filter.add_mime_type(filetype.as_mimetype())

    return file_filter
