# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

import tempfile
from pathlib import Path

def create_temp_file(text: bool = False, suffix: str | None = None) -> str:
    """
    Safely create file for storing temporary data.

    :param text: Select if temporary file should be opened in text mode.
    :type text: :class:`bool`

    :param suffix: Use custom filename suffix (eg. file extension).
    :type suffix: :class:`str`

    :returns: An absolute path to the temp file.
    :rtype: :class:`str`
    """

    temp_file = tempfile.mkstemp(prefix="halftone-", suffix=suffix, text=text)
    temp_path = temp_file[1]
    return temp_path

def delete_temp_file(path: str) -> None:
    """
    Delete temporary file located at given path.

    :param path: Absolute path to the temporary file.
    :type path: :class:`str`

    :rtype: :class:`None`
    """

    if not path:
        return

    temp_file = Path(path)
    temp_file.unlink()
