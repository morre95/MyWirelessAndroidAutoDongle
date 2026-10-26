# Adding a board

This guide lists every place where a board plugs into the image pipeline. The
Radxa ZERO 3W port is the worked example: each step names the file it used.
Paths are relative to the repository root.

A board needs USB OTG/gadget mode, Wi-Fi with access-point support, Bluetooth,
and must run from the car's USB power. See the [Radxa platform ADR](adr/0001-radxa-zero3w-platform.md)
for how the Radxa sources were chosen and verified.

## Rules

- Keep the common application shared. Don't add board-name conditionals to
  the Bluetooth, USB or proxy code in `aa_wireless_dongle/package/aawg/`.
- Don't copy the common daemon or the whole common overlay into a board
  directory. Override only the files that really differ.
- Don't change the Buildroot submodule or another board's source pins as a side
  effect.
- Keep download hash checking on. Pin every source and firmware version.

## Checklist

### 1. Defconfig

`aa_wireless_dongle/configs/<board>_defconfig`. Example:
`radxa-zero3w_defconfig`.

It owns the architecture and toolchain, the kernel version or tarball, the
in-tree device tree, the bootloader and its firmware blobs, the packages to
bundle, the root filesystem size and the post-build/post-image hooks. Set:

- `BR2_GLOBAL_PATCH_DIR` to the shared `aa_wireless_dongle/patches` plus the
  board's own `patches` directory;
- `BR2_DOWNLOAD_FORCE_CHECK_HASHES=y`, with a hash file for every custom
  download (Radxa: `board/radxa/zero3w/patches/linux/linux.hash`);
- `BR2_ROOTFS_OVERLAY` to `board/common/rootfs_overlay` followed by the board
  overlay;
- the same `BR2_PACKAGE_*` set for the dongle (`AAWG`, BlueZ, hostapd,
  dnsmasq, uMTPrd, Dropbear) as the existing defconfigs.

The defconfig name is the board id everywhere else: Compose, CI and release
assets.

### 2. Kernel configuration and patches

- `board/common/kernel.config` holds the kernel options every board needs.
  Add board-only options in a fragment and list both in
  `BR2_LINUX_KERNEL_CONFIG_FRAGMENT_FILES`. Radxa: `board/radxa/zero3w/linux.fragment`
  builds the USB accessory gadget in.
- `aa_wireless_dongle/patches/linux/` holds the shared Android accessory
  patches (`0001`, `0002`). Check that they apply to the board's kernel.
- Board-only kernel patches go in the board's `patches/linux/`, numbered after
  the shared ones. Radxa: `0003` to `0006`, covering the device tree, GPIO
  defaults and kernel-version fixes.

### 3. Boot and image layout

The board directory, `aa_wireless_dongle/board/<vendor>/<board>/`, owns how the
card boots and is laid out. Radxa: `board/radxa/zero3w/`.

- **Boot configuration:** Radxa uses U-Boot with `extlinux.conf`; the Pi boards
  use `config.txt` and `cmdline.txt`.
- **`genimage.cfg`:** the partition layout. Keep the computer-visible FAT
  partition labelled `WirelessAA` and holding `aawgd.conf`, plus a `persist`
  partition. Radxa places the bootloader raw at 32 KiB, before the first
  partition.
- **`post-build.sh`:** moves `aawgd.conf` to the boot partition and links
  `/etc/aawgd.conf` to it, so users can edit settings from a computer.
- **Post-image hook:** Radxa uses Buildroot's `support/scripts/genimage.sh`
  with `BR2_ROOTFS_POST_SCRIPT_ARGS`; the Pi boards use their own
  `post-image.sh`.

### 4. Board overlay

`board/<vendor>/<board>/rootfs_overlay/` holds only the files that differ from
`board/common/rootfs_overlay/`. Radxa has two:

- `etc/fstab`: its microSD partitions are `mmcblk1p1` and `mmcblk1p3`;
- `etc/hostapd.conf.in`: 5 GHz channel 36 instead of 2.4 GHz channel 6.

The daemon expects the wireless interface to be `wlan0`. It finds the USB
device controller under `/sys/class/udc` by itself, so no controller name is
configured per board.

### 5. Drivers, firmware and startup

- Wireless and Bluetooth drivers that aren't in the kernel get a package under
  `aa_wireless_dongle/package/`, sourced from `package/Config.in`. Radxa:
  `aic8800` (driver modules), `aic8800-firmware` and `aic8800-startup`.
- Patches to such a package go in the board's `patches/<package>/`, which
  `BR2_GLOBAL_PATCH_DIR` picks up. Radxa: `board/radxa/zero3w/patches/aic8800/`.
- Ship only firmware with clear redistribution terms, and keep its licence
  file. Radxa uses the AIC8800D80 files from linux-firmware under `LICENSE.aic`.
- Board startup goes in an init script installed by the board's package or
  overlay. Radxa: `S38radio` (in `package/aic8800-startup/src/`) loads the
  drivers, waits for firmware readiness, resets the Bluetooth controller and
  attaches it before BlueZ starts. The Pi boards load `brcmfmac`, `hci_uart`
  and `dwc2` in `board/raspberrypi/rootfs_overlay/etc/init.d/S00modules`.
  Don't put one board's driver loading in the common overlay.

### 6. Compose, build script, CI and release

- `docker-compose.yml`: add a service based on `generate_image_donotuse` with
  `BOARD_NAME=<defconfig>`. Radxa: `radxa-zero3w`, which writes
  `images/sdcard-radxa-zero3w.img`.
- `build.sh`: boards are the Compose services named `rpi*` or `radxa*`. For
  another prefix, extend the `grep -E` pattern; add a label in `board_label()`.
- `.github/workflows/build.yml`: add the defconfig to the build matrix. Each
  job uploads `<defconfig>-sdcard.img.xz` and its `.sha256`. Radxa also needs
  the "Free disk space" step, because its build takes about 14 GB.
- Release: `.github/workflows/release.yml` downloads the build run's artifacts
  by name pattern (`WirelessAndroidAutoDongle-raspberrypi*` and
  `WirelessAndroidAutoDongle-radxa*`). A board whose defconfig starts with
  something else needs its own download step, or its image is left out of the
  release. Never use the `-all` artifact, which duplicates every image.
- `BUILDING.md`: add the board's row to the Compose table.

### 7. Verification

- **Host tests** in `tests/`, for every changed script and shared behaviour.
  Radxa: `tests/radxa_*_test.py` for the image layout, packages and startup
  helpers, and `tests/build_sh_test.py` for `build.sh`. Run each with
  `python3 tests/<name>.py`.
- **Image checks** against a fresh build: partitions, boot files, `fstab`
  and the `WirelessAA` label. Radxa: `tests/radxa_image_test.py`, with
  `RADXA_OUTPUT` pointing at the build directory.
- **Bring-up diagnostics** that are not shipped in the image go in the board's
  `checks/` directory. Radxa: `board/radxa/zero3w/checks/`, with its own
  `README.md`.
- **Hardware record** in `docs/hardware-validation/<board>.md`: board revision,
  radio, phone, head unit, cable, and the results for first pairing, cold
  start time, reconnects, a long session and a settings change.
- **Pi regression:** after any change to shared files, build the Pi boards and
  check at least one on hardware.
- **Docs:** add the board to the README, first under "In testing", with its
  USB port and cable and its known limitations.
