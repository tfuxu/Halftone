# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw, Gio, Gtk

from halftone.constants import rootdir # pyright: ignore


@Gtk.Template(resource_path=f"{rootdir}/ui/report_page.ui")
class HalftoneReportPage(Gtk.Box):
    __gtype_name__ = "HalftoneReportPage"

    def __init__(self, parent: Gtk.Widget, **kwargs) -> None:
        super().__init__(**kwargs)

        self.parent = parent
        self.settings: Gio.Settings = parent.settings

        self.app: Adw.Application = self.parent.get_application()
        self.win: Adw.ApplicationWindow = self.app.get_active_window()

        self._setup_signals()
        self._setup()

    """
    Setup methods
    """

    def _setup_signals(self) -> None:
        pass

    def _setup(self) -> None:
        pass
