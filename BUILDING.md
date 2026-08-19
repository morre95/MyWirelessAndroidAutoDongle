# Building Wireless Android Auto Dongle

This repository uses Buildroot to create a bootable SD-card image. Building
with Docker Compose is the recommended method because the container provides
the required build tools.

## Clone the repository

Clone the repository together with its Buildroot submodule:

```shell
git clone --recurse-submodules https://github.com/morre95/MyWirelessAndroidAutoDongle.git
cd MyWirelessAndroidAutoDongle
```

If the repository was cloned without submodules, initialize them before
building:

```shell
git submodule update --init --recursive
```

## Build with Docker Compose

Run the command from the repository root, replacing `rpi02w` with the service
for your board from the table below:

```shell
docker compose run --rm --build rpi02w
```

The first build downloads and compiles the complete cross-toolchain, so it can
take a while. Downloads and intermediate output are kept in Docker volumes to
make later builds faster.

| Board | Docker service | Buildroot defconfig | Generated image |
| --- | --- | --- | --- |
| Raspberry Pi Zero W | `rpi0w` | `raspberrypi0w_defconfig` | `images/sdcard-raspberrypi0w.img` |
| Raspberry Pi Zero 2 W | `rpi02w` | `raspberrypizero2w_defconfig` | `images/sdcard-raspberrypizero2w.img` |
| Raspberry Pi 3 A+ | `rpi3a` | `raspberrypi3a_defconfig` | `images/sdcard-raspberrypi3a.img` |
| Raspberry Pi 4 | `rpi4` | `raspberrypi4_defconfig` | `images/sdcard-raspberrypi4.img` |
| Raspberry Pi 5 | `rpi5` | `raspberrypi5_defconfig` | `images/sdcard-raspberrypi5.img` |

For an interactive shell inside the build container, run:

```shell
docker compose run --rm --build bash
```

## Build without Docker

Install the host packages required by Buildroot as described in the
[Buildroot manual](https://buildroot.org/downloads/manual/manual.html), then
run the following commands from the repository root. This example builds for
the Raspberry Pi Zero 2 W:

```shell
cd buildroot
make BR2_EXTERNAL=../aa_wireless_dongle O=output/raspberrypizero2w raspberrypizero2w_defconfig
make -C output/raspberrypizero2w
```

For another board, replace both occurrences of `raspberrypizero2w` with the
board name shown in the defconfig column, without the `_defconfig` suffix. For
example, use `raspberrypi5` for a Raspberry Pi 5.

The manually built image is created at:

```text
buildroot/output/<board>/images/sdcard.img
```

## Install the image

Write the generated `.img` file to a microSD card using Raspberry Pi Imager or
another disk-imaging tool. Select the generated file as a custom image. Writing
the image erases the selected card, so verify the destination carefully.

After flashing, see the [Install and run](README.md#install-and-run) section for
configuration, cabling, and first-time phone pairing instructions.
