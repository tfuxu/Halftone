# Copyright 2023, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import GLib, Gdk, Gio, Gtk, Adw

from pixely.views.dither_page import HalftoneDitherPage
from pixely.views.report_page import HalftoneReportPage

from pixely.utils.filters import get_file_filter, supported_input_formats
from pixely.constants import rootdir, app_id, build_type


@Gtk.Template(resource_path=f"{rootdir}/ui/main_window.ui")
class HalftoneMainWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'HalftoneMainWindow'

    toast_overlay = Gtk.Template.Child()

    main_stack = Gtk.Template.Child()
    open_image_button = Gtk.Template.Child()

    open_image_chooser = Gtk.Template.Child()
    all_filter = Gtk.Template.Child()

    content = Gdk.ContentFormats.new_for_gtype(Gio.File)
    drop_target = Gtk.DropTarget(formats=content, actions=Gdk.DragAction.COPY)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Application object
        self.app = kwargs['application']
        self.settings = Gio.Settings(app_id)

        self.add_controller(self.drop_target)

        self.dither_page = HalftoneDitherPage(self)
        self.report_page = HalftoneReportPage(self)

        self.setup_actions()
        self.setup_signals()
        self.setup()

    def setup_actions(self):
        """ Setup menu actions and accelerators. """

        self.open_image_action = Gio.SimpleAction.new('open-image', None)
        self.open_image_action.connect('activate', self.on_open_image)
        self.app.add_action(self.open_image_action)

        self.save_image_action = Gio.SimpleAction.new('save-image', None)
        self.save_image_action.connect('activate', self.dither_page.on_save_image)
        self.app.add_action(self.save_image_action)

        # By default disable save image action
        self.save_image_action.set_enabled(False)

    def setup_signals(self):
        self.drop_target.connect("drop",
            self.on_target_drop)

        self.drop_target.connect("enter",
            self.on_target_enter)

        self.drop_target.connect("leave",
            self.on_target_leave)

        self.open_image_chooser.connect("response",
            self.on_image_chooser_response)

        self.connect("unrealize",
            self.save_window_props)

    def setup(self):
        self.set_default_icon_name(app_id)

        # Set devel style
        if build_type == "debug":
            self.add_css_class("devel")

        self.setup_image_chooser()
        self.setup_main_stack()

    def setup_image_chooser(self):
        self.open_image_chooser.set_transient_for(self)
        self.open_image_chooser.set_action(Gtk.FileChooserAction.OPEN)

        self.open_image_chooser.add_filter(get_file_filter(_("Supported image formats"),
                                                            supported_input_formats))

        self.open_image_chooser.add_filter(self.all_filter)

    def setup_main_stack(self):
        self.main_stack.add_named(self.report_page, "stack_report_page")
        self.main_stack.add_named(self.dither_page, "stack_dither_page")

    def load_image(self, file: Gio.File):
        self.show_loading_page()
        try:
            self.dither_page.load_preview_image(file)
        except GLib.GError as e:
            # TODO: Modify error page for different error codes
            if e.code == 3:  # Unrecognized image file format
                pass
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("Failed to load an image"))
            )
        else:
            self.show_dither_page()

    @Gtk.Template.Callback()
    def on_open_image(self, *args):
        self.open_image_chooser.show()

    def on_image_chooser_response(self, widget, response):
        if response == Gtk.ResponseType.ACCEPT:
            input_file = widget.get_file()
        widget.hide()

        if response == Gtk.ResponseType.ACCEPT:
            self.load_image(input_file)

    def on_target_drop(self, widget, file: Gio.File, *args):
        self.load_image(file)

    def on_target_enter(self, *args):
        self.previous_stack = self.main_stack.get_visible_child_name()
        self.main_stack.set_visible_child_name('stack_drop_page')
        return Gdk.DragAction.COPY

    def on_target_leave(self, *args):
        self.main_stack.set_visible_child_name(self.previous_stack)

    def show_loading_page(self, *args):
        self.open_image_action.set_enabled(False)
        self.save_image_action.set_enabled(False)
        self.main_stack.set_visible_child_name("stack_loading_page")

    def show_error_page(self, *args):
        self.open_image_action.set_enabled(True)
        self.save_image_action.set_enabled(False)
        self.main_stack.set_visible_child_name("stack_error_page")

    def show_dither_page(self, *args):
        self.open_image_action.set_enabled(True)
        self.save_image_action.set_enabled(True)
        self.main_stack.set_visible_child_name("stack_dither_page")

    def save_window_props(self, *args):
        window_size = self.get_default_size()

        self.settings.set_int("window-width", window_size.width)
        self.settings.set_int("window-height", window_size.height)
        self.settings.set_boolean("window-maximized", self.is_maximized())
