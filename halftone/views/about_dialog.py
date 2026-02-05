# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Optional

from gi.repository import Adw, Gtk
from wand.version import MAGICK_VERSION_FEATURES, MAGICK_VERSION_INFO, VERSION

from halftone import constants # pyright: ignore


class HalftoneAboutDialog:
    def __init__(self) -> None:
        self.dialog: Adw.AboutDialog = None

        self._setup()
        self._setup_debug_info()

    """
    Setup methods
    """

    def _setup(self) -> None:
        self.dialog = Adw.AboutDialog(
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
        self.dialog.add_legal_section(
            title="ImageMagick",
            copyright=None,
            license_type=Gtk.License.MIT_X11,
            license=None
        )

    def _setup_debug_info(self) -> None:
        magick_version = f"ImageMagick: {".".join(map(str, MAGICK_VERSION_INFO))}"
        wand_version = f"Wand: {VERSION}"
        magick_features = f"Features: {MAGICK_VERSION_FEATURES}"

        info_list = [magick_version, wand_version, magick_features]

        debug_info = ""
        for info in info_list:
            debug_info += info + "\n"

        self.dialog.set_debug_info(debug_info)
        self.dialog.set_debug_info_filename("halftone-debug-info")

    """
    Public methods
    """

    def show(self, parent: Optional[Gtk.Widget] = None) -> None:
        self.dialog.present(parent)
