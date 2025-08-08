# Copyright 2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from typing import Literal

from gi.repository import Adw, Gdk, Gio, Gtk

from halftone.backend.model.output_options import OutputOptions
from halftone.backend.utils.filetypes import FileType, get_output_formats
from halftone.backend.utils.image import calculate_height
from halftone.constants import rootdir  # pyright: ignore

@Gtk.Template(resource_path=f"{rootdir}/ui/image_options_view.ui")
class HalftoneImageOptionsView(Adw.Bin):
    __gtype_name__ = "HalftoneImageOptionsView"

    export_format_combo: Adw.ComboRow = Gtk.Template.Child()
    dither_algorithms_combo: Adw.ComboRow = Gtk.Template.Child()

    image_width_row: Adw.SpinRow = Gtk.Template.Child()
    aspect_ratio_toggle: Adw.SwitchRow = Gtk.Template.Child()
    image_height_row: Adw.SpinRow = Gtk.Template.Child()

    image_formats_stringlist: Gtk.StringList = Gtk.Template.Child()

    color_amount_row: Adw.SpinRow = Gtk.Template.Child()

    def __init__(
        self,
        parent: Gtk.Widget,
        output_options: OutputOptions,
        update_image_callback: Callable[[bool], None],
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.parent = parent
        self.settings: Gio.Settings = parent.settings

        self.app: Adw.Application = self.parent.get_application()
        self.win: Adw.ApplicationWindow = self.app.get_active_window()

        self.original_texture: Gdk.Texture = None

        self.output_options = output_options
        self.keep_aspect_ratio: bool = True

        self.update_image_callback = update_image_callback

        self._setup_signals()
        self._setup()

    """
    Setup methods
    """

    def _setup_signals(self) -> None:
        self.aspect_ratio_toggle.connect("notify::active",
            self.on_aspect_ratio_toggled)

        self.dither_algorithms_combo.connect("notify::selected",
            self.on_dither_algorithm_selected)

        self.export_format_combo.connect("notify::selected",
            self.on_save_format_selected)

    def _setup(self) -> None:
        # Workaround: Set default values for SpinRows
        self.color_amount_row.set_value(10)
        self.image_width_row.set_value(1)
        self.image_height_row.set_value(1)

        # By default keep image aspect ratio
        self.aspect_ratio_toggle.set_active(True)

        self._setup_save_formats()

    def _setup_save_formats(self) -> None:
        output_formats = get_output_formats(True) # TODO: Add a setting to toggle showing all formats

        for filetype in output_formats:
            self.image_formats_stringlist.append(filetype.as_extension())

        self.export_format_combo.set_selected(output_formats.index(FileType.PNG))

    """
    Callbacks
    """

    @Gtk.Template.Callback()
    def on_color_amount_changed(self, widget: Adw.SpinRow) -> None:
        new_color_amount = int(widget.props.value)

        if new_color_amount == self.output_options.color_amount:
            return

        self.output_options.color_amount = new_color_amount

        if self.original_texture:
            self.update_image_callback(True)

    @Gtk.Template.Callback()
    def on_brightness_changed(self, widget: Adw.SpinRow) -> None:
        new_brightness = int(widget.props.value)

        if new_brightness == self.output_options.brightness:
            return

        self.output_options.brightness = new_brightness

        self.update_image_callback(True)

    @Gtk.Template.Callback()
    def on_contrast_changed(self, widget: Adw.SpinRow) -> None:
        new_contrast = int(widget.props.value)

        if new_contrast == self.output_options.contrast:
            return

        self.output_options.contrast = new_contrast

        self.update_image_callback(True)

    @Gtk.Template.Callback()
    def on_image_width_changed(self, widget: Adw.SpinRow) -> None:
        new_width = int(widget.props.value)

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

            self.update_image_callback(True)

    @Gtk.Template.Callback()
    def on_image_height_changed(self, widget: Adw.SpinRow) -> None:
        new_height = int(widget.props.value)

        if new_height == self.output_options.height:
            return

        self.output_options.height = new_height

        if self.original_texture:
            if not self.keep_aspect_ratio:
                self.update_image_callback(True)

    def on_aspect_ratio_toggled(self, widget: Adw.SwitchRow, *args) -> None:
        if widget.props.active is True:
            self.keep_aspect_ratio = True
            self.image_height_row.set_sensitive(False)

        if widget.props.active is False:
            self.keep_aspect_ratio = False
            self.image_height_row.set_sensitive(True)

    def on_dither_algorithm_selected(self, widget: Adw.ComboRow, *args) -> None:
        algorithm_string = self._get_dither_algorithm_selected_string(widget)

        self.output_options.algorithm = algorithm_string

        if self.original_texture:
            self.update_image_callback(True)

    def on_save_format_selected(self, widget: Adw.ComboRow, *args) -> None:
        selected_format = widget.props.selected
        format_string = self.image_formats_stringlist.get_string(selected_format)

        self.output_options.output_format = format_string

    """
    Private methods
    """

    def _get_dither_algorithm_selected_string(
        self,
        widget: Adw.ComboRow
    ) -> Literal['floyd_steinberg', 'riemersma', 'ordered'] | None:
        selected_algorithm = widget.props.selected

        match selected_algorithm:
            case 0:
                return "floyd_steinberg"
            case 1:
                return "riemersma"
            case 2:
                return "ordered"
            case _:
                return None

