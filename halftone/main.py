# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
from collections.abc import Sequence
from typing import Optional

from gi.repository import Adw, Gio

from halftone.backend.logger import Logger
from halftone.constants import app_id, rootdir  # pyright: ignore
from halftone.views.main_window import HalftoneMainWindow

logging = Logger()


class HalftoneApplication(Adw.Application):
    __gtype_name__ = "HalftoneApplication"

    def __init__(self) -> None:
        super().__init__(
            application_id=app_id,
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )

        self.set_resource_base_path(rootdir)
        self.settings: Gio.Settings = Gio.Settings.new(app_id)

        self._setup_actions()

    """
    Overrides
    """

    def do_open(self, files: Sequence[Gio.File], n_files: int, hint: str):
        """Handle opening a new windows with specified file paths"""
        for file in files:
            path = file.get_path()
            if path:
                self._open_window(file_path=path)

    def do_activate(self, *args, **kwargs) -> None:
        """Called when the application is activated without files."""
        self._open_window()

    """
    Private methods
    """

    def _open_window(self, file_path: Optional[str] = None):
        """Create and show a new window, optionally with a file loaded."""
        window = HalftoneMainWindow(
            application=self,  # pyright: ignore
            default_height=self.settings.get_int("window-height"),  # pyright: ignore
            default_width=self.settings.get_int("window-width"),  # pyright: ignore
            maximized=self.settings.get_boolean("window-maximized"),  # pyright: ignore
            file_path=file_path
        )
        window.present()

    """
    Setup methods
    """

    def _setup_actions(self) -> None:
        """ Setup menu actions and accelerators. """

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self._on_quit)
        self.add_action(quit_action)

        self.set_accels_for_action('app.quit', ['<Primary>Q'])
        self.set_accels_for_action('window.close', ['<Primary>W'])

    """
    Callbacks
    """

    def _on_quit(self, *args) -> None:
        """ Quit application process. """

        self.quit()

"""
Main entry point
"""

def main() -> int:
    """ The application's entry point. """

    app = HalftoneApplication()
    return app.run(sys.argv)
