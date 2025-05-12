# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from enum import Enum
from pathlib import Path
from typing import Callable, Literal

from wand.exceptions import BaseError, BaseFatalError
from gi.repository import GLib, Gdk, Gsk, Gio, Gtk, Adw

from halftone.views.image_view import HalftoneImageView

from halftone.backend.utils.filetypes import FileType, get_output_formats
from halftone.backend.utils.temp import HalftoneTempFile
from halftone.backend.utils.image import calculate_height
from halftone.backend.model.output_options import OutputOptions
from halftone.backend.magick import HalftoneImageMagick
from halftone.backend.logger import Logger

from halftone.utils.killable_thread import KillableThread
from halftone.constants import rootdir # pyright: ignore

logging = Logger()

LOADING_OVERLAY_DELAY = 2000  # In milliseconds


@Gtk.Template(resource_path=f"{rootdir}/ui/dither_page.ui")
class HalftoneDitherPage(Adw.BreakpointBin):
    __gtype_name__ = "HalftoneDitherPage"

    image_viewport: Gtk.Viewport = Gtk.Template.Child()

    image_preferences_bin: Adw.Bin = Gtk.Template.Child()

    split_view: Adw.OverlaySplitView = Gtk.Template.Child()
    sidebar_view: Adw.ToolbarView = Gtk.Template.Child()

    bottom_sheet_box: Gtk.Box = Gtk.Template.Child()
    bottom_sheet: Adw.Bin = Gtk.Template.Child()

    scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()

    save_image_button: Gtk.Button = Gtk.Template.Child()

    export_format_combo: Adw.ComboRow = Gtk.Template.Child()
    dither_algorithms_combo: Adw.ComboRow = Gtk.Template.Child()

    image_width_row: Adw.SpinRow = Gtk.Template.Child()
    aspect_ratio_toggle: Adw.SwitchRow = Gtk.Template.Child()
    image_height_row: Adw.SpinRow = Gtk.Template.Child()

    image_formats_stringlist: Gtk.StringList = Gtk.Template.Child()

    color_amount_row: Adw.SpinRow = Gtk.Template.Child()

    save_image_dialog: Gtk.FileDialog = Gtk.Template.Child()

    preview_loading_overlay: Gtk.Box = Gtk.Template.Child()

    mobile_breakpoint: Adw.Breakpoint = Gtk.Template.Child()

    def __init__(self, parent: Gtk.Widget, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.settings: Gio.Settings = parent.settings

        self.app: Adw.Application = self.parent.get_application()
        self.win: Adw.ApplicationWindow = self.app.get_active_window()

        self.toast_overlay: Adw.ToastOverlay = self.parent.toast_overlay

        self.is_image_ready: bool = False
        self.is_mobile: bool = False

        self.last_x: float = 0.0
        self.last_y: float = 0.0

        self.task_id: int | None = None
        self.tasks: list[KillableThread] = []

        self.input_image_path: str = ""
        self.preview_image_path: str = ""

        self.original_texture: Gdk.Texture = None
        self.updated_texture: Gdk.Texture = None

        self.output_options: OutputOptions = OutputOptions()
        self.keep_aspect_ratio: bool = True

        self.image_view = HalftoneImageView(self.parent, None)
        self.image_viewport.set_child(self.image_view)

        self.setup_controllers()
        self.setup_gestures()
        self.setup_actions()
        self.connect_signals()
        self.setup()

    def setup_controllers(self):
        # Zoom via scroll wheels, etc.
        scroll_controller = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)

        scroll_controller.connect("scroll-end", self.on_scroll_end)
        scroll_controller.connect("scroll", self.on_scroll)

        self.scrolled_window.add_controller(scroll_controller)

    def setup_gestures(self):
        # Drag for moving image around
        drag_gesture = Gtk.GestureDrag.new()
        drag_gesture.set_button(0)

        drag_gesture.connect("drag-begin", self.on_drag_begin)
        drag_gesture.connect("drag-update", self.on_drag_update)
        drag_gesture.connect("drag-end", self.on_drag_end)

        self.scrolled_window.add_controller(drag_gesture)

    def setup_actions(self):
        """ `zoom.*` action group """

        self.install_action("zoom.in", None, self.image_view.on_zoom)
        self.install_action("zoom.out", None, self.image_view.on_zoom)

    def connect_signals(self):
        self.image_view.connect("zoom-changed",
            self.on_zoom_changed)

        self.aspect_ratio_toggle.connect("notify::active",
            self.on_aspect_ratio_toggled)

        self.dither_algorithms_combo.connect("notify::selected",
            self.on_dither_algorithm_selected)

        self.export_format_combo.connect("notify::selected",
            self.on_save_format_selected)

        self.mobile_breakpoint.connect("apply",
            self.on_breakpoint_apply)

        self.mobile_breakpoint.connect("unapply",
            self.on_breakpoint_unapply)

    def setup(self):
        # Set utility page in sidebar by default
        self.sidebar_view.set_content(self.image_preferences_bin)

        # Workaround: Set default values for SpinRows
        self.color_amount_row.set_value(10)
        self.image_width_row.set_value(1)
        self.image_height_row.set_value(1)

        # By default keep image aspect ratio
        self.aspect_ratio_toggle.set_active(True)

        self.setup_save_formats()

    def setup_save_formats(self):
        output_formats = get_output_formats(True) # TODO: Add a setting to toggle showing all formats

        for filetype in output_formats:
            self.image_formats_stringlist.append(filetype.as_extension())

        self.export_format_combo.set_selected(output_formats.index(FileType.PNG))

    """ Main functions """

    def update_preview_image(self, path: str, output_options: OutputOptions,
                                   run_delay: bool = True, callback: Callable | None = None):
        self.is_image_ready = False

        if run_delay:
            GLib.timeout_add(LOADING_OVERLAY_DELAY, self.on_awaiting_image_load)
        else:
            self.on_awaiting_image_load()

        if self.preview_image_path:
            self.clean_preview_paintable()

        self.output_options = output_options

        try:
            self.preview_image_path = HalftoneImageMagick().dither_image(path, self.output_options)
        except (BaseError, BaseFatalError) as e:
            logging.traceback_error(
                "Failed to finish ImageMagick dithering operations.",
                exception=e, show_exception=True)
            self.win.latest_traceback = logging.get_traceback(e)
            self.win.show_error_page()  # TODO: Temporary hack: Replace with an error stack page inside dither page
            return

        try:
            self.set_updated_texture(self.preview_image_path)
        except (GLib.Error, TypeError):
            self.win.show_error_page()  # TODO: Temporary hack: Replace with an error stack page inside dither page
            return

        self.on_successful_image_load()
        self.is_image_ready = True

        if callback:
            callback()

    # NOTE: Use this only if you initially load the picture (eg. from file dialog)
    def load_preview_image(self, file: Gio.File):
        self.input_image_path = file.get_path()

        self.set_original_texture(self.input_image_path)

        self.set_size_spins(self.original_texture.get_width(),
                            self.original_texture.get_height())

        self.start_task(self.update_preview_image,
                        self.input_image_path,
                        self.output_options,
                        False,
                        self.on_successful_image_load)

    def save_image(self, paintable: Gdk.Paintable, output_path: str,
                         output_options: OutputOptions, callback: Callable):
        self.win.show_loading_page()

        image_bytes = paintable.save_to_tiff_bytes()

        HalftoneImageMagick().save_image(image_bytes.get_data(), output_path, output_options)

        if callback:
            callback()

        logging.debug("Saving done!")

        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Image dithered successfully!"),
                button_label=_("Open Image"),
                action_name="app.show-image-externally",
                action_target=GLib.Variant("s", output_path))
        )

    """ Callbacks """

    @Gtk.Template.Callback()
    def on_color_amount_changed(self, widget: Adw.SpinRow):
        new_color_amount = self.get_color_amount_pref(widget)

        if new_color_amount == self.output_options.color_amount:
            return

        self.output_options.color_amount = new_color_amount

        if self.original_texture:
            self.start_task(self.update_preview_image,
                            self.input_image_path,
                            self.output_options,
                            True,
                            self.on_successful_image_load)

    @Gtk.Template.Callback()
    def on_brightness_changed(self, widget: Adw.SpinRow):
        new_brightness = int(widget.props.value)

        if new_brightness == self.output_options.brightness:
            return

        self.output_options.brightness = new_brightness

        self.start_task(self.update_preview_image,
                        self.input_image_path,
                        self.output_options,
                        True,
                        self.on_successful_image_load)

    @Gtk.Template.Callback()
    def on_contrast_changed(self, widget: Adw.SpinRow):
        new_contrast = int(widget.props.value)

        if new_contrast == self.output_options.contrast:
            return

        self.output_options.contrast = new_contrast

        self.start_task(self.update_preview_image,
                        self.input_image_path,
                        self.output_options,
                        True,
                        self.on_successful_image_load)

    @Gtk.Template.Callback()
    def on_image_width_changed(self, widget: Adw.SpinRow):
        new_width = self.get_image_width_pref(widget)

        if new_width == self.output_options.width:
            return

        self.output_options.width = new_width

        if self.original_texture:
            img_height = self.original_texture.get_height()
            img_width = self.original_texture.get_width()

            if self.aspect_ratio_toggle.get_active() is True:
                new_height = calculate_height(img_width, img_height, new_width)
                self.output_options.height = new_height
                self.image_height_row.set_value(new_height)

            self.start_task(self.update_preview_image,
                            self.input_image_path,
                            self.output_options,
                            True,
                            self.on_successful_image_load)

    @Gtk.Template.Callback()
    def on_image_height_changed(self, widget: Adw.SpinRow):
        new_height = self.get_image_height_pref(widget)

        if new_height == self.output_options.height:
            return

        self.output_options.height = new_height

        if self.original_texture:
            if not self.keep_aspect_ratio:
                self.start_task(self.update_preview_image,
                                self.input_image_path,
                                self.output_options,
                                True,
                                self.on_successful_image_load)

    def on_save_image(self, *args):
        file_extension = self.get_output_format_suffix()
        file_display_name = Path(self.input_image_path).stem

        output_filename = f"halftone-{file_display_name}.{file_extension}"
        logging.debug(f"Output filename: {output_filename}")

        self.save_image_dialog.set_initial_name(output_filename)
        self.save_image_dialog.save(self.win, None, self.on_image_dialog_result)

    def on_zoom_changed(self, *args):
        current_filter = self.image_view.scaling_filter
        nearest = Gsk.ScalingFilter.NEAREST
        linear = Gsk.ScalingFilter.LINEAR

        if self.image_view.scale >= 1.0 and current_filter is not nearest:
            self.image_view.scaling_filter = nearest
        elif self.image_view.scale < 1.0 and current_filter is not linear:
            self.image_view.scaling_filter = linear

        self.action_set_enabled("zoom.in", self.image_view.can_zoom_in)
        self.action_set_enabled("zoom.out", self.image_view.can_zoom_out)

    def on_scroll_end(self, controller: Gtk.EventControllerScroll):
        # Avoid kinetic scrolling in scrolled window after zooming
        # Some gestures can become buggy if deceleration is not canceled
        if controller.get_current_event_state() == (Gdk.ModifierType.CONTROL_MASK):
            self.cancel_deceleration()

    def on_scroll(self, controller: Gtk.EventControllerScroll, _x: float, y: float) -> bool:
        state = controller.get_current_event_state()

        # Use Ctrl key as a modifier for vertical scrolling and Shift for horizontal
        if (state == Gdk.ModifierType.CONTROL_MASK or
            state == Gdk.ModifierType.SHIFT_MASK):
            return Gdk.EVENT_PROPAGATE

        if y < 0.0:
            self.image_view.zoom_in()
        else:
            self.image_view.zoom_out()

        # Do not propagate event to scrolled window
        return Gdk.EVENT_STOP

    def on_drag_begin(self, gesture: Gtk.GestureDrag, _x: float, _y: float) -> None:
        device = gesture.get_device()

        # Allow only left and middle button
        if (not gesture.get_current_button() in [1, 2] or
            # Drag gesture for touchscreens is handled by ScrolledWindow
            device and device.get_source() == Gdk.InputSource.TOUCHSCREEN):
            gesture.set_state(Gtk.EventSequenceState.DENIED)
            return

        self.image_view.set_cursor_from_name("grabbing")
        self.last_x = 0.0
        self.last_y = 0.0

    def on_drag_update(self, _gesture: Gtk.GestureDrag, x: float, y: float) -> None:
        self.update_adjustment(x, y)
        self.last_x = x
        self.last_y = y

    def on_drag_end(self, _gesture: Gtk.GestureDrag, _x: float, _y: float) -> None:
        self.image_view.set_cursor(None)
        self.last_x = 0.0
        self.last_y = 0.0

    def on_toggle_sheet(self, action: Gio.SimpleAction, *args):
        if self.is_mobile:
            if self.bottom_sheet_box.props.visible:
                self.bottom_sheet_box.set_visible(False)
                return

            self.bottom_sheet_box.set_visible(True)
        else:
            if self.split_view.props.show_sidebar:
                self.split_view.set_show_sidebar(False)
                return

            self.split_view.set_show_sidebar(True)

    def on_aspect_ratio_toggled(self, widget: Adw.SwitchRow, *args):
        if widget.props.active is True:
            self.keep_aspect_ratio = True
            #widget.props.icon_name = "chain-link-symbolic"
            #widget.props.tooltip_text = _("Keep aspect ratio")
            self.image_height_row.set_sensitive(False)

        if widget.props.active is False:
            self.keep_aspect_ratio = False
            #widget.props.icon_name = "chain-link-loose-symbolic"
            #widget.props.tooltip_text = _("Don't keep aspect ratio")
            self.image_height_row.set_sensitive(True)

    def on_image_dialog_result(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult):
        try:
            file = dialog.save_finish(result)
        except GLib.Error as e:
            if e.code != 2: # 'Dismissed by user' error
                logging.traceback_error(
                    "Failed to finish Gtk.FileDialog save procedure.",
                    exception=e, show_exception=True)
                self.win.latest_traceback = logging.get_traceback(e)
                self.toast_overlay.add_toast(
                    Adw.Toast(title=_("Failed to save an image. Check logs for more information"))
                )
        else:
            if file is not None:
                self.start_task(self.save_image,
                                self.updated_texture,
                                file.get_path(),
                                self.output_options,
                                self.win.show_dither_page)

    def on_dither_algorithm_selected(self, widget: Adw.ComboRow, *args):
        algorithm_string = self.get_dither_algorithm_pref(widget)

        self.output_options.algorithm = algorithm_string

        if self.original_texture:
            self.start_task(self.update_preview_image,
                            self.input_image_path,
                            self.output_options,
                            True,
                            self.on_successful_image_load)

    def on_save_format_selected(self, widget: Adw.ComboRow, *args):
        selected_format = widget.props.selected
        format_string = self.image_formats_stringlist.get_string(selected_format)

        self.output_options.output_format = format_string

    def on_successful_image_load(self, *args):
        self.preview_loading_overlay.set_visible(False)
        self.image_view.remove_css_class("preview-loading-blur")
        self.save_image_button.set_sensitive(True)

    def on_awaiting_image_load(self, *args):
        if not self.is_image_ready:
            self.preview_loading_overlay.set_visible(True)
            self.image_view.add_css_class("preview-loading-blur")
            self.save_image_button.set_sensitive(False)

    def on_breakpoint_apply(self, *args):
        self.sidebar_view.set_content(None)
        self.bottom_sheet.set_child(self.image_preferences_bin)

        self.is_mobile = True

    def on_breakpoint_unapply(self, *args):
        self.bottom_sheet.set_child(None)
        self.sidebar_view.set_content(self.image_preferences_bin)

        self.is_mobile = False

    """ Module-specific helpers """

    def set_original_texture(self, path: str):
        try:
            self.original_texture = Gdk.Texture.new_from_filename(path)
        except GLib.Error as e:
            logging.traceback_error(
                "Failed to construct new Gdk.Texture from path.",
                exception=e, show_exception=True)
            self.win.latest_traceback = logging.get_traceback(e)
            raise
        except TypeError as e:
            logging.traceback_error(
                "Missing Gdk.Texture decoding plugin for requested image.",
                exception=e, show_exception=True)
            self.win.latest_traceback = logging.get_traceback(e)
            raise

        self.image_view.texture = self.original_texture

    def set_updated_texture(self, path: str):
        try:
            self.updated_texture = Gdk.Texture.new_from_filename(path)
        except GLib.Error as e:
            logging.traceback_error(
                "Failed to construct new Gdk.Texture from path.",
                exception=e, show_exception=True)
            self.win.latest_traceback = logging.get_traceback(e)
            raise
        except TypeError as e:
            logging.traceback_error(
                "Missing Gdk.Texture decoding plugin for requested image.",
                exception=e, show_exception=True)
            self.win.latest_traceback = logging.get_traceback(e)
            raise

        self.image_view.texture = self.updated_texture

    def clean_preview_paintable(self):
        try:
            HalftoneTempFile().delete_temp_file(self.preview_image_path)
        except FileNotFoundError as e:
            logging.warning(f"Failed to delete temporary file. Path: {self.preview_image_path} Error: {e}")

    def get_output_format_suffix(self) -> str:
        selected_format = self.export_format_combo.props.selected
        format_string = self.image_formats_stringlist.get_string(selected_format)

        # TODO: Possible edge case; Make sure to return something when string is None
        return format_string

    def get_color_amount_pref(self, widget: Adw.SpinRow) -> int:
        color_amount = int(widget.props.value)
        return color_amount

    def get_image_width_pref(self, widget: Adw.SpinRow) -> int:
        new_width = int(widget.props.value)
        return new_width

    def get_image_height_pref(self, widget: Adw.SpinRow) -> int:
        new_height = int(widget.props.value)
        return new_height

    def get_dither_algorithm_pref(self, widget: Adw.ComboRow) -> Literal['floyd_steinberg', 'riemersma', 'ordered'] | None:
        selected_algorithm = widget.props.selected

        class selectedAlgo(Enum):
            FLOYD_STEINBERG = 0
            RIEMERSMA = 1
            ORDERED = 2

        def __get_algorithm_string() -> Literal['floyd_steinberg', 'riemersma', 'ordered'] | None:
            if selected_algorithm == selectedAlgo.FLOYD_STEINBERG.value:
                return "floyd_steinberg"
            if selected_algorithm == selectedAlgo.RIEMERSMA.value:
                return "riemersma"
            if selected_algorithm == selectedAlgo.ORDERED.value:
                return "ordered"

            return None

        algorithm_string = __get_algorithm_string()

        return algorithm_string

    def set_size_spins(self, width: int, height: int):
        self.image_width_row.set_value(width)
        self.image_height_row.set_value(height)

    def update_adjustment(self, x: float, y: float) -> None:
        self.scrolled_window.get_hadjustment().set_value(
            self.scrolled_window.get_hadjustment().get_value() - x + self.last_x
        )
        self.scrolled_window.get_vadjustment().set_value(
            self.scrolled_window.get_vadjustment().get_value() - y + self.last_y
        )

    def cancel_deceleration(self) -> None:
        self.scrolled_window.set_kinetic_scrolling(False)
        self.scrolled_window.set_kinetic_scrolling(True)

    def start_task(self, task: Callable, *args): #callback: callable
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
                Adw.Toast(title=_("Failed to load preview image. Check logs for more information"))
            )
            self.win.latest_traceback = logging.get_traceback(e)
