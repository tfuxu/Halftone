# Copyright 2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw, Gtk, Gio

from halftone.constants import rootdir # pyright: ignore


@Gtk.Template(resource_path=f"{rootdir}/ui/error_page.ui")
class HalftoneErrorPage(Adw.Bin):
    __gtype_name__ = "HalftoneErrorPage"

    def __init__(self, parent: Gtk.Widget, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.settings: Gio.Settings = parent.settings

        self.app: Adw.Application = self.parent.get_application()
        self.win: Adw.ApplicationWindow = self.app.get_active_window()

        self.setup_signals()
        self.setup()

    def setup_signals(self):
        pass

    def setup(self):
        pass

    @Gtk.Template.Callback()
    def on_copy_logs_clicked(self, *args):
        clipboard = self.get_clipboard()
        clipboard.set(self.parent.latest_traceback)

        self.parent.toast_overlay.add_toast(
            Adw.Toast(title=_("Copied logs to clipboard"))
        )
