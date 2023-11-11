# Copyright 2023, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from enum import Enum
from pathlib import Path

from gi.repository import GLib, Gdk, Gio, Gtk, Adw

from halftone.backend.utils.temp import HalftoneTempFile
from halftone.backend.utils.image import calculate_height
from halftone.backend.model.output_options import OutputOptions
from halftone.backend.magick import HalftoneImageMagick
from halftone.backend.logger import Logger

from halftone.utils.killable_thread import KillableThread
from halftone.utils.filters import supported_output_formats
from halftone.constants import rootdir # pylint: disable=E0401,E0611

logging = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/dither_page.ui")
class HalftoneDitherPage(Adw.BreakpointBin):
    __gtype_name__ = "HalftoneDitherPage"

    image_dithered = Gtk.Template.Child()

    split_view = Gtk.Template.Child()

    preview_scroll_window = Gtk.Template.Child()

    save_image_button = Gtk.Template.Child()

    save_format_combo = Gtk.Template.Child()
    dither_algorithms_combo = Gtk.Template.Child()

    image_properties_expander = Gtk.Template.Child()

    brightness_toggle = Gtk.Template.Child()
    contrast_toggle = Gtk.Template.Child()
    image_size_toggle = Gtk.Template.Child()

    image_width_row = Gtk.Template.Child()
    aspect_ratio_toggle = Gtk.Template.Child()
    image_height_row = Gtk.Template.Child()

    brightness_row = Gtk.Template.Child()
    contrast_row = Gtk.Template.Child()

    image_formats_stringlist = Gtk.Template.Child()
    algorithms_stringlist = Gtk.Template.Child()

    color_amount_row = Gtk.Template.Child()

    save_image_chooser = Gtk.Template.Child()
    all_filter = Gtk.Template.Child()

    preview_group_stack = Gtk.Template.Child()

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.settings = parent.settings

        self.app = self.parent.get_application()
        self.win = self.app.get_active_window()

        self.toast_overlay = self.parent.toast_overlay

        self.origin_x: float = None
        self.origin_y: float = None

        self.task_id = None
        self.tasks = []

        self.input_image_path: str = None
        self.preview_image_path: str = None

        self.original_paintable: Gdk.Paintable = None
        self.updated_paintable: Gdk.Paintable = None

        self.output_options: OutputOptions = OutputOptions()

        self.keep_aspect_ratio = True

        self.setup_signals()
        self.setup()
        self.setup_controllers()

    def setup_signals(self):
        self.aspect_ratio_toggle.connect("notify::active",
            self.on_aspect_ratio_toggled)

        self.save_image_chooser.connect("response",
            self.on_image_chooser_response)

        self.dither_algorithms_combo.connect("notify::selected",
            self.on_dither_algorithm_selected)

        self.save_format_combo.connect("notify::selected",
            self.on_save_format_selected)

        self.settings.connect("changed::preview-content-fit",
            self.update_preview_content_fit)

    def setup(self):
        # Set default preview stack child
        self.preview_group_stack.set_visible_child_name("preview_stack_loading_page")

        # Workaround: Set default values for SpinRows
        self.color_amount_row.set_value(10)
        self.image_width_row.set_value(1)
        self.image_height_row.set_value(1)

        # By default keep image aspect ratio
        self.aspect_ratio_toggle.set_active(True)

        self.setup_image_chooser()
        self.setup_dither_algorithms()
        self.setup_save_formats()

    def setup_image_chooser(self):
        self.save_image_chooser.set_transient_for(self.win)
        self.save_image_chooser.set_action(Gtk.FileChooserAction.SAVE)

    def setup_dither_algorithms(self):
        algorithms_list = [
            "Floyd-Steinberg",
            "Riemersma",
            "Bayer (ordered)"
        ]

        for algorithm in algorithms_list:
            self.algorithms_stringlist.append(algorithm)

    def setup_save_formats(self):
        for image_format in supported_output_formats:
            self.image_formats_stringlist.append(image_format)

        self.save_format_combo.set_selected(supported_output_formats.index("png"))

    def setup_controllers(self):
        preview_drag_ctrl = Gtk.GestureDrag.new()
        preview_drag_ctrl.connect("drag-begin", self.preview_drag_begin)
        preview_drag_ctrl.connect("drag-update", self.preview_drag_update)

        self.preview_scroll_window.add_controller(preview_drag_ctrl)

    def preview_drag_begin(self, x: float, y: float, *args):
        self.origin_x = self.preview_scroll_window.get_hadjustment().get_value()
        self.origin_y = self.preview_scroll_window.get_vadjustment().get_value()

    def preview_drag_update(self, widget, offset_x: float, offset_y: float, *args):
        hadj = self.preview_scroll_window.get_hadjustment()
        vadj = self.preview_scroll_window.get_vadjustment()

        hadj.set_value(self.origin_x - offset_x)
        vadj.set_value(self.origin_y - offset_y)

    """ Main functions """

    def update_preview_image(self, path: str, output_options: OutputOptions,
                                callback: callable = None):
        self.on_awaiting_image_load()

        if self.preview_image_path:
            self.clean_preview_paintable()

        self.output_options = output_options
        self.preview_image_path = HalftoneImageMagick().dither_image(path, self.output_options)

        try:
            self.set_updated_paintable(self.preview_image_path)
        except GLib.GError:
            self.win.show_error_page()
            raise
        else:
            self.image_dithered.set_paintable(self.updated_paintable)
            self.on_successful_image_load()

        if callback:
            callback()

    # NOTE: Use this only if you initially load the picture (eg. from file chooser)
    def load_preview_image(self, file: Gio.File):
        self.input_image_path = file.get_path()
        try:
            self.set_original_paintable(self.input_image_path)
        except GLib.GError:
            self.win.show_error_page()
            raise
        else:
            self.set_size_spins(self.original_paintable.get_width(),
                                self.original_paintable.get_height())
            self.start_task(self.update_preview_image,
                            self.input_image_path,
                            OutputOptions(),
                            self.on_successful_image_load)

    def save_image(self, paintable: Gdk.Paintable, output_path: str,
                        output_options: OutputOptions, callback: callable):
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

    """ Signal callbacks """

    @Gtk.Template.Callback()
    def on_color_amount_changed(self, widget):
        new_color_amount = self.get_color_amount_pref(widget)

        if new_color_amount == self.output_options.color_amount:
            return

        self.output_options.color_amount = new_color_amount

        if self.original_paintable:
            self.start_task(self.update_preview_image,
                            self.input_image_path,
                            self.output_options,
                            self.on_successful_image_load)

    @Gtk.Template.Callback()
    def on_brightness_toggled(self, widget, *args):
        if self.contrast_toggle.props.active == True:
            self.contrast_toggle.set_active(False)
            self.image_properties_expander.remove(self.contrast_row)

        if self.image_size_toggle.props.active == True:
            self.image_size_toggle.set_active(False)
            self.remove_image_size_rows()

        self.on_image_prop_option_toggled(widget, self.brightness_row)

    @Gtk.Template.Callback()
    def on_contrast_toggled(self, widget, *args):
        if self.brightness_toggle.props.active == True:
            self.brightness_toggle.set_active(False)
            self.image_properties_expander.remove(self.brightness_row)

        if self.image_size_toggle.props.active == True:
            self.image_size_toggle.set_active(False)
            self.remove_image_size_rows()

        self.on_image_prop_option_toggled(widget, self.contrast_row)

    @Gtk.Template.Callback()
    def on_resize_toggled(self, widget, *args):
        if self.brightness_toggle.props.active == True:
            self.brightness_toggle.set_active(False)
            self.image_properties_expander.remove(self.brightness_row)

        if self.contrast_toggle.props.active == True:
            self.contrast_toggle.set_active(False)
            self.image_properties_expander.remove(self.contrast_row)

        self.on_image_prop_option_toggled(widget,
                                          self.image_width_row,
                                          self.aspect_ratio_toggle,
                                          self.image_height_row)

    @Gtk.Template.Callback()
    def on_toggle_sidebar_clicked(self, widget, *args):
        if self.split_view.props.show_sidebar == False:
            self.split_view.set_show_sidebar(True)
            return

        self.split_view.set_show_sidebar(False)

    @Gtk.Template.Callback()
    def on_brightness_changed(self, widget):
        new_brightness = int(widget.props.value)

        if new_brightness == self.output_options.brightness:
            return

        self.output_options.brightness = new_brightness

        self.start_task(self.update_preview_image,
                        self.input_image_path,
                        self.output_options,
                        self.on_successful_image_load)

    @Gtk.Template.Callback()
    def on_contrast_changed(self, widget):
        new_contrast = int(widget.props.value)

        if new_contrast == self.output_options.contrast:
            return

        self.output_options.contrast = new_contrast

        self.start_task(self.update_preview_image,
                        self.input_image_path,
                        self.output_options,
                        self.on_successful_image_load)

    @Gtk.Template.Callback()
    def on_image_width_changed(self, widget):
        new_width = self.get_image_width_pref(widget)

        if new_width == self.output_options.width:
            return

        self.output_options.width = new_width

        if self.original_paintable:
            img_height = self.original_paintable.get_height()
            img_width = self.original_paintable.get_width()

            if self.aspect_ratio_toggle.get_active() == True:
                new_height = calculate_height(img_width, img_height, new_width)
                self.output_options.height = new_height
                self.image_height_row.set_value(new_height)

            self.start_task(self.update_preview_image,
                            self.input_image_path,
                            self.output_options,
                            self.on_successful_image_load)

    @Gtk.Template.Callback()
    def on_image_height_changed(self, widget):
        new_height = self.get_image_height_pref(widget)

        if new_height == self.output_options.height:
            return

        self.output_options.height = new_height

        if self.original_paintable:
            if not self.keep_aspect_ratio:
                self.start_task(self.update_preview_image,
                                self.input_image_path,
                                self.output_options,
                                self.on_successful_image_load)

    def on_save_image(self, *args):
        file_extension = self.get_output_format_suffix()
        file_display_name = Path(self.input_image_path).stem

        output_filename = f"halftone-{file_display_name}.{file_extension}"
        logging.debug(f"Output filename: {output_filename}")

        self.save_image_chooser.set_current_name(output_filename)
        self.save_image_chooser.show()

    def on_aspect_ratio_toggled(self, widget, *args):
        if widget.props.active == True:
            self.keep_aspect_ratio = True
            #widget.props.icon_name = "chain-link-symbolic"
            #widget.props.tooltip_text = _("Keep aspect ratio")
            self.image_height_row.set_sensitive(False)

        if widget.props.active == False:
            self.keep_aspect_ratio = False
            #widget.props.icon_name = "chain-link-loose-symbolic"
            #widget.props.tooltip_text = _("Don't keep aspect ratio")
            self.image_height_row.set_sensitive(True)

    def on_image_chooser_response(self, widget, response):
        if response == Gtk.ResponseType.ACCEPT:
            output_file = widget.get_file()
        widget.hide()

        if response == Gtk.ResponseType.ACCEPT:
            self.start_task(self.save_image,
                            self.updated_paintable,
                            output_file.get_path(),
                            self.output_options,
                            self.win.show_dither_page)

    def on_dither_algorithm_selected(self, widget, *args):
        algorithm_string = self.get_dither_algorithm_pref(widget)

        self.output_options.algorithm = algorithm_string

        if self.original_paintable:
            self.start_task(self.update_preview_image,
                            self.input_image_path,
                            self.output_options,
                            self.on_successful_image_load)

    def on_save_format_selected(self, widget, *args):
        selected_format = widget.props.selected
        format_string = self.image_formats_stringlist.get_string(selected_format)

        self.output_options.output_format = format_string

    def on_successful_image_load(self, *args):
        self.preview_group_stack.set_visible_child_name("preview_stack_main_page")
        self.save_image_button.set_sensitive(True)

    def on_awaiting_image_load(self, *args):
        self.preview_group_stack.set_visible_child_name("preview_stack_loading_page")
        self.save_image_button.set_sensitive(False)

    """ Module-specific helpers """

    def set_original_paintable(self, path: str):
        try:
            self.original_paintable = Gdk.Texture.new_from_filename(path)
        except GLib.GError as e:
            logging.traceback_error(
                "Failed to construct new Gdk.Texture from path.",
                exc=e, show_exception=True)
            self.win.latest_traceback = logging.get_traceback(e)
            raise

    def set_updated_paintable(self, path: str):
        try:
            self.updated_paintable = Gdk.Texture.new_from_filename(path)
        except GLib.GError as e:
            logging.traceback_error(
                "Failed to construct new Gdk.Texture from path.",
                exc=e, show_exception=True)
            self.win.latest_traceback = logging.get_traceback(e)
            raise

    def clean_preview_paintable(self):
        try:
            HalftoneTempFile().delete_temp_file(self.preview_image_path)
        except FileNotFoundError:
            pass

    def on_image_prop_option_toggled(self, toggle, *row_widgets):
        if toggle.props.active == True:
            for row in row_widgets:
                self.image_properties_expander.add_row(row)
            self.image_properties_expander.set_enable_expansion(True)
            self.image_properties_expander.set_expanded(True)

        if toggle.props.active == False:
            for row in row_widgets:
                self.image_properties_expander.remove(row)
            self.image_properties_expander.set_enable_expansion(False)
            self.image_properties_expander.set_expanded(False)

    def remove_image_size_rows(self):
        self.image_properties_expander.remove(self.image_width_row)
        self.image_properties_expander.remove(self.aspect_ratio_toggle)
        self.image_properties_expander.remove(self.image_height_row)

    def get_output_format_suffix(self) -> str:
        selected_format = self.save_format_combo.props.selected
        format_string = self.image_formats_stringlist.get_string(selected_format)

        return format_string

    def get_color_amount_pref(self, widget) -> int:
        color_amount = int(widget.props.value)
        return color_amount

    def get_image_width_pref(self, widget) -> int:
        new_width = int(widget.props.value)
        return new_width

    def get_image_height_pref(self, widget) -> int:
        new_height = int(widget.props.value)
        return new_height

    def get_dither_algorithm_pref(self, widget) -> str:
        selected_algorithm = widget.props.selected

        class selectedAlgo(Enum):
            FLOYD_STEINBERG = 0
            RIEMERSMA = 1
            ORDERED = 2

        def __get_algorithm_string():
            if selected_algorithm == selectedAlgo.FLOYD_STEINBERG.value:
                return "floyd_steinberg"
            elif selected_algorithm == selectedAlgo.RIEMERSMA.value:
                return "riemersma"
            elif selected_algorithm == selectedAlgo.ORDERED.value:
                return "ordered"

        algorithm_string = __get_algorithm_string()

        return algorithm_string

    def update_preview_content_fit(self, *args):
        selected_content_fit = self.settings.get_int("preview-content-fit")

        if selected_content_fit == 0:
            content_fit = Gtk.ContentFit.FILL
        elif selected_content_fit == 1:
            content_fit = Gtk.ContentFit.CONTAIN
        elif selected_content_fit == 2:
            content_fit = Gtk.ContentFit.COVER
        elif selected_content_fit == 3:
            content_fit = Gtk.ContentFit.SCALE_DOWN

        self.image_dithered.set_content_fit(content_fit)

    def set_size_spins(self, width, height):
        self.image_width_row.set_value(width)
        self.image_height_row.set_value(height)

    def start_task(self, task: callable, *args): #callback: callable
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
        except GLib.GError:
            self.toast_overlay.add_toast(
                Adw.Toast(title=_("Failed to load preview image"))
            )
