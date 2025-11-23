# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from pathlib import Path

from gi.repository import Adw, Gly, GlyGtk4, GLib, Gdk, Gio, Gtk
from wand.exceptions import BaseError, BaseFatalError

from halftone.backend.logger import Logger
from halftone.backend.magick import HalftoneImageMagick
from halftone.backend.model.image_options import ImageOptionsModel
from halftone.backend.utils.temp import delete_temp_file
from halftone.constants import rootdir  # pyright: ignore
from halftone.utils.killable_thread import KillableThread
from halftone.views.image_options_view import HalftoneImageOptionsView
from halftone.views.image_view import HalftoneImageView

logging = Logger()

LOADING_OVERLAY_DELAY = 2000  # In milliseconds


@Gtk.Template(resource_path=f"{rootdir}/ui/dither_page.ui")
class HalftoneDitherPage(Adw.BreakpointBin):
    __gtype_name__ = "HalftoneDitherPage"

    multi_layout_view: Adw.MultiLayoutView = Gtk.Template.Child()
    desktop_split_view: Adw.OverlaySplitView = Gtk.Template.Child()

    image_view: HalftoneImageView = Gtk.Template.Child()

    save_image_dialog: Gtk.FileDialog = Gtk.Template.Child()

    mobile_options_revealer: Gtk.Revealer = Gtk.Template.Child()
    mobile_breakpoint: Adw.Breakpoint = Gtk.Template.Child()

    def __init__(self, parent: Gtk.Widget, **kwargs) -> None:
        super().__init__(**kwargs)

        self.parent = parent
        self.settings: Gio.Settings = parent.settings

        self.app: Adw.Application = self.parent.get_application()
        self.win: Adw.ApplicationWindow = self.app.get_active_window()

        self.toast_overlay: Adw.ToastOverlay = self.parent.toast_overlay

        self.is_image_ready: bool = False
        self.is_mobile: bool = False

        self.task_id: int | None = None
        self.tasks: list[KillableThread] = []

        self.input_image_path: str = ""
        self.preview_image_path: str = ""

        self.original_texture: Gdk.Texture
        self.updated_texture: Gdk.Texture | None = None

        self.image_options: ImageOptionsModel = ImageOptionsModel()

        self.image_options_view = HalftoneImageOptionsView(
            self.parent,
            self.image_options,
            self.start_image_update_task
        )

        self._connect_signals()
        self._setup()

    """
    Setup methods
    """

    def _connect_signals(self) -> None:
        self.mobile_breakpoint.connect("apply",
            self.on_breakpoint_apply)

        self.mobile_breakpoint.connect("unapply",
            self.on_breakpoint_unapply)

    def _setup(self) -> None:
        self.multi_layout_view.set_child("options", self.image_options_view)

    """
    Callbacks
    """

    def on_save_image(self, *args) -> None:
        file_extension = self._get_output_format_suffix()
        file_display_name = Path(self.input_image_path).stem

        output_filename = f"halftone-{file_display_name}.{file_extension}"
        logging.debug(f"Output filename: {output_filename}")

        self.save_image_dialog.set_initial_name(output_filename)
        self.save_image_dialog.save(self.win, None, self.on_image_dialog_result)

    def on_toggle_sheet(self, _action: Gio.SimpleAction, *args) -> None:
        if self.is_mobile:
            if self.mobile_options_revealer.props.reveal_child:
                self.mobile_options_revealer.set_reveal_child(False)
                return

            self.mobile_options_revealer.set_reveal_child(True)
        else:
            if self.desktop_split_view.props.show_sidebar:
                self.desktop_split_view.set_show_sidebar(False)
                return

            self.desktop_split_view.set_show_sidebar(True)

    def on_image_dialog_result(
        self,
        dialog: Gtk.FileDialog,
        result: Gio.AsyncResult
    ) -> None:
        try:
            file = dialog.save_finish(result)
        except GLib.Error as e:
            if e.code != 2: # 'Dismissed by user' error
                logging.traceback_error(
                    "Failed to finish Gtk.FileDialog save procedure.",
                    exception=e, show_exception=True)
                self.win.latest_traceback = logging.get_traceback(e)
                self.toast_overlay.add_toast(
                    Adw.Toast(
                        title=_("Failed to save an image. Check logs for more information")
                    )
                )
        else:
            if file is not None:
                self._start_task(self._save_image,
                                 self.updated_texture,
                                 file.get_path(),
                                 self.image_options,
                                 self.win.show_dither_page)

    def on_successful_image_load(self, *args) -> None:
        self.image_view.loading_screen_box.set_visible(False)
        self.image_view.image_widget.remove_css_class("preview-loading-blur")
        #self.image_options_view.save_image_button.set_sensitive(True)

    def on_awaiting_image_load(self, *args) -> None:
        if not self.is_image_ready:
            self.image_view.loading_screen_box.set_visible(True)
            self.image_view.image_widget.add_css_class("preview-loading-blur")
            #self.image_options_view.save_image_button.set_sensitive(False)

    def on_breakpoint_apply(self, *args) -> None:
        self.image_view.toggle_sheet_button.set_icon_name("sheet-show-bottom-symbolic")
        self.image_view.toggle_sheet_button.set_tooltip_text(_("Toggle Bottom Sheet"))

        self.is_mobile = True

    def on_breakpoint_unapply(self, *args) -> None:
        self.image_view.toggle_sheet_button.set_icon_name("sidebar-show-left-symbolic")
        self.image_view.toggle_sheet_button.set_tooltip_text(_("Toggle Sidebar"))

        self.is_mobile = False

    """
    Public methods
    """

    # NOTE: Use this only if you initially load the picture (eg. from file dialog)
    def load_preview_image(self, file: Gio.File) -> None:
        self.input_image_path = file.get_path()

        self._set_original_texture(self.input_image_path)

        self._set_size_spins(self.original_texture.get_width(),
                            self.original_texture.get_height())

        self.start_image_update_task(run_delay=False)

    def clean_preview_paintable(self) -> None:
        try:
            delete_temp_file(self.preview_image_path)
        except FileNotFoundError as e:
            logging.warning(
                f"Failed to delete temporary file. Path: {self.preview_image_path} Error: {e}"
            )

    def start_image_update_task(self, run_delay: bool = True) -> None:
        self._start_task(
            self._update_preview_image,
            self.input_image_path,
            self.image_options,
            run_delay,
            self.on_successful_image_load
        )

    """
    Private methods
    """

    def _update_preview_image(
        self,
        path: str,
        image_options: ImageOptionsModel,
        run_delay: bool = True,
        callback: Callable | None = None
    ) -> None:
        self.is_image_ready = False

        if run_delay:
            GLib.timeout_add(LOADING_OVERLAY_DELAY, self.on_awaiting_image_load)
        else:
            self.on_awaiting_image_load()

        if self.preview_image_path:
            self.clean_preview_paintable()

        self.image_options = image_options

        try:
            self.preview_image_path = HalftoneImageMagick().dither_image(
                path=path,
                image_options=self.image_options
            )
        except (BaseError, BaseFatalError) as e:
            logging.traceback_error(
                "Failed to finish ImageMagick dithering operations.",
                exception=e, show_exception=True)
            self.win.latest_traceback = logging.get_traceback(e)
            self.win.show_error_page()  # TODO: Temporary hack: Replace with an error stack page inside dither page
            return

        try:
            self._set_updated_texture(self.preview_image_path)
        except (GLib.Error, TypeError):
            self.win.show_error_page()  # TODO: Temporary hack: Replace with an error stack page inside dither page
            return

        self.on_successful_image_load()
        self.is_image_ready = True

        if callback:
            callback()

    def _save_image(
        self,
        paintable: Gdk.Paintable,
        output_path: str,
        image_options: ImageOptionsModel,
        callback: Callable
    ) -> None:
        self.win.show_loading_page()

        image_bytes = paintable.save_to_tiff_bytes()

        HalftoneImageMagick().save_image(
            blob=image_bytes.get_data(),
            output_filename=output_path,
            image_options=image_options
        )

        if callback:
            callback()

        logging.debug("Saving done!")

        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Image dithered successfully!"),
                button_label=_("Open Image"),
                action_name="win.show-image-externally",
                action_target=GLib.Variant("s", output_path))
        )

    def _set_original_texture(self, path: str) -> None:
        self._set_texture(path, as_original=True)

    def _set_updated_texture(self, path: str) -> None:
        self._set_texture(path)

    def _set_texture(self, path: str, as_original: bool = False) -> None:
        image_widget = self.image_view.image_widget

        file = Gio.File.new_for_path(path)
        loader = Gly.Loader.new(file)

        try:
            image = loader.load()  # TODO: Replace with async variant
        except GLib.Error as e:
            logging.traceback_error(
                "Failed to load an image using Glycin.",
                exception=e, show_exception=True)
            self.win.latest_traceback = logging.get_traceback(e)
            raise

        try:
            frame = image.next_frame() # TODO: Replace with async variant
        except GLib.Error as e:
            logging.traceback_error(
                "Failed to request the next frame of the Glycin image.",
                exception=e, show_exception=True)
            self.win.latest_traceback = logging.get_traceback(e)
            raise

        texture = GlyGtk4.frame_get_texture(frame)

        current_zoom = image_widget.zoom
        current_scaling_filter = image_widget.scaling_filter

        image_widget.texture = texture

        if as_original:
            self.original_texture = texture
            self.image_options_view.original_texture = texture
        else:
            self.updated_texture = texture
            image_widget.zoom = current_zoom
            image_widget.scaling_filter = current_scaling_filter

    def _get_output_format_suffix(self) -> str:
        selected_format = self.image_options_view.export_format_combo.props.selected
        format_string = self.image_options_view.image_formats_stringlist.get_string(selected_format)

        # NOTE: This should only happen if the list isn't populated
        if format_string is None:
            format_string = "png"

        return format_string.lower()

    # TODO: Remove this method, as the image_height_row doesn't exist
    def _set_size_spins(self, width: int, height: int) -> None:
        self.image_options_view.image_width_row.set_value(width)

    def _start_task(self, task: Callable, *args) -> None:
        logging.debug("Starting new async task")

        for t in self.tasks:
            t.kill()

        self.tasks = []

        try:
            thread = KillableThread(
                target=task,
                args=(
                    #callback,
                    *args,
                ))

            thread.daemon = True
            thread.start()
            self.task_id = thread.ident
            self.tasks.append(thread)
        except GLib.Error as e:
            logging.traceback_error(
                "Failed to finish async task.",
                exception=e, show_exception=True)
            self.toast_overlay.add_toast(
                Adw.Toast(
                    title=_("Failed to load preview image. Check logs for more information")
                )
            )
            self.win.latest_traceback = logging.get_traceback(e)
