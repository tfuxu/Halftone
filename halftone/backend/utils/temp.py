# Copyright 2023, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

import tempfile
from pathlib import Path


class HalftoneTempFile:
    def __init__(self):
        pass

    def create_temp_file(self, text: bool = False, suffix: str = None) -> str:
        """
        Safely create file for storing temporary data.

        Returns
        -------
        :class:`str`:
            An absolute path to the temp file.
        """

        temp_file = tempfile.mkstemp(prefix="halftone-", suffix=suffix, text=text)
        temp_path = temp_file[1]
        return temp_path

    def delete_temp_file(self, path: str) -> None:
        """
        Delete temporary file located at given path.
        """

        temp_file = Path(path)
        temp_file.unlink()
