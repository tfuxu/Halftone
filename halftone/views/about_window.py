# Copyright 2023-2024, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk, Adw

from halftone import constants # pyright: ignore


class HalftoneAboutWindow:
    def __init__(self, parent):
        self.parent = parent
        self.app = self.parent.get_application()

        self.setup()

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
            copyright="Copyright © 2023 tfuxu",
            license_type=Gtk.License.GPL_3_0,
            version=constants.version,
            release_notes_version=constants.rel_ver,
        )

    def show_about(self):
        self.about_window.present(self.parent)
