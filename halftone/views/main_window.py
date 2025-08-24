# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Literal, Callable, Any, Optional

from gi.repository import Adw, GLib, Gdk, Gio, Gtk

from halftone.backend.logger import Logger
from halftone.backend.utils.filetypes import get_input_formats
from halftone.constants import app_id, build_type, rootdir  # pyright: ignore
from halftone.utils.filters import get_file_filter
from halftone.views.dither_page import HalftoneDitherPage
from halftone.views.error_page import HalftoneErrorPage
from halftone.views.report_page import HalftoneReportPage
from halftone.views.about_window import HalftoneAboutWindow

logging = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/main_window.ui")
class HalftoneMainWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'HalftoneMainWindow'

    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()

    main_stack: Gtk.Stack = Gtk.Template.Child()
    open_image_button: Gtk.Button = Gtk.Template.Child()

    welcome_page_content: Adw.StatusPage = Gtk.Template.Child()

    open_image_dialog: Gtk.FileDialog = Gtk.Template.Child()
    all_filter: Gtk.FileFilter = Gtk.Template.Child()

    content = Gdk.ContentFormats.new_for_gtype(Gio.File)
    drop_target = Gtk.DropTarget(formats=content, actions=Gdk.DragAction.COPY)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Application object
        self.app: Adw.Application = kwargs['application']
        self.settings: Gio.Settings = Gio.Settings(app_id)

        self.latest_traceback: str = ""

        self.add_controller(self.drop_target)

        self.error_page: Adw.Bin = HalftoneErrorPage(self)
        self.dither_page: Adw.BreakpointBin = HalftoneDitherPage(self)
        self.report_page: Gtk.Box = HalftoneReportPage(self)

        self._setup_actions()
        self._setup_signals()
        self._setup()

    """
    Setup methods
    """

    def _setup_actions(self) -> None:
        """ Setup menu actions and accelerators. """
        self.toggle_sheet_action = self.create_action(
            name='toggle-sheet',
            callback=self.dither_page.on_toggle_sheet,
            shortcuts=['F9'],
            enabled=False,
        )

        self.save_image_action = self.create_action(
            name='save-image',
            callback=self.dither_page.on_save_image,
            shortcuts=['<Primary>S'],
            enabled=False,
        )

        self.open_image_action = self.create_action(
            name='open-image',
            callback=self.on_open_image,
            shortcuts=['<Primary>O']
        )

        self.create_action(
            name='about',
            callback=self._on_about,
            shortcuts=['<Primary>question']
        )

        self.create_action(
            name='quit',
            callback=self.destroy,
            shortcuts=['<Primary>Q', '<Primary>W']
        )

        self.create_action(
            name='show-image-externally',
            callback=lambda _action, param: self._show_image_externally(param.get_string()),
            variant_type_string="s"
        )

    def _setup_signals(self) -> None:
        self.drop_target.connect("drop",
            self.on_target_drop)

        self.drop_target.connect("enter",
            self.on_target_enter)

        self.drop_target.connect("leave",
            self.on_target_leave)

        self.connect("close-request",
            self.on_close_request)

        self.connect("unrealize",
            self._save_window_props)

    def _setup(self) -> None:
        self.set_default_icon_name(app_id)
        self.welcome_page_content.set_icon_name(app_id)

        # Set devel style
        if build_type == "debug":
            self.add_css_class("devel")

        # Prefer to use dark scheme
        Adw.StyleManager.get_default().set_color_scheme(
            color_scheme=Adw.ColorScheme.PREFER_DARK
        )

        self._setup_image_dialog()
        self._setup_main_stack()

    def _setup_image_dialog(self) -> None:
        input_formats = get_input_formats()

        supported_filter = get_file_filter(
            _("Supported image formats"), input_formats
        )

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(supported_filter)
        filters.append(self.all_filter)

        self.open_image_dialog.set_filters(filters)

    def _setup_main_stack(self) -> None:
        # TODO: Finish report page
        #self.main_stack.add_named(self.report_page, "stack_report_page")
        self.main_stack.add_named(self.error_page, "stack_error_page")
        self.main_stack.add_named(self.dither_page, "stack_dither_page")

    """
    Callbacks
    """

    @Gtk.Template.Callback()
    def on_open_image(self, *args) -> None:
        self.open_image_dialog.open(self, None, self.on_image_dialog_result)

    def on_image_dialog_result(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult
    ) -> None:
        try:
            file = dialog.open_finish(result)
        except GLib.Error as e:
            if e.code != 2: # 'Dismissed by user' error
                logging.traceback_error(
                    "Failed to finish Gtk.FileDialog open procedure.",
                    exception=e, show_exception=True)
                self.latest_traceback = logging.get_traceback(e)
                self.toast_overlay.add_toast(
                    Adw.Toast(
                        title=_("Failed to open an image. Check logs for more information")
                    )
                )
        else:
            if file is not None:
                self.load_image(file)

    def on_target_drop(
        self,
        _widget: Gtk.DropTarget,
        file: Gio.File,
        *args
    ) -> None:
        if file is not None:
            self.load_image(file)

    def on_target_enter(self, *args) -> Literal[Gdk.DragAction.COPY]:
        self.previous_stack = self.main_stack.get_visible_child_name()
        self.main_stack.set_visible_child_name('stack_drop_page')

        return Gdk.DragAction.COPY

    def on_target_leave(self, *args) -> None:
        if self.previous_stack:
            self.main_stack.set_visible_child_name(self.previous_stack)
        else:
            logging.error(
                "EDGE CASE: No stack page set as previous. Staying at current page"
            )

    def on_close_request(self, *args) -> None:
        self.dither_page.clean_preview_paintable()

    """
    Public methods
    """

    def create_action(
        self,
        name: str,
        callback: Callable[..., Any],
        shortcuts: Optional[list[str]] = None,
        enabled: bool = True,
        variant_type_string: Optional[str] = None,
    ) -> Gio.SimpleAction:
        """
        Helper method for quick action creation (with shortcut
        and typed callback support).
        """

        variant_type: Optional[GLib.VariantType] = None

        if variant_type_string is not None:
            variant_type = GLib.VariantType.new(variant_type_string)

        action: Gio.SimpleAction = Gio.SimpleAction.new(name, variant_type)
        action.connect("activate", callback)
        action.set_enabled(enabled)

        self.add_action(action)

        if shortcuts:
            self.app.set_accels_for_action(f"win.{name}", shortcuts)

        return action

    def load_image(self, file: Gio.File) -> None:
        self.show_loading_page()

        try:
            self.dither_page.load_preview_image(file)
        except (GLib.Error, TypeError) as e:
            # TODO: Modify error page for different error codes
            if isinstance(e, GLib.Error):
                if e.code == 3:  # Unrecognized image file format
                    pass

            self.toast_overlay.add_toast(
                Adw.Toast(
                    title=_("Failed to load an image. Check logs for more information")
                )
            )
            self.show_error_page()
            return

        self.show_dither_page()

    def show_loading_page(self, *args) -> None:
        self.toggle_sheet_action.set_enabled(False)
        self.open_image_action.set_enabled(False)
        self.save_image_action.set_enabled(False)
        self.main_stack.set_visible_child_name("stack_loading_page")

    def show_error_page(self, *args) -> None:
        self.toggle_sheet_action.set_enabled(False)
        self.open_image_action.set_enabled(True)
        self.save_image_action.set_enabled(False)
        self.main_stack.set_visible_child_name("stack_error_page")

    def show_dither_page(self, *args) -> None:
        self.toggle_sheet_action.set_enabled(True)
        self.open_image_action.set_enabled(True)
        self.save_image_action.set_enabled(True)
        self.main_stack.set_visible_child_name("stack_dither_page")

    """
    Private methods
    """

    def _on_about(self, *args) -> None:
        """ Show about dialog. """
        about_window = HalftoneAboutWindow(self)
        about_window.show_about()

    def _show_image_externally(self, path: str) -> None:
        """
        Launch an external application to display provided image.

        This may present an app chooser dialog to the user
        depending on system and configuration.
        """
        file = Gio.File.new_for_path(path)
        launcher = Gtk.FileLauncher.new(file)

        def _on_external_launch_result(
            launcher: Gtk.FileLauncher,
            result: Gio.AsyncResult
        ) -> None:
            try:
                launcher.launch_finish(result)
            except GLib.Error as e:
                if e.code != 2:  # 'The portal dialog was dismissed by the user' error
                    logging.error(f"Failed to launch external application: {e}")
                    self.latest_traceback = logging.get_traceback(e)
                    self.toast_overlay.add_toast(
                        Adw.Toast(
                            title=_("Failed to open preview image. Check logs for more information")
                        )
                    )

        launcher.launch(self, None, _on_external_launch_result)

    def _save_window_props(self, *args) -> None:
        window_size = self.get_default_size()

        self.settings.set_int("window-width", window_size.width)
        self.settings.set_int("window-height", window_size.height)
        self.settings.set_boolean("window-maximized", self.is_maximized())
