# Copyright 2023, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import logging

from gi.repository import GObject, Gtk, Gdk, Gio, Adw, GLib

from pixely.constants import rootdir, app_id, build_type
from pixely.views.main_window import PixelyMainWindow
from pixely.views.preferences_window import PixelyPreferencesWindow
from pixely.views.about_window import PixelyAboutWindow

if build_type == "debug":
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging_level)


class PixelyApplication(Adw.Application):
    __gtype_name__ = "PixelyApplication"

    def __init__(self):
        super().__init__(
            application_id=app_id,
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.set_resource_base_path(rootdir)

        self.window = None
        self.settings = Gio.Settings.new(app_id)

        self.setup_actions()

    def do_activate(self):
        """ Called when the application is activated. """

        self.window = self.props.active_window

        if not self.window:
            self.window = PixelyMainWindow(
                application=self,
                default_height=self.settings.get_int("window-height"),
                default_width=self.settings.get_int("window-width"),
                maximized=self.settings.get_boolean("window-maximized")
            )

        self.window.present()

    def setup_actions(self):
        """ Setup menu actions and accelerators. """

        user_home_dir = os.environ.get("XDG_CONFIG_HOME", os.environ["HOME"])

        show_saved_image_action = Gio.SimpleAction.new_stateful(
                'show-saved-image',
                GLib.VariantType.new("s"),
                GLib.Variant("s", user_home_dir))
        show_saved_image_action.connect('activate', self.open_saved_image)
        self.add_action(show_saved_image_action)

        '''preferences_action = Gio.SimpleAction.new('preferences', None)
        preferences_action.connect('activate', self.on_preferences)
        self.add_action(preferences_action)'''

        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about)
        self.add_action(about_action)

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self.on_quit)
        self.add_action(quit_action)

        self.set_accels_for_action('win.show-help-overlay', ['<Primary>question'])

        self.set_accels_for_action('app.open-image', ['<Primary>O'])
        self.set_accels_for_action('app.save-image', ['<Primary>S'])
        #self.set_accels_for_action('app.preferences', ['<Primary>comma'])
        self.set_accels_for_action('app.quit', ['<Primary>Q', '<Primary>W'])

    def open_saved_image(self, action, output_path: GLib.Variant, *args):
        """ Show directory of saved image. """

        Gtk.show_uri(
            self.window,
            f"file://{output_path.get_string()}",
            Gdk.CURRENT_TIME
        )

    '''def on_preferences(self, *args):
        """ Show preferences window. """

        pref_window = PixelyPreferencesWindow(self.window)
        pref_window.present()'''

    def on_about(self, *args):
        """ Show about dialog. """

        about_window = PixelyAboutWindow(self.window)
        about_window.show_about()

    def on_quit(self, *args):
        """ Quit application process. """

        self.quit()


def main():
    """ The application's entry point. """

    app = PixelyApplication()
    return app.run(sys.argv)
