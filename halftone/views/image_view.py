# Copyright 2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

# NOTE: This code is mostly a port of the `Image Scaling` example from gtk4-demo: https://gitlab.gnome.org/GNOME/gtk/-/blob/main/demos/gtk-demo/imageview.c

import math

from gi.repository import Adw, Gtk, Gdk, Gsk, Gio, GLib, Graphene, GObject


class HalftoneImageView(Gtk.Widget):
    __gtype_name__ = "HalftoneImageView"

    _texture: Gdk.Texture | None
    _scaling_filter = Gsk.ScalingFilter.LINEAR

    _scale = 1.0

    def __init__(self, parent: Gtk.Widget, texture: Gdk.Texture | None, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.settings: Gio.Settings = parent.settings

        self.app: Adw.Application = self.parent.get_application()
        self.win: Adw.ApplicationWindow = self.app.get_active_window()

        self.set_accessible_role(Gtk.AccessibleRole.IMG)

        self._texture = texture

    """ Properties """

    @GObject.Property(type=Gdk.Texture)
    def texture(self) -> Gdk.Texture | None:
        return self._texture

    @texture.setter
    def set_texture(self, texture: Gdk.Texture) -> None:
        self._texture = texture
        self._scale = 1.0
        self._scaling_filter = Gsk.ScalingFilter.LINEAR

        self.queue_resize()

        self.notify("scale")
        self.notify("scaling_filter")

    @GObject.Property(type=float, minimum=1.0/1024.0, maximum=1024.0, default=1.0)
    def scale(self) -> float:
        return self._scale

    @scale.setter
    def set_scale(self, scale: float) -> None:
        self._scale = scale

        self.queue_resize()

    @GObject.Property(type=Gsk.ScalingFilter, default=Gsk.ScalingFilter.LINEAR)
    def scaling_filter(self) -> Gsk.ScalingFilter:
        return self._scaling_filter

    @scaling_filter.setter
    def set_scaling_filter(self, filter: Gsk.ScalingFilter) -> None:
        self._scaling_filter = filter

        self.queue_resize()

    @GObject.Property(type=bool, default=True)
    def can_zoom_in(self) -> bool:
        return self._scale < 1024.0

    @GObject.Property(type=bool, default=True)
    def can_zoom_out(self) -> bool:
        return self._scale > 1.0/1024.0

    @GObject.Property(type=bool, default=False)
    def can_reset_zoom(self) -> bool:
        return self._scale != 1.0

    """ Signals """

    @GObject.Signal(name="zoom-changed")
    def zoom_changed(self):
        pass

    """ Overrides """

    # Here's where the zoom magic happens
    def do_snapshot(self, snapshot: Gdk.Snapshot) -> None:
        width = self.get_width()
        height = self.get_height()

        if self.texture is None:
            return

        new_width = self.scale * self.texture.get_width()
        new_height = self.scale * self.texture.get_height()

        x = (width - math.ceil(new_width)) / 2
        y = (height - math.ceil(new_height)) / 2

        snapshot.push_clip(Graphene.Rect().alloc().init(0, 0, width, height))
        snapshot.save()
        snapshot.translate(Graphene.Point().alloc().init(x, y))
        snapshot.translate(Graphene.Point().alloc().init(new_width / 2, new_height / 2))
        snapshot.translate(Graphene.Point().alloc().init(-new_width / 2, -new_height / 2))
        snapshot.append_scaled_texture(
            self.texture,
            self.scaling_filter,
            Graphene.Rect().alloc().init(0, 0, new_width, new_height)
        )

        snapshot.restore()
        snapshot.pop()

        self.emit("zoom-changed")

    # NOTE: Needed for Gtk.Viewport to implement scrollability
    # TODO: Interface with `Gtk.Scrollable` to enable more capabilities
    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
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

        minimum = natural = math.ceil(self.scale * size)
        return (minimum, natural, baseline, baseline)

    """ Callbacks """

    def on_zoom(self, _widget: Gtk.Widget, action_name: str, _parameter: GLib.Variant | None):
        scale: float

        match action_name:
            case "zoom.in":
                scale = min(1024.0, self.scale * math.sqrt(2))
            case "zoom.out":
                scale = max(1.0/1024.0, self.scale / math.sqrt(2))
            case "zoom.reset":
                scale = 1.0
            case _:
                raise ValueError("Invalid action name provided. Make sure it's from \"zoom.*\" namespace.")

        self.scale = scale

    """ Public methods """

    def zoom_to(self, zoom: float) -> None:
        self.scale = zoom

    def zoom_in(self) -> None:
        self.scale = min(1024.0, self.scale * math.sqrt(2))

    def zoom_out(self) -> None:
        self.scale = max(1.0/1024.0, self.scale / math.sqrt(2))

    def reset_zoom(self) -> None:
        self.scale = 1.0
