# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from wand.version import MAGICK_VERSION_INFO, VERSION, MAGICK_VERSION_FEATURES

from gi.repository import Adw, Gtk

from halftone import constants # pyright: ignore


class HalftoneAboutWindow:
    def __init__(self, parent: Gtk.Widget):
        self.parent = parent
        self.app: Adw.Application = self.parent.get_application()

        self.setup()
        self.set_debug_info()

    def setup(self):
        self.about_window = Adw.AboutDialog(
            application_name="Halftone",
            application_icon=constants.app_id,
            developer_name="tfuxu",
            website=constants.project_url,
            support_url=constants.help_url,
            issue_url=constants.bugtracker_url,
            developers=[
                "tfuxu https://github.com/tfuxu",
                "Brage Fuglseth https://bragefuglseth.dev",
            ],
            designers=[
                "tfuxu https://github.com/tfuxu",
                "TheEvilSkeleton https://gitlab.com/TheEvilSkeleton"
            ],
            # TRANSLATORS: This is a place to put your credits (formats: "Name https://example.com" or "Name <email@example.com>", no quotes) and is not meant to be translated literally.
            translator_credits=_("translator-credits"),
            copyright="Copyright © 2023-2025 tfuxu",
            license_type=Gtk.License.GPL_3_0,
            version=constants.version,
            release_notes_version=constants.rel_ver,
        )
        self.about_window.add_legal_section("ImageMagick", None, Gtk.License.MIT_X11, None)

    def set_debug_info(self) -> None:
        magick_version = f"ImageMagick: {".".join(map(str, MAGICK_VERSION_INFO))}"
        wand_version = f"Wand: {VERSION}"
        magick_features = f"Features: {MAGICK_VERSION_FEATURES}"

        info_list = [magick_version, wand_version, magick_features]

        debug_info = ""
        for info in info_list:
            debug_info += info + "\n"

        self.about_window.set_debug_info(debug_info)
        self.about_window.set_debug_info_filename("halftone-debug-info")

    def show_about(self) -> None:
        self.about_window.present(self.parent)
