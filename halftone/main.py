# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

from gi.repository import Adw, GLib, Gio, Gtk

from halftone.backend.logger import Logger
from halftone.constants import app_id, rootdir  # pyright: ignore
from halftone.views.main_window import HalftoneMainWindow
#from halftone.views.preferences_window import HalftonePreferencesWindow

logging = Logger()


class HalftoneApplication(Adw.Application):
    __gtype_name__ = "HalftoneApplication"

    def __init__(self) -> None:
        super().__init__(
            application_id=app_id,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

        self.set_resource_base_path(rootdir)

        self.window: Adw.ApplicationWindow = None
        self.settings: Gio.Settings = Gio.Settings.new(app_id)

    """
    Overrides
    """

    def do_activate(self, *args, **kwargs) -> None:
        """ Called when the application is activated. """

        self.window = self.props.active_window

        if not self.window:
            self.window = HalftoneMainWindow(
                application=self, # pyright: ignore
                default_height=self.settings.get_int("window-height"), # pyright: ignore
                default_width=self.settings.get_int("window-width"), # pyright: ignore
                maximized=self.settings.get_boolean("window-maximized") # pyright: ignore
            )

        self.window.present()

"""
Main entry point
"""

def main() -> int:
    """ The application's entry point. """

    app = HalftoneApplication()
    return app.run(sys.argv)
