<img src="data/icons/hicolor/scalable/apps/com.github.tfuxu.pixely.svg" align="left" height="150px" vspace="10px">

Pixely
======

Give your images a pixel art-like style and reduce the file size in the process with Pixely.

<br>

![pixely-light](data/screenshots/pixely-light.png#gh-light-mode-only)
![pixely-dark](data/screenshots/pixely-dark.png#gh-dark-mode-only)

## What is Pixely?
Pixely is a simple Libadwaita app for lossy image compression using quantization and dithering techniques.

## Why would I use it?
Because it's fun! And it also can significantly reduce image size.

<details>
<summary>What is that dithering?</summary>
Dithering is a technique used on old systems with limited color range to more accurately display graphics containing higher amount of colors than what the device could handle. It was commonly used in early Macintosh computers, Nintendo Game Boy and many other systems from the 80s and 90s.

##### Wanna learn more about how dithering works? 
Check out [this<sup>↗</sup>](https://surma.dev/things/ditherpunk/) article which nicely explains how dithering argorithms works (warning, math!) and shows most popular dithering algorithms in action.
</details>

## Features:
- **Three different dither algorithms:**
  You can choose between the classic Floyd-Steinberg algorithm, interesting Riemersma and Bayer (_a.k.a_ ordered) dither known from Game Boys.
- **Live preview:**
  Check out how your image will look like in real time with live preview feature.
- **Convert to many formats:**
  In addition to dithering, you can convert your images to different formats to save up some space on disk.
- **It's just that simple.**
  Everything is as simple as possible, so that you could start dithering your images as soon as you install the app.

## How to install Pixely
You can install Pixely in many ways, here are some listed:

**1. Official Flatpak package:**

<a href='https://flathub.org/apps/details/com.github.tfuxu.pixely'>
  <img width='192' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-i-en.png'/>
</a><br>

**2. Alternative package distributions:**
> **Warning**
> Although some of the methods listed here may be maintained by the Pixely maintainers, these methods **are not** officially supported and issues related to packaging in them should be reported outside this project's bug tracker.

<a href="https://repology.org/project/pixely/versions">
    <img src="https://repology.org/badge/vertical-allrepos/pixely.svg" alt="Packaging status" align="left">
</a><br><br>

**3. Install from source:**

If you don't find any other options appealing to you, then you can always compile code on your machine from source and install it that way. For more information, check out [How to build?](#how-to-build) section.

## How can I contribute?
Thanks for asking! I always appriciate when someone wants to contribute to any project, and here you are who want to contribute to my project! Just for you, I've created this list of things that you need to do if you want to contribute to Pixely:
1. Read [Code of Conduct](CODE_OF_CONDUCT.md)
2. Fork this repository: https://github.com/tfuxu/Pixely/fork
3. Clone your fork: `git clone https://github.com/👁️you👁️/Pixely.git`
4. Create a local branch with your changes: `git checkout -b new-thingies`
5. When changing stuff in Python, try to follow [PEP8](https://pep8.org/)
6. Commit your changes (please do the signed commits): `git commit -S`
7. Push the changes to fork: `git push origin new-thingies`
8. Create a new pull request

## How to build?

### GNOME Builder:
This is the easiest way of building Pixely if you want to build it as a Flatpak package. Highly recommended, but probably not for everyone, as GNOME Builder and Flatpak can be quite resource hungry.

1. Download [GNOME Builder](https://flathub.org/apps/details/org.gnome.Builder).
2. In Builder, click the _Clone Repository_ button at the bottom, using `https://github.com/tfuxu/Pixely.git` as the URL.
3. Click the _Build_ button at the top once the project is loaded.

### Flatpak Builder:
This is a little bit more advanced way of building Flatpak packages, but if you don't want or can't have GNOME Builder, then this method would be your best bet.

#### Prerequisites:

- Flatpak Builder `flatpak-builder`
- GNOME SDK runtime `org.gnome.Sdk//44`
- GNOME Platform runtime `org.gnome.Platform//44`

Install required runtimes:
```shell
flatpak install org.gnome.Sdk//44 org.gnome.Platform//44
```

#### Building Instructions:

##### User installation
```shell
git clone https://github.com/tfuxu/Pixely.git
cd Pixely
flatpak-builder --install --user --force-clean repo/ build-aux/flatpak/com.github.tfuxu.pixely.json
```

##### System installation
```shell
git clone https://github.com/tfuxu/Pixely.git
cd Pixely
flatpak-builder --install --system --force-clean repo/ build-aux/flatpak/com.github.tfuxu.pixely.json
```

### Meson Build System:
If you don't want to install Pixely as a Flatpak package, you can build it using Meson build system. Meson is used in majority of GTK apps and enforced on GNOME core apps, so learning how to use it would be pretty handy if you plan to contribute to other GTK projects.

#### Prerequisites:

The following packages are required to build Pixely:

- Python 3 `python`
- PyGObject `python-gobject`
- Blueprint [`blueprint-compiler`](https://jwestman.pages.gitlab.gnome.org/blueprint-compiler/setup.html)
- GTK 4 `gtk4`
- Libadwaita (>= 1.2.0) `libadwaita`
- Imagemagick `imagemagick`
- Meson `meson`
- Ninja `ninja-build`

Required Python libraries:

```shell
pip install -r requirements.txt
```

#### Building Instructions:

##### Global installation

```shell
git clone https://github.com/tfuxu/Pixely.git
cd Pixely
meson setup builddir
meson configure builddir -Dprefix=/usr/local
sudo ninja -C builddir install
```

##### Local build (for testing and development purposes)

```shell
git clone https://github.com/tfuxu/Pixely.git
cd Pixely
meson setup builddir
meson configure builddir -Dprefix="$(pwd)/builddir"
ninja -C builddir install
ninja -C builddir run
```

> **Note** 
> During testing and development, as a convenience, you can use the `local.sh` script to quickly rebuild local builds.

## License
<p>
<img src="https://www.gnu.org/graphics/gplv3-with-text-136x68.png" alt="GPLv3 logo" align="right">
This repository is licensed under the terms of the GNU GPLv3 license. You can find a copy of the license in the COPYING file.
</p>

## Inspirations
This project was started after I discovered [Pixfect](https://github.com/daudix-UFO/Pixfect), a little Bash script that does exactly what Pixely does.

The user interface design is based on [Converter](https://gitlab.com/adhami3310/Converter) style, with itself is based on [Upscaler](https://gitlab.com/TheEvilSkeleton/Upscaler) design.

This README (mostly [How to Build?](#how-to-build) section) is based on [Gradience](https://github.com/GradienceTeam/Gradience) README.
