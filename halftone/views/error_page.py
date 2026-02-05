# Copyright 2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Optional
from gi.repository import Adw, Gio, Gtk

from halftone.constants import rootdir # pyright: ignore


@Gtk.Template(resource_path=f"{rootdir}/ui/error_page.ui")
class HalftoneErrorPage(Adw.Bin):
    __gtype_name__ = "HalftoneErrorPage"

    copy_logs_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, parent: Gtk.Widget, **kwargs) -> None:
        super().__init__(**kwargs)

        self.parent = parent
        self.settings: Gio.Settings = parent.settings

        self._latest_error: Optional[str] = None

        self.app: Adw.Application = self.parent.get_application()
        self.win: Adw.ApplicationWindow = self.app.get_active_window()

        self._setup_signals()
        self._setup()

    """
    Setup methods
    """

    def _setup_signals(self):
        pass

    def _setup(self):
        pass

    """
    Callbacks
    """

    @Gtk.Template.Callback()
    def on_copy_logs_clicked(self, *args) -> None:
        clipboard = self.get_clipboard()
        clipboard.set(self._latest_error)

        self.parent.toast_overlay.add_toast(
            Adw.Toast(title=_("Copied logs to clipboard"))
        )

    """
    Public Methods
    """

    def set_latest_error(self, error_text: Optional[str]) -> None:
        if error_text:
            self.copy_logs_button.set_sensitive(True)
        else:
            self.copy_logs_button.set_sensitive(False)

        self._latest_error = error_text
