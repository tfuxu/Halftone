# Copyright 2023, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw, Gtk

from halftone.constants import rootdir # pylint: disable=E0401,E0611


@Gtk.Template(resource_path=f"{rootdir}/ui/preferences_window.ui")
class HalftonePreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = "HalftonePreferencesWindow"

    content_fit_combo = Gtk.Template.Child()

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.settings = parent.settings

        self.app = self.parent.get_application()
        self.win = self.app.get_active_window()

        self.set_transient_for(self.win)

        self.setup()
        self.setup_signals()

    def setup_signals(self):
        self.content_fit_combo.connect("notify::selected",
            self.on_content_fit_selected)

    def setup(self):
        self.setup_content_fit()

    def setup_content_fit(self, *args):
        selected_content_fit = self.settings.get_int("preview-content-fit")
        self.content_fit_combo.set_selected(selected_content_fit)

    def on_content_fit_selected(self, widget, *args):
        selected_content_fit = widget.props.selected
        self.settings.set_int("preview-content-fit", selected_content_fit)
