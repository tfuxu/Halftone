# Copyright (c) 2021-2025, Loupe Authors <https://gitlab.gnome.org/GNOME/loupe>
# Copyright (c) 2019-2025, Komikku Authors <https://codeberg.org/valos/Komikku>
# Copyright 2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

import math

from gi.repository import GLib, GObject, Gdk, Graphene, Gsk, Gtk

from halftone.backend.logger import Logger

logging = Logger()

# Max zoom level 800%
MAX_ZOOM_LEVEL: float = 8.0

class HalftoneImage(Gtk.Widget, Gtk.Scrollable):  # pyright: ignore
    __gtype_name__ = "HalftoneImage"

    # Displayed texture, will be None only in initial view
    _texture: Gdk.Texture | None
    # Currently applied scaling filter (available: LINEAR, NEAREST, TRILINEAR)
    _scaling_filter: Gsk.ScalingFilter = Gsk.ScalingFilter.LINEAR

    # Current zoom level
    _zoom: float = 1.0

    # Always fit image into window, causes `zoom` to change automatically
    _best_fit: bool = True

    # Horizontal scrolling
    _hadjustment: Gtk.Adjustment = Gtk.Adjustment()
    # Vertical scrolling
    _vadjustment: Gtk.Adjustment = Gtk.Adjustment()

    # Current pointer position, needed for aimed zooming
    pointer_position: tuple[float, float] | None = None

    # Stores current widget dimensions, used for automatic best-fit
    widget_dimensions: tuple[int, int] = (0, 0)

    def __init__(
        self,
        texture: Gdk.Texture | None = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.set_accessible_role(Gtk.AccessibleRole.IMG)
        self.set_overflow(Gtk.Overflow.HIDDEN)

        self._texture = texture

        self._setup_controllers()

    """
    Setup methods
    """

    def _setup_controllers(self) -> None:
        # Needed for having the current cursor position available
        motion_controller = Gtk.EventControllerMotion.new()

        motion_controller.connect("enter", self._on_motion_enter)
        motion_controller.connect("motion", self._on_motion)
        motion_controller.connect("leave", self._on_motion_leave)

        self.add_controller(motion_controller)

    """
    Properties
    """

    @GObject.Property(type=Gdk.Texture)
    def texture(self) -> Gdk.Texture | None:
        return self._texture

    @texture.setter
    def set_texture(self, texture: Gdk.Texture) -> None:
        self._texture = texture
        self._zoom = 1.0
        self._scaling_filter = Gsk.ScalingFilter.LINEAR
        self._best_fit = True
        self.widget_dimensions = (0, 0)

        self.notify("zoom")
        self.notify("scaling_filter")

        self.queue_allocate()

    # TODO: Check if not having a minimum value can create issues
    @GObject.Property(type=float, default=1.0, maximum=MAX_ZOOM_LEVEL)
    def zoom(self) -> float:
        return self._zoom

    @zoom.setter
    def set_zoom(self, zoom: float) -> None:
        self._set_zoom_aiming(zoom, self.pointer_position)

    @GObject.Property(type=bool, default=True)
    def best_fit(self) -> bool:
        return self._best_fit

    @best_fit.setter
    def set_best_fit(self, best_fit: bool) -> None:
        self._best_fit = best_fit

        self.queue_draw()

    def set_hadjustment(self, hadjustment: Gtk.Adjustment | None = None) -> None:
        adjustment = hadjustment

        if adjustment is None:
            adjustment = Gtk.Adjustment()

        adjustment.connect("value-changed", lambda _: self.queue_draw())

        self._hadjustment = adjustment
        self._configure_adjustments()

    @GObject.Property(type=Gtk.Adjustment, setter=set_hadjustment)
    def hadjustment(self) -> Gtk.Adjustment:
        return self._hadjustment

    def set_vadjustment(self, vadjustment: Gtk.Adjustment | None = None) -> None:
        adjustment = vadjustment

        if adjustment is None:
            adjustment = Gtk.Adjustment()

        adjustment.connect("value-changed", lambda _: self.queue_draw())

        self._vadjustment = adjustment
        self._configure_adjustments()

    @GObject.Property(type=Gtk.Adjustment, setter=set_vadjustment)
    def vadjustment(self) -> Gtk.Adjustment:
        return self._vadjustment

    @GObject.Property(type=Gtk.ScrollablePolicy, default=Gtk.ScrollablePolicy.MINIMUM)
    def vscroll_policy(self) -> Gtk.ScrollablePolicy:
        return Gtk.ScrollablePolicy.MINIMUM

    @GObject.Property(type=Gtk.ScrollablePolicy, default=Gtk.ScrollablePolicy.MINIMUM)
    def hscroll_policy(self) -> Gtk.ScrollablePolicy:
        return Gtk.ScrollablePolicy.MINIMUM

    @GObject.Property(type=Gsk.ScalingFilter, default=Gsk.ScalingFilter.LINEAR)
    def scaling_filter(self) -> Gsk.ScalingFilter:
        return self._scaling_filter

    @scaling_filter.setter
    def set_scaling_filter(self, filter: Gsk.ScalingFilter) -> None:
        self._scaling_filter = filter

        self.queue_draw()

    @GObject.Property(type=bool, default=True)
    def can_zoom_in(self) -> bool:
        return self._zoom < MAX_ZOOM_LEVEL

    @GObject.Property(type=bool, default=True)
    def can_zoom_out(self) -> bool:
        return self._zoom > self._get_best_fit_zoom_level()

    @GObject.Property(type=bool, default=False)
    def can_reset_zoom(self) -> bool:
        return self._zoom != self._get_best_fit_zoom_level()

    """
    Signals
    """

    @GObject.Signal(name="zoom-changed")
    def zoom_changed(self):
        pass

    """
    Overrides
    """

    # Here's where the zoom magic happens
    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        widget_width = float(self.get_width())
        widget_height = float(self.get_height())

        if self.texture is None:
            return

        texture_width = self.image_displayed_width()
        texture_height = self.image_displayed_height()

        hadjustment: Gtk.Adjustment = self.hadjustment
        vadjustment: Gtk.Adjustment = self.vadjustment

        self._configure_adjustments()

        snapshot.save()

        # Apply the scrolling position to the image
        x = -(hadjustment.get_value() - (hadjustment.get_upper() - texture_width) / 2)
        snapshot.translate(Graphene.Point().init(int(x), 0))
        y = -(vadjustment.get_value() - (vadjustment.get_upper() - texture_height) / 2)
        snapshot.translate(Graphene.Point().init(0, int(y)))

        # Centering in widget when no scrolling (black bars around image)
        snapshot.translate(
            Graphene.Point().init(
                max((widget_width - texture_width) // 2, 0),
                max((widget_height - texture_height) // 2, 0),
            )
        )

        scale_factor = self.get_scale_factor()
        if scale_factor != 1:
            snapshot.scale(1 / scale_factor, 1 / scale_factor)

        # Create texture boundaries
        bounds_width = int(texture_width) * scale_factor
        bounds_height = int(texture_height) * scale_factor
        bounds = Graphene.Rect().alloc().init(0, 0, bounds_width, bounds_height)

        snapshot.append_scaled_texture(
            self.texture,
            self.scaling_filter,
            bounds
        )

        snapshot.restore()
        self.emit("zoom-changed")

    def do_measure(
        self,
        orientation: Gtk.Orientation,
        for_size: int
    ) -> tuple[int, int, int, int]:
        baseline = self.get_baseline()
        size: int

        if self.texture is None:
            return (0, 0, baseline, baseline)

        width = self.texture.get_width()
        height = self.texture.get_height()

        if orientation == Gtk.Orientation.HORIZONTAL:
            size = width
        else:
            size = height

        minimum = 0
        natural = math.ceil(size * self.zoom)
        return (minimum, natural, baseline, baseline)

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        if self.best_fit:
            # Ensure there is an actual size change
            if self.widget_dimensions != (width, height):
                self._configure_best_fit()

        self.widget_dimensions = width, height
        self._configure_adjustments()

    """
    Callbacks
    """

    def _on_motion_enter(
        self,
        _controller: Gtk.EventControllerMotion,
        x: float,
        y: float
    ) -> None:
        self.pointer_position = (x, y)
        logging.debug(f"on_motion_enter value: {self.pointer_position}")

    def _on_motion(
        self,
        _controller: Gtk.EventControllerMotion,
        x: float,
        y: float
    ) -> None:
        self.pointer_position = (x, y)
        logging.debug(f"on_motion value: {self.pointer_position}")

    def _on_motion_leave(self, _controller: Gtk.EventControllerMotion) -> None:
        self.pointer_position = None
        logging.debug(f"on_motion_leave value: {self.pointer_position}")

    def on_zoom(
        self,
        _widget: Gtk.Widget,
        action_name: str,
        _parameter: GLib.Variant | None
    ) -> None:
        zoom: float

        match action_name:
            case "zoom.in":
                zoom = self.zoom + 0.1
            case "zoom.out":
                zoom = self.zoom - 0.1
            case "zoom.best-fit":
                zoom = self._get_best_fit_zoom_level()
            case _:
                raise ValueError(
                    "Invalid action name provided. Make sure it's from \"zoom.*\" namespace."
                )

        self.zoom_to(zoom)

    """
    Public methods
    """

    def zoom_to(self, zoom: float) -> None:
        """
        Zoom to specific level aiming at the current pointer position.
        """

        self._set_zoom_aiming(zoom, self.pointer_position)

    def zoom_in_cursor(self) -> None:
        """
        Zoom in a step aiming at the current pointer position.

        Used by shortcuts.
        """

        zoom = self.zoom + 0.1
        self._set_zoom_aiming(zoom, self.pointer_position)

    def zoom_in_center(self) -> None:
        """
        Zoom in a step aiming at the center of the viewport.

        Used by buttons.
        """

        zoom = self.zoom + 0.1
        self._set_zoom_aiming(zoom, None)

    def zoom_out_cursor(self) -> None:
        """
        Zoom out a step aiming at the current pointer position.

        Used by shortcuts.
        """

        zoom = self.zoom - 0.1
        self._set_zoom_aiming(zoom, self.pointer_position)

    def zoom_out_center(self) -> None:
        """
        Zoom out a step aiming at the center of the viewport.

        Used by buttons.
        """

        zoom = self.zoom - 0.1
        self._set_zoom_aiming(zoom, None)

    def zoom_best_fit(self) -> None:
        """
        Zoom to best fit.

        Used by shortcuts and buttons.
        """

        self._set_zoom_aiming(self._get_best_fit_zoom_level(), self.pointer_position)

    def image_displayed_width(self) -> float:
        """
        Image width with current zoom factor.
        """

        texture: Gdk.Texture | None = self.texture
        if texture is None:
            return 0.0

        return texture.get_width() * self.zoom

    def image_displayed_height(self) -> float:
        """
        Image height with current zoom factor.
        """

        texture: Gdk.Texture | None = self.texture
        if texture is None:
            return 0.0

        return texture.get_height() * self.zoom

    def max_hadjustment_value(self) -> float:
        return max(self.image_displayed_width() - self.get_width(), 0.0)

    def max_vadjustment_value(self) -> float:
        return max(self.image_displayed_height() - self.get_height(), 0.0)

    """
    Private methods
    """

    # TODO: Create a sub-function that handles the `position` parameter being None
    def _set_zoom_aiming(self, zoom: float, position: tuple[float, float] | None) -> None:
        """
        Set zoom level aiming for given position or center if not available.
        """

        # Clamp the provided zoom value between the current best-fit and max zoom.
        zoom = max(self._get_best_fit_zoom_level(), min(zoom, MAX_ZOOM_LEVEL))

        if zoom == self.zoom:
            return

        borders = self._get_borders()
        zoom_ratio = self.zoom / zoom

        logging.debug(f"Setting zoom level to: {zoom}")

        if zoom <= self._get_best_fit_zoom_level():
            zoom = self._get_best_fit_zoom_level()
            self.best_fit = True
        else:
            self.best_fit = False

        self._zoom = zoom
        self._configure_adjustments()

        # Aim at the viewport center if `position` is None
        x = self.get_width() // 2
        y = self.get_height() // 2

        if position:
            x = position[0]
            y = position[1]

        hadjustment: Gtk.Adjustment = self.hadjustment
        vadjustment: Gtk.Adjustment = self.vadjustment

        h_value = max((x + hadjustment.get_value() - borders[0]) / zoom_ratio - x, 0)
        hadjustment.set_value(h_value)

        v_value = max((y + vadjustment.get_value() - borders[1]) / zoom_ratio - y, 0)
        vadjustment.set_value(v_value)

        self.notify("zoom")

        self.queue_allocate()
        self.queue_draw()

    def _configure_adjustments(self) -> None:
        """
        Configures scrollbars for current situation.
        """

        if self.texture is None:
            return

        hadjustment: Gtk.Adjustment = self.hadjustment
        content_width = self.image_displayed_width()
        widget_width = float(self.get_width())

        hadjustment.configure(
            # value
            max(min(hadjustment.get_value(), self.max_hadjustment_value()), 0.0),
            # lower
            0.0,
            # upper
            content_width,
            # arrow button and shortcut step
            widget_width * 0.1,
            # page up/down step
            widget_width * 0.9,
            # page size
            min(widget_width, content_width)
        )

        vadjustment: Gtk.Adjustment = self.vadjustment
        content_height = self.image_displayed_height()
        widget_height = float(self.get_height())

        vadjustment.configure(
            # value
            max(min(vadjustment.get_value(), self.max_vadjustment_value()), 0.0),
            # lower
            0.0,
            # upper
            content_height,
            # arrow button and shortcut step
            widget_height * 0.1,
            # page up/down step
            widget_height * 0.9,
            # page size
            min(widget_height, content_height)
        )

    def _configure_best_fit(self) -> None:
        """
        Sets respective output values if best-fit is active.
        """

        # Calculate new zoom value for best fit
        if self.best_fit:
            best_fit_level = self._get_best_fit_zoom_level()
            self.zoom = best_fit_level
            self._configure_adjustments()

    def _get_borders(self) -> tuple[float, float]:
        """
        Returns the width of horizontal (left, right) and vertical (top, bottom) bars.
        """

        widget_width = float(self.get_width())

        if widget_width > self.image_displayed_width():
            hborder = (widget_width - self.image_displayed_width()) / 2.0
        else:
            hborder = 0.0

        widget_height = float(self.get_height())

        if widget_height > self.image_displayed_height():
            vborder = (widget_height - self.image_displayed_height()) / 2.0
        else:
            vborder = 0.0

        return (hborder, vborder)

    def _get_best_fit_zoom_level(self) -> float:
        """
        Calculates the zoom level that will make the image fit in widget.
        """

        texture: Gdk.Texture | None = self.texture
        if texture is None:
            return 0.0

        image_width = texture.get_width() / self.get_scale_factor()
        image_height = texture.get_height() / self.get_scale_factor()

        texture_aspect_ratio = image_width / image_height
        widget_aspect_ratio = self.get_width() / self.get_height()

        max_zoom_factor = 1.0

        if texture_aspect_ratio > widget_aspect_ratio:
            default_zoom = min(self.get_width() / image_width, max_zoom_factor)
        else:
            default_zoom = min(self.get_height() / image_height, max_zoom_factor)

        return default_zoom
