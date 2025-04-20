# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

from gi.repository import Gtk, Gio, Adw, GLib

from halftone.backend.logger import Logger

from halftone.constants import rootdir, app_id # pyright: ignore
from halftone.views.main_window import HalftoneMainWindow
from halftone.views.about_window import HalftoneAboutWindow
#from halftone.views.preferences_window import HalftonePreferencesWindow

logging = Logger()


class HalftoneApplication(Adw.Application):
    __gtype_name__ = "HalftoneApplication"

    def __init__(self):
        super().__init__(
            application_id=app_id,
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.set_resource_base_path(rootdir)

        self.window: Adw.ApplicationWindow = None
        self.settings: Gio.Settings = Gio.Settings.new(app_id)

        self.setup_actions()

    def do_activate(self, *args, **kwargs):
        """ Called when the application is activated. """

        self.window = self.props.active_window

        if not self.window:
            self.window = HalftoneMainWindow(
                application=self, # pyright: ignore
                default_height=self.settings.get_int("window-height"), # pyright: ignore
                default_width=self.settings.get_int("window-width"), # pyright: ignore
                maximized=self.settings.get_boolean("window-maximized") # pyright: ignore
            ) # pyright: ignore

        self.window.present()

    def setup_actions(self):
        """ Setup menu actions and accelerators. """

        user_home_dir = os.environ.get("XDG_CONFIG_HOME", os.environ["HOME"])

        show_image_external_action = Gio.SimpleAction.new_stateful(
                'show-image-externally',
                GLib.VariantType.new("s"),
                GLib.Variant("s", user_home_dir))
        show_image_external_action.connect('activate', self.show_image_external)
        self.add_action(show_image_external_action)

        show_preview_image_action = Gio.SimpleAction.new('show-preview-image', None)
        show_preview_image_action.connect('activate', self.show_preview_image)
        self.add_action(show_preview_image_action)

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

        self.set_accels_for_action('app.toggle-sheet', ['F9'])
        self.set_accels_for_action('app.open-image', ['<Primary>O'])
        self.set_accels_for_action('app.save-image', ['<Primary>S'])
        #self.set_accels_for_action('app.preferences', ['<Primary>comma'])
        self.set_accels_for_action('app.quit', ['<Primary>Q', '<Primary>W'])

    def show_preview_image(self, _action: Gio.SimpleAction, *args):
        """ Helper for `show-preview-image` action. """

        preview_image_path = self.window.dither_page.preview_image_path # pyright: ignore
        image_path_variant = GLib.Variant("s", preview_image_path)

        self.show_image_external(None, image_path_variant)

    def show_image_external(self, _action: Gio.SimpleAction | None, image_path: GLib.Variant, *args):
        """
        Launch an external application to display provided image.

        This may present an app chooser dialog to the user
        depending on system and configuration.
        """

        try:
            image_file = Gio.File.new_for_path(image_path.get_string())
        except GLib.Error as e:
            logging.traceback_error("Failed to construct a new Gio.File object from path.",
                                    exception=e, show_exception=True)
            self.window.latest_traceback = logging.get_traceback(e)
            self.window.toast_overlay.add_toast(
                Adw.Toast(title=_("Failed to open preview image. Check logs for more information"))
            )
        else:
            launcher = Gtk.FileLauncher.new(image_file)

            def open_image_finish(_launcher: Gtk.FileLauncher, result: Gio.AsyncResult, *args):
                try:
                    launcher.launch_finish(result)
                except GLib.Error as e:
                    if e.code != 2: # 'The portal dialog was dismissed by the user' error
                        logging.traceback_error("Failed to finish Gtk.FileLauncher procedure.",
                                                exception=e, show_exception=True)
                        self.window.latest_traceback = logging.get_traceback(e)
                        self.window.toast_overlay.add_toast(
                            Adw.Toast(title=_("Failed to open preview image. Check logs for more information"))
                        )

            launcher.launch(self.window, None, open_image_finish)

    '''def on_preferences(self, *args):
        """ Show preferences window. """

        pref_window = HalftonePreferencesWindow(self.window)
        pref_window.present()'''

    def on_about(self, *args):
        """ Show about dialog. """

        about_window = HalftoneAboutWindow(self.window)
        about_window.show_about()

    def on_quit(self, *args):
        """ Quit application process. """

        self.quit()


def main():
    """ The application's entry point. """

    app = HalftoneApplication()
    return app.run(sys.argv)
