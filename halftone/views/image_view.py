# Copyright 2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Any

from gi.repository import Adw, Gdk, Gsk, Gtk

from halftone.constants import rootdir  # pyright: ignore
from halftone.views.image import HalftoneImage


@Gtk.Template(resource_path=f"{rootdir}/ui/image_view.ui")
class HalftoneImageView(Adw.Bin):
    __gtype_name__ = "HalftoneImageView"

    shortcut_controller: Gtk.ShortcutController = Gtk.Template.Child()

    loading_screen_box: Gtk.Box = Gtk.Template.Child()

    toggle_sheet_button: Gtk.Button = Gtk.Template.Child()

    viewer_scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()
    image_widget: HalftoneImage = Gtk.Template.Child()

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.last_x: float = 0.0
        self.last_y: float = 0.0

        self.zoom_target: float = 1.0

        self._setup_controllers()
        self._setup_gestures()
        self._setup_actions()
        self._setup_signals()

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

        self.viewer_scrolled_window.add_controller(scroll_controller)

    def _setup_gestures(self) -> None:
        # Drag for moving image around
        drag_gesture = Gtk.GestureDrag.new()
        drag_gesture.set_button(0)

        drag_gesture.connect("drag-begin", self.on_drag_begin)
        drag_gesture.connect("drag-update", self.on_drag_update)
        drag_gesture.connect("drag-end", self.on_drag_end)

        self.viewer_scrolled_window.add_controller(drag_gesture)

        # Zoom using 2-finger pinch/zoom gestures
        zoom_gesture = Gtk.GestureZoom.new()

        zoom_gesture.connect("begin", self.on_zoom_begin)
        zoom_gesture.connect("scale-changed", self.on_zoom_scale_changed)

        self.viewer_scrolled_window.add_controller(zoom_gesture)

    def _setup_actions(self) -> None:
        """ `zoom.*` action group """

        self.install_action("zoom.in", None, self.image_widget.on_zoom)
        self.install_action("zoom.out", None, self.image_widget.on_zoom)

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

    def _setup_signals(self) -> None:
        self.image_widget.connect("zoom-changed",
            self.on_zoom_changed)

    """
    Callbacks
    """

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
            self.image_widget.zoom_in()
        else:
            self.image_widget.zoom_out()

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

        self.image_widget.set_cursor_from_name("grabbing")
        self.last_x = 0.0
        self.last_y = 0.0

    def on_drag_update(self, _gesture: Gtk.GestureDrag, x: float, y: float) -> None:
        self._update_adjustment(x, y)
        self.last_x = x
        self.last_y = y

    def on_drag_end(self, _gesture: Gtk.GestureDrag, _x: float, _y: float) -> None:
        self.image_widget.set_cursor(None)
        self.last_x = 0.0
        self.last_y = 0.0

    def on_zoom_begin(
        self,
        _gesture: Gtk.GestureZoom,
        _sequence: Gdk.EventSequence
    ) -> None:
        self._cancel_deceleration()
        self.zoom_target = self.image_widget.scale

    def on_zoom_scale_changed(self, _gesture: Gtk.GestureZoom, scale: float) -> None:
        self.image_widget.scale = self.zoom_target * scale

    def on_zoom_changed(self, *args: Any) -> None:
        current_filter = self.image_widget.scaling_filter
        nearest = Gsk.ScalingFilter.NEAREST
        linear = Gsk.ScalingFilter.LINEAR

        if self.image_widget.scale >= 1.0 and current_filter is not nearest:
            self.image_widget.scaling_filter = nearest
        elif self.image_widget.scale < 1.0 and current_filter is not linear:
            self.image_widget.scaling_filter = linear

        self.action_set_enabled("zoom.in", self.image_widget.can_zoom_in)
        self.action_set_enabled("zoom.out", self.image_widget.can_zoom_out)

    """
    Private methods
    """

    def _cancel_deceleration(self) -> None:
        self.viewer_scrolled_window.set_kinetic_scrolling(False)
        self.viewer_scrolled_window.set_kinetic_scrolling(True)

    def _update_adjustment(self, x: float, y: float) -> None:
        self.viewer_scrolled_window.get_hadjustment().set_value(
            self.viewer_scrolled_window.get_hadjustment().get_value() - x + self.last_x
        )
        self.viewer_scrolled_window.get_vadjustment().set_value(
            self.viewer_scrolled_window.get_vadjustment().get_value() - y + self.last_y
        )

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
