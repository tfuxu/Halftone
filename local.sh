#!/usr/bin/bash

# Copyright (C) 2022-2023, Gradience Team
# Copyright 2023, tfuxu <https://github.com/tfuxu>
# SPDX-License-Identifier: GPL-3.0-or-later

read -p "Do you want to install Python requirements? [N/y] " answer

if [[ "$answer" == "y" ]]; then
    pip3 install -r requirements.txt
elif [[ "$answer" == "n" || "$answer" == "" ]]; then
    echo "Skipping requirements installation"
fi

echo "Cleaning builddir directory"
rm -r builddir

echo "Rebuilding"
meson setup builddir
meson configure builddir -Dprefix="$(pwd)/builddir" -Dbuildtype=debug
ninja -C builddir install

echo "Running"
ninja -C builddir run
