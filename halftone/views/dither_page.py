# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from pathlib import Path

from gi.repository import Adw, GLib, Gdk, Gio, Gsk, Gtk
from wand.exceptions import BaseError, BaseFatalError

from halftone.backend.logger import Logger
from halftone.backend.magick import HalftoneImageMagick
from halftone.backend.model.output_options import OutputOptions
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

    shortcut_controller: Gtk.ShortcutController = Gtk.Template.Child()

    image_viewport: Gtk.Viewport = Gtk.Template.Child()

    split_view: Adw.OverlaySplitView = Gtk.Template.Child()
    sidebar_view: Adw.ToolbarView = Gtk.Template.Child()

    bottom_sheet_box: Gtk.Box = Gtk.Template.Child()
    bottom_sheet: Adw.Bin = Gtk.Template.Child()

    scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()

    save_image_dialog: Gtk.FileDialog = Gtk.Template.Child()

    preview_loading_overlay: Gtk.Box = Gtk.Template.Child()

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

        self.zoom_target: float = 1.0

        self.last_x: float = 0.0
        self.last_y: float = 0.0

        self.task_id: int | None = None
        self.tasks: list[KillableThread] = []

        self.input_image_path: str = ""
        self.preview_image_path: str = ""

        self.original_texture: Gdk.Texture = None
        self.updated_texture: Gdk.Texture = None

        self.output_options: OutputOptions = OutputOptions()

        self.image_view = HalftoneImageView(self.parent, None)
        self.image_viewport.set_child(self.image_view)

        self.image_options_view = HalftoneImageOptionsView(
            self.parent,
            self.output_options,
            self.start_image_update_task
        )

        self._setup_controllers()
        self._setup_gestures()
        self._setup_actions()
        self._connect_signals()
        self._setup()

    """
    Setup methods
    """

    def _setup_controllers(self) -> None:
        # Zoom via scroll wheels, etc.
        scroll_controller = Gtk.EventControllerScroll.new(
            flags=Gtk.EventControllerScrollFlags.BOTH_AXES
        )

        scroll_controller.connect("scroll", self.on_scroll)
        scroll_controller.connect("scroll-end", self.on_scroll_end)

        self.scrolled_window.add_controller(scroll_controller)

    def _setup_gestures(self) -> None:
        # Drag for moving image around
        drag_gesture = Gtk.GestureDrag.new()
        drag_gesture.set_button(0)

        drag_gesture.connect("drag-begin", self.on_drag_begin)
        drag_gesture.connect("drag-update", self.on_drag_update)
        drag_gesture.connect("drag-end", self.on_drag_end)

        self.scrolled_window.add_controller(drag_gesture)

        # Zoom using 2-finger pinch/zoom gestures
        zoom_gesture = Gtk.GestureZoom.new()

        zoom_gesture.connect("begin", self.on_zoom_begin)
        zoom_gesture.connect("scale-changed", self.on_zoom_scale_changed)

        self.scrolled_window.add_controller(zoom_gesture)

    def _setup_actions(self) -> None:
        """ `zoom.*` action group """

        self.install_action("zoom.in", None, self.image_view.on_zoom)
        self.install_action("zoom.out", None, self.image_view.on_zoom)

        # Add bindings for `zoom.*` action group

        zoom_in_shortcuts = [
            (Gdk.KEY_equal, []),
            (Gdk.KEY_equal, [Gdk.ModifierType.CONTROL_MASK]),
            (Gdk.KEY_plus, []),
            (Gdk.KEY_plus, [Gdk.ModifierType.CONTROL_MASK]),
            (Gdk.KEY_KP_Add, []),
            (Gdk.KEY_KP_Add, [Gdk.ModifierType.CONTROL_MASK])
        ]
        self._add_shortcuts("zoom.in", zoom_in_shortcuts)

        zoom_out_shortcuts = [
            (Gdk.KEY_minus, []),
            (Gdk.KEY_minus, [Gdk.ModifierType.CONTROL_MASK]),
            (Gdk.KEY_KP_Subtract, []),
            (Gdk.KEY_KP_Subtract, [Gdk.ModifierType.CONTROL_MASK]),
        ]
        self._add_shortcuts("zoom.out", zoom_out_shortcuts)

    def _connect_signals(self) -> None:
        self.image_view.connect("zoom-changed",
            self.on_zoom_changed)

        self.mobile_breakpoint.connect("apply",
            self.on_breakpoint_apply)

        self.mobile_breakpoint.connect("unapply",
            self.on_breakpoint_unapply)

    def _setup(self) -> None:
        # Set utility page in sidebar by default
        self.sidebar_view.set_content(self.image_options_view)

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

    def on_zoom_changed(self, *args) -> None:
        current_filter = self.image_view.scaling_filter
        nearest = Gsk.ScalingFilter.NEAREST
        linear = Gsk.ScalingFilter.LINEAR

        if self.image_view.scale >= 1.0 and current_filter is not nearest:
            self.image_view.scaling_filter = nearest
        elif self.image_view.scale < 1.0 and current_filter is not linear:
            self.image_view.scaling_filter = linear

        self.action_set_enabled("zoom.in", self.image_view.can_zoom_in)
        self.action_set_enabled("zoom.out", self.image_view.can_zoom_out)

    def on_scroll(
        self,
        controller: Gtk.EventControllerScroll,
        _x: float,
        y: float
    ) -> bool:
        state = controller.get_current_event_state()
        device = controller.get_current_event_device()

        if device and device.get_source() == Gdk.InputSource.TOUCHPAD:
            # Touchpads do zoom via gestures, expect when Ctrl key is pressed
            if state != Gdk.ModifierType.CONTROL_MASK:
                # Propagate event to scrolled window
                return Gdk.EVENT_PROPAGATE
        else:
            # Use Ctrl key as a modifier for vertical scrolling and Shift for horizontal
            if (state == Gdk.ModifierType.CONTROL_MASK or
                state == Gdk.ModifierType.SHIFT_MASK):
                # Propagate event to scrolled window
                return Gdk.EVENT_PROPAGATE

        if y < 0.0:
            self.image_view.zoom_in()
        else:
            self.image_view.zoom_out()

        # Do not propagate event to scrolled window
        return Gdk.EVENT_STOP

    def on_scroll_end(self, controller: Gtk.EventControllerScroll) -> None:
        # Avoid kinetic scrolling in scrolled window after zooming
        # Some gestures can become buggy if deceleration is not canceled
        if controller.get_current_event_state() == Gdk.ModifierType.CONTROL_MASK:
            self._cancel_deceleration()

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
        self._update_adjustment(x, y)
        self.last_x = x
        self.last_y = y

    def on_drag_end(self, _gesture: Gtk.GestureDrag, _x: float, _y: float) -> None:
        self.image_view.set_cursor(None)
        self.last_x = 0.0
        self.last_y = 0.0

    def on_zoom_begin(
        self,
        _gesture: Gtk.GestureZoom,
        _sequence: Gdk.EventSequence
    ) -> None:
        self._cancel_deceleration()
        self.zoom_target = self.image_view.scale

    def on_zoom_scale_changed(self, _gesture: Gtk.GestureZoom, scale: float) -> None:
        self.image_view.scale = self.zoom_target * scale

    def on_toggle_sheet(self, action: Gio.SimpleAction, *args) -> None:
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
                                 self.output_options,
                                 self.win.show_dither_page)

    def on_successful_image_load(self, *args) -> None:
        self.preview_loading_overlay.set_visible(False)
        self.image_view.remove_css_class("preview-loading-blur")
        self.image_options_view.save_image_button.set_sensitive(True)

    def on_awaiting_image_load(self, *args) -> None:
        if not self.is_image_ready:
            self.preview_loading_overlay.set_visible(True)
            self.image_view.add_css_class("preview-loading-blur")
            self.image_options_view.save_image_button.set_sensitive(False)

    def on_breakpoint_apply(self, *args) -> None:
        self.sidebar_view.set_content(None)
        self.bottom_sheet.set_child(self.image_options_view)

        self.is_mobile = True

    def on_breakpoint_unapply(self, *args) -> None:
        self.bottom_sheet.set_child(None)
        self.sidebar_view.set_content(self.image_options_view)

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
            self.output_options,
            run_delay,
            self.on_successful_image_load
        )

    """
    Private methods
    """

    def _update_preview_image(
        self,
        path: str,
        output_options: OutputOptions,
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

        self.output_options = output_options

        try:
            self.preview_image_path = HalftoneImageMagick().dither_image(
                path=path,
                output_options=self.output_options
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
        output_options: OutputOptions,
        callback: Callable
    ) -> None:
        self.win.show_loading_page()

        image_bytes = paintable.save_to_tiff_bytes()

        HalftoneImageMagick().save_image(
            blob=image_bytes.get_data(),
            output_filename=output_path,
            output_options=output_options
        )

        if callback:
            callback()

        logging.debug("Saving done!")

        self.toast_overlay.add_toast(
            Adw.Toast(title=_("Image dithered successfully!"),
                button_label=_("Open Image"),
                action_name="app.show-image-externally",
                action_target=GLib.Variant("s", output_path))
        )

    def _set_original_texture(self, path: str) -> None:
        self._set_texture(path, as_original=True)

    def _set_updated_texture(self, path: str) -> None:
        self._set_texture(path)

    def _set_texture(self, path: str, as_original: bool = False) -> None:
        try:
            texture = Gdk.Texture.new_from_filename(path)
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
        else:
            current_scale = self.image_view.scale
            current_scaling_filter = self.image_view.scaling_filter

            self.image_view.texture = texture

            if as_original:
                self.original_texture = texture
                self.image_options_view.original_texture = texture
            else:
                self.updated_texture = texture
                self.image_view.scale = current_scale
                self.image_view.scaling_filter = current_scaling_filter

    def _get_output_format_suffix(self) -> str:
        selected_format = self.image_options_view.export_format_combo.props.selected
        format_string = self.image_options_view.image_formats_stringlist.get_string(selected_format)

        # NOTE: This should only happen if the list isn't populated
        if format_string is None:
            format_string = "png"

        return format_string

    def _set_size_spins(self, width: int, height: int) -> None:
        self.image_options_view.image_width_row.set_value(width)
        self.image_options_view.image_height_row.set_value(height)

    def _add_shortcuts(
        self,
        action_name: str,
        shortcut_list: list[tuple[int, list[Gdk.ModifierType]]]
    ) -> None:
        for key, modifiers in shortcut_list:
            modifier = Gdk.ModifierType.NO_MODIFIER_MASK

            for m in modifiers:
                modifier = modifier | m

            shortcut = Gtk.Shortcut.new(
                Gtk.KeyvalTrigger.new(key, modifier),
                Gtk.NamedAction.new(action_name)
            )

            self.shortcut_controller.add_shortcut(shortcut)

    def _update_adjustment(self, x: float, y: float) -> None:
        self.scrolled_window.get_hadjustment().set_value(
            self.scrolled_window.get_hadjustment().get_value() - x + self.last_x
        )
        self.scrolled_window.get_vadjustment().set_value(
            self.scrolled_window.get_vadjustment().get_value() - y + self.last_y
        )

    def _cancel_deceleration(self) -> None:
        self.scrolled_window.set_kinetic_scrolling(False)
        self.scrolled_window.set_kinetic_scrolling(True)

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
