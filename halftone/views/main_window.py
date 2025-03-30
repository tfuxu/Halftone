# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Literal

from gi.repository import GLib, Gdk, Gio, Gtk, Adw

from halftone.views.error_page import HalftoneErrorPage
from halftone.views.dither_page import HalftoneDitherPage
from halftone.views.report_page import HalftoneReportPage

from halftone.backend.utils.filetypes import get_input_formats
from halftone.backend.logger import Logger

from halftone.utils.filters import get_file_filter
from halftone.constants import rootdir, app_id, build_type # pyright: ignore

logging = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/main_window.ui")
class HalftoneMainWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'HalftoneMainWindow'

    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()

    main_stack: Gtk.Stack = Gtk.Template.Child()
    open_image_button: Gtk.Button = Gtk.Template.Child()

    open_image_dialog: Gtk.FileDialog = Gtk.Template.Child()
    all_filter: Gtk.FileFilter = Gtk.Template.Child()

    content = Gdk.ContentFormats.new_for_gtype(Gio.File)
    drop_target = Gtk.DropTarget(formats=content, actions=Gdk.DragAction.COPY)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Application object
        self.app: Adw.Application = kwargs['application']
        self.settings: Gio.Settings = Gio.Settings(app_id)

        self.latest_traceback: str = ""

        self.add_controller(self.drop_target)

        self.error_page: Adw.Bin = HalftoneErrorPage(self)
        self.dither_page: Adw.BreakpointBin = HalftoneDitherPage(self)
        self.report_page: Gtk.Box = HalftoneReportPage(self)

        self.setup_actions()
        self.setup_signals()
        self.setup()

    def setup_actions(self):
        """ Setup menu actions and accelerators. """

        self.toggle_sheet_action = Gio.SimpleAction.new('toggle-sheet', None)
        self.toggle_sheet_action.connect('activate', self.dither_page.on_toggle_sheet)
        self.app.add_action(self.toggle_sheet_action)

        self.open_image_action = Gio.SimpleAction.new('open-image', None)
        self.open_image_action.connect('activate', self.on_open_image)
        self.app.add_action(self.open_image_action)

        self.save_image_action = Gio.SimpleAction.new('save-image', None)
        self.save_image_action.connect('activate', self.dither_page.on_save_image)
        self.app.add_action(self.save_image_action)

        # By default disable dither page specific actions
        self.toggle_sheet_action.set_enabled(False)
        self.save_image_action.set_enabled(False)

    def setup_signals(self):
        self.drop_target.connect("drop",
            self.on_target_drop)

        self.drop_target.connect("enter",
            self.on_target_enter)

        self.drop_target.connect("leave",
            self.on_target_leave)

        self.connect("close-request",
            self.on_close_request)

        self.connect("unrealize",
            self.save_window_props)

    def setup(self):
        self.set_default_icon_name(app_id)

        # Set devel style
        if build_type == "debug":
            self.add_css_class("devel")

        # Prefer to use dark scheme
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)

        self.setup_image_dialog()
        self.setup_main_stack()

    def setup_image_dialog(self):
        input_formats = get_input_formats()

        supported_filter = get_file_filter(
            _("Supported image formats"), input_formats
        )

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(supported_filter)
        filters.append(self.all_filter)

        self.open_image_dialog.set_filters(filters)

    def setup_main_stack(self):
        # TODO: Finish report page
        #self.main_stack.add_named(self.report_page, "stack_report_page")
        self.main_stack.add_named(self.error_page, "stack_error_page")
        self.main_stack.add_named(self.dither_page, "stack_dither_page")

    def load_image(self, file: Gio.File):
        self.show_loading_page()
        try:
            self.dither_page.load_preview_image(file)
        except GLib.Error as e:
            # TODO: Modify error page for different error codes
            if e.code == 3:  # Unrecognized image file format
                return

            logging.traceback_error("Failed to load an image.",
                                        exception=e, show_exception=True)
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("Failed to load an image. Check logs for more information"))
            )
            self.latest_traceback = logging.get_traceback(e)
            self.show_error_page()
            return
        else:
            self.show_dither_page()

    @Gtk.Template.Callback()
    def on_open_image(self, *args):
        self.open_image_dialog.open(self, None, self.on_image_dialog_result)

    def on_image_dialog_result(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult):
        try:
            file = dialog.open_finish(result)
        except GLib.Error as e:
            if e.code != 2: # 'Dismissed by user' error
                logging.traceback_error("Failed to finish Gtk.FileDialog procedure.",
                                        exception=e, show_exception=True)
                self.toast_overlay.add_toast(
                    Adw.Toast(title=_("Failed to retrieve a file. Check logs for more information"))
                )
                self.latest_traceback = logging.get_traceback(e)
        else:
            if file is not None:
                self.load_image(file)

    def on_target_drop(self, widget: Gtk.DropTarget, file: Gio.File, *args):
        if file is not None:
            self.load_image(file)

    def on_target_enter(self, *args) -> Literal[Gdk.DragAction.COPY]:
        self.previous_stack = self.main_stack.get_visible_child_name()
        self.main_stack.set_visible_child_name('stack_drop_page')

        return Gdk.DragAction.COPY

    def on_target_leave(self, *args):
        if self.previous_stack:
            self.main_stack.set_visible_child_name(self.previous_stack)

    def show_loading_page(self, *args):
        self.toggle_sheet_action.set_enabled(False)
        self.open_image_action.set_enabled(False)
        self.save_image_action.set_enabled(False)
        self.main_stack.set_visible_child_name("stack_loading_page")

    def show_error_page(self, *args):
        self.toggle_sheet_action.set_enabled(False)
        self.open_image_action.set_enabled(True)
        self.save_image_action.set_enabled(False)
        self.main_stack.set_visible_child_name("stack_error_page")

    def show_dither_page(self, *args):
        self.toggle_sheet_action.set_enabled(True)
        self.open_image_action.set_enabled(True)
        self.save_image_action.set_enabled(True)
        self.main_stack.set_visible_child_name("stack_dither_page")

    def on_close_request(self, *args):
        self.dither_page.clean_preview_paintable()

    def save_window_props(self, *args):
        window_size = self.get_default_size()

        self.settings.set_int("window-width", window_size.width)
        self.settings.set_int("window-height", window_size.height)
        self.settings.set_boolean("window-maximized", self.is_maximized())
