# ADR-0001: Radxa ZERO 3W platform sources

## Status

Proposed. The received V1.12M board and its AIC8800D80 radio are identified, and a working Radxa OS diagnostic baseline was recorded on 2026-10-21. Final Buildroot source selection still requires kernel/driver/accessory compatibility and firmware redistribution checks. This record does not establish a working Buildroot image or complete [task #5](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5).

## Date

2026-10-14; hardware/version evidence updated 2026-10-21.

## Context

The approved [specification](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4) targets a Radxa ZERO 3W with 1 GB RAM, no eMMC and microSD boot. The board arrived on 2026-10-21; the owner read its PCB marking as **V1.12M**. Linux identifies the radio as AIC8800D80 over SDIO. The module supplier/model beneath the QR sticker was not visually verified.

The first delivery needs onboard Wi-Fi AP and Bluetooth, an Android accessory USB gadget, computer-editable configuration, persistent pairing and normal car USB power operation. Existing Pi targets must remain supported. eMMC-equipped variants are outside this delivery.

The repository pins Buildroot 2026.02.3 at `679b9ead7620bbf193620d1ebf56f53c1764d37a`. Its Pi kernel and accessory patches are a working Pi baseline, not a Radxa BSP.

## Decision established by the approved plan

Keep Buildroot and the existing external tree. Add board-local boot/image/runtime integration and reuse the common application. Do not update the Buildroot submodule or change Pi source pins as a side effect.

Build the AIC SDIO path for this hardware rather than the older AP6212 path. Radxa OS is a temporary diagnostic reference; Buildroot remains the delivered image platform. The snapshots below are **audit references and candidates, not a selected release bill of materials**. Before a defconfig is implemented, record the complete selected source combination, hashes and required patch adaptations. Matching a Debian package version to a source snapshot requires provenance evidence, not just the same kernel version number.

## Physical diagnostic baseline: 2026-10-21

Collected over SSH from the owner's board after installing the official [Radxa OS b1 image](https://github.com/radxa-build/radxa-zero3/releases/tag/rsdk-b1). No distribution upgrade, replacement kernel or firmware update was performed. Local Wi-Fi provisioning and SSH/hostname setup were added to the flashed card; network credentials and addresses are intentionally omitted here.

| Component | Observed version or identity | Evidence |
| --- | --- | --- |
| Board | ZERO 3W, PCB V1.12M, purchased 1 GB/no-eMMC variant | Owner-read revision; RK3566 marking; empty eMMC footprint in photographs |
| RAM/storage | 973 MiB usable RAM; 29.1 GiB microSD, root on `mmcblk1p3` | `free -h`, `lsblk`; no eMMC block device enumerated |
| Diagnostic image | `radxa-zero3_bookworm_kde_b1.output_512.img.xz`, release `rsdk-b1` | Official download and SHA-512 verification before decompression |
| OS/build | Debian 12 Bookworm; RSDK build `Tue, 15 Jul 2025 03:55:44 +0000` | `/etc/os-release`, `/etc/radxa_image_fingerprint`; `RSDK_REVISION` is empty |
| Running kernel | `6.1.84-10-rk2410-nocsf`, aarch64 | `uname -a`; image package `6.1.84-10`, source-package field `linux-upstream` |
| Kernel metapackage | `linux-image-radxa-zero3` `6.1.84-10` | Source-package field `linux-rk2410-nocsf` |
| Installed U-Boot packages | `u-boot-radxa-zero3` `2017.09-51-4db083c`; `u-boot-rk2410` `2017.09-51-f7a5177` | `dpkg-query`; these are installed package versions, not a captured serial boot banner or verified upstream source commits |
| Device-tree identity | `radxa,zero3w-aic8800ds2 radxa,zero3 rockchip,rk3566` | `/proc/device-tree/compatible`; compatible strings do not identify the exact DT source revision |
| Radio silicon | AIC8800D80; `chip_id=7`, `chip_sub_id=2` | Kernel boot log: `aicwf_sdio_chipmatch USE AIC8800D80` |
| SDIO functions | `c8a1:0082` → `aicwf_sdio`; `c8a1:0182` → `aicbsp_sdio` | `/sys/bus/sdio/devices/*/{vendor,device,uevent}` |
| Wi-Fi driver | `aic8800_fdrv` `6.4.3.0`; srcversion `041C32F5C9EA4EFB673DA78` | `/sys/module/aic8800_fdrv/{version,srcversion}` |
| Radio BSP module | `aic8800_bsp` `1.0`; srcversion `735249D0F60042EF8A111A7` | `/sys/module/aic8800_bsp/{version,srcversion}` |
| AIC driver/firmware packages | `aic8800-sdio-dkms` and `aic8800-firmware`, both `4.0+git20241119.06da8476-1` | `dpkg-query`; package version and module version are different identifiers |
| Bluetooth userspace | BlueZ `5.66-1+deb12u2` | `dpkg-query` |
| Board initialization | `rsetup` / `rsetup-config-aic8800-ttys1` `0.4.16`; `radxa-otgutils` `0.3.2` | `dpkg-query` |
| Bluetooth UART setup | `hciattach -s 1500000 /dev/%I any 1500000 flow nosleep`, preceded by AIC reset | Installed `rsetup-hciattach@.service` and `rsetup-aic8800-reset@.service`; package selects `ttyS1` |

The compressed image's verified SHA-512 is:

```text
6f9f67df6f997bef41aac2cc568ebb4b7820216be1256a49ce472cb877684c08ad793ff726da3155a02f0eab60b2b2c9318168b3cf8fab81849ae91e8724f10d
```

The unmodified decompressed image's SHA-256 is `f530b3081332811d63e8250cad744aa032ea7cfcd127897f43d7ae2e6eabb892`. The installer verified the written image by reading it back **before** adding local configuration. These hashes identify the upstream diagnostic image, not the subsequently configured and booted card.

### Firmware observed loading

The kernel log names the following files under `/lib/firmware/aic8800_fw/SDIO/aic8800D80/`. SHA-256 values were calculated from those installed files. Other firmware variants in the Debian package were not established as required for this board.

| File | SHA-256 |
| --- | --- |
| `fw_patch_table_8800d80_u02.bin` | `ad83e162ac9f6aa033f3b18315d8830bcb13d8cc945bec2c8ec810a2b6eaed47` |
| `fw_adid_8800d80_u02.bin` | `a526cbd02fcdc495f049f3ad6b5933cb08cd984b16790c716a060d582fee1a56` |
| `fw_patch_8800d80_u02.bin` | `96514eb2790783deea3390811473519fd19640c26c532d4263eb8923d2fbb497` |
| `fw_patch_8800d80_u02_ext0.bin` | `f1f5048c094c74103b1a0e11cb6898fc18de9ee532cef90967d80745ee8573a1` |
| `fmacfw_8800d80_u02.bin` | `2ce84b41de107c43656f98899e86bc65c13afda15ca780c629aead20f3bc56ad` |
| `aic_userconfig_8800d80.txt` | `56c039d10af63c888b18890f508968a143f034de279fd2c4ec7ee65133e3dbdb` |

The installed package maps to official [tag `4.0+git20241119.06da8476-1`](https://github.com/radxa-pkg/aic8800/tree/fc7cbdd1791416c2457fa27a59e508bf325c9c3f), full source commit `fc7cbdd1791416c2457fa27a59e508bf325c9c3f`. All six files above match the SHA-256 of `src/SDIO/driver_fw/fw/aic8800D80/` at that commit. The `06da8476` portion identifies an imported AIC SDK revision; it is not a commit resolvable in the Radxa packaging repository. This pinned tag is the radio reference for the first compatibility build, replacing the newer, untested AIC audit snapshot below as the baseline to reproduce.

The installed firmware copyright file and the tag's [copyright metadata](https://github.com/radxa-pkg/aic8800/blob/fc7cbdd1791416c2457fa27a59e508bf325c9c3f/debian/copyright) declare `Files: *`, Radxa copyright and GPL-3+, without separate AIC binary terms. This packaging metadata alone does not resolve the firmware's redistribution/source obligations. Resolve the selected binaries' terms before including them in a downloadable Buildroot release.

### Capability evidence and limits

- Physical microSD boot and SSH succeeded on V1.12M. `/`, `/config` and `/boot/efi` are mounted from microSD in **Radxa OS**; the future Buildroot partition layout is not tested by this result.
- `wlan0` connected on 5 GHz, channel 100, 80 MHz width. `iw list` advertises AP and AP/VLAN modes. A hostapd AP, regulatory/channel behavior and Bluetooth coexistence have not been tested.
- `bluetoothctl show` reports a powered controller. Pairing, the dongle Bluetooth profiles and reconnection have not been tested.
- `/sys/class/udc/fcc00000.usb` exists. Accessory gadget binding, enumeration, accessory-start uevents and Android Auto have not been tested.
- The owner powered the board from a USB outlet for this diagnostic session. The exact supply/port/cable and car USB acceptance were not recorded or measured.

Reproduce the version inventory with `uname -a`, `dpkg-query -W`, the module/sysfs paths above, `iw dev`, `iw list`, `bluetoothctl show` and `lsblk`. Use a privileged kernel-log read to identify loaded firmware, then `sha256sum` on those files. Do not publish Wi-Fi credentials, SSIDs or Bluetooth/MAC addresses with the evidence.

## Source findings

| Component | Audited source/reference | What this establishes | Remaining verification |
| --- | --- | --- | --- |
| U-Boot | [v2026.01](https://github.com/u-boot/u-boot/tree/v2026.01), commit `127a42c7257a6ffbbd1575ed1cbaa8f5408a44b3` | Includes `radxa-zero-3-rk3566_defconfig`, default ZERO 3W DT and ZERO 3W/3E SPL DT list | Build with the chosen BL31/DDR components and boot the actual 1 GB no-eMMC board |
| Mainline Linux reference | [v6.12](https://github.com/torvalds/linux/tree/v6.12), commit `adc218676eef25575469234709c2d87185ca223a` | ZERO 3W DT, enabled microSD controller and OTG-capable DWC3 controller are present | Select a maintained, pinned release; verify radio DT requirements, peripheral role, accessory patches and hardware operation |
| Radxa vendor kernel reference | [Radxa kernel submodule](https://github.com/radxa/kernel/tree/fd366906451692033f1ba273e77e7e2f936c78db), commit `fd366906451692033f1ba273e77e7e2f936c78db` | Official `linux-rk2410-nocsf` packaging points to `linux-6.1-stan-rkr4.1`; audited source Makefile reports 6.1.84 | Identify packaging/BSP modifications, source compatibility, maintained pin and accessory patch porting needs |
| Radxa BSP reference | [bsp snapshot](https://github.com/radxa-repo/bsp/tree/8296ccd2a51e7ad7f41529b1045f8bfd1392dba3), commit `8296ccd2a51e7ad7f41529b1045f8bfd1392dba3` | Official documentation lists `radxa-zero3` under the `rk2410` U-Boot profile | Pin resulting source plus required BSP patches/configuration if the vendor route is selected |
| Boot DDR/firmware | Existing Buildroot `rockchip-rkbin` pin `f43a462e7a1429a9d407ae52b4745033034a6cf9` | Existing RK3566 Buildroot example uses an RK3566 DDR binary; package has source/license hashes | Confirm DDR filename/version and BL31 choice for the selected ZERO 3W boot chain |
| AIC8800 candidate | [Radxa driver snapshot](https://github.com/radxa-pkg/aic8800/tree/e9e43ed79c50483080e9bcdfb08caeeb869d7191), commit `e9e43ed79c50483080e9bcdfb08caeeb869d7191` | SDIO driver, Bluetooth low-power module and cfg80211 AP start/stop operations exist | Confirm actual radio/transport, kernel compatibility, Bluetooth initialization and firmware/calibration files |

The mainline Linux v6.12 snapshot is used to inspect a known source baseline near the existing accessory patches. It is not a recommendation to ship an unmaintained initial release. A supported stable revision and its download hash must be selected for implementation.

### Boot and storage

The [ZERO 3W DT](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/arch/arm64/boot/dts/rockchip/rk3566-radxa-zero-3w.dts) aliases eMMC, microSD and radio controllers separately. The shared board DT enables the microSD controller. A no-eMMC board must not inherit Pi partition assumptions or require a populated eMMC controller to boot.

The inherited [RK356x controller](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/arch/arm64/boot/dts/rockchip/rk356x.dtsi) uses `rockchip,rk3568-dwc3`/`snps,dwc3` and `dr_mode = "otg"` for the first controller. This is source evidence for a DWC3 integration, not proof that the physical port enters peripheral mode or handles accessory negotiation. Pi's unconditional `dwc2` loading must not be reused as the Radxa initialization contract.

[U-Boot's Rockchip documentation](https://docs.u-boot.org/en/latest/board/rockchip/rockchip.html) describes the Rockchip TPL/SPL/BL31 boot-image requirements and raw SD placement. Image generation must include that boot structure before normal flash-and-boot installation can be claimed.

### Wireless driver and Bluetooth

[Radxa's FAQ](https://docs.radxa.com/en/zero/zero3/faq) describes different wireless modules across revisions. RAM size and absence of eMMC do not identify the radio. Do not select an AIC or Broadcom driver from the product-family name alone.

The received board uses the AIC SDIO path. Both the initial [audited Makefile](https://github.com/radxa-pkg/aic8800/blob/e9e43ed79c50483080e9bcdfb08caeeb869d7191/src/SDIO/driver_fw/driver/aic8800/Makefile) and the now-identified [baseline Makefile](https://github.com/radxa-pkg/aic8800/blob/fc7cbdd1791416c2457fa27a59e508bf325c9c3f/src/SDIO/driver_fw/driver/aic8800/Makefile) enable `aic8800_bsp`, `aic8800_fdrv` and `aic8800_btlpm`. The default Ubuntu path derives the kernel directory/version from the host's `uname`; it also sets `CONFIG_USE_FW_REQUEST = n`. A Buildroot package must control the target kernel/module build and verify the driver's firmware-loading route instead of using host DKMS or installing Debian packages into the image. Preserve required fixes from the baseline's `debian/patches/series`, including its Linux 6.12 compatibility patch; the unpatched SDK is not equivalent to the installed DKMS package.

The [SDIO cfg80211 implementation](https://github.com/radxa-pkg/aic8800/blob/e9e43ed79c50483080e9bcdfb08caeeb869d7191/src/SDIO/driver_fw/driver/aic8800/aic8800_fdrv/rwnx_main.c) registers AP operations. This makes AP functionality a credible candidate for testing; it does not prove hostapd reliability, regulatory/channel operation or concurrent Bluetooth on the owner's board. Bluetooth low-power module presence also does not establish a fully initialized HCI controller.

### Download hashes and distribution metadata

Keep custom source/hash files scoped by board and kernel source; do not let a Radxa tarball use the Pi kernel hash. Buildroot's [custom hash and kernel-module mechanisms](https://buildroot.org/downloads/manual/manual.html) support external board packages. The checked-out `pkg-kernel-module.mk` builds modules against `LINUX_DIR` with target flags and handles module installation.

The audited [rkbin license](https://github.com/rockchip-linux/rkbin/blob/f43a462e7a1429a9d407ae52b4745033034a6cf9/LICENSE) grants use/copy/distribution and requires notices to remain. Buildroot classifies the package as proprietary. Preserve the actual notices and source/license hashes.

Radxa's [driver copyright metadata](https://github.com/radxa-pkg/aic8800/blob/e9e43ed79c50483080e9bcdfb08caeeb869d7191/debian/copyright) distinguishes GPL-3+ packaging and GPL-2 source. Verify notices and redistribution terms for the selected firmware/calibration binaries separately; repository-level driver licensing alone does not establish the required binary-file terms.

The checked-out Armbian firmware package sets `ARMBIAN_FIRMWARE_REDISTRIBUTE = NO` when firmware is selected. Its AP6212 option is therefore not sufficient evidence for including those files in this project's downloadable release image. If an older radio is received, identify an appropriate, documented firmware source before packaging it.

## Alternatives considered

### Mainline bootloader/kernel plus the appropriate radio package

Preferred candidate to evaluate because upstream ZERO 3 boot configuration and DT exist, and board-local configuration fits the current external tree. Radio and accessory compatibility remain explicit integration work; source presence does not guarantee operation.

### Radxa vendor bootloader/kernel source through the official BSP

Fallback candidate if it provides necessary radio/board support unavailable on the maintained upstream choice. Radxa's [U-Boot instructions](https://docs.radxa.com/en/zero/zero3/low-level-dev/u-boot) state that BSP source preparation adds changes; copying only a branch name or Debian package is insufficient. The existing 6.12 accessory patches cannot be assumed to apply to the audited 6.1 vendor kernel.

### Replace Buildroot with Radxa OS or assume Pi drivers work

Not selected. The approved plan retains Buildroot and the existing common application. A complete distribution replacement exceeds this task, while unconditional Pi driver/boot assumptions do not match the inspected Radxa sources.

## Accessory source compatibility: 2026-10-21

The next investigation compared the existing accessory patches with immutable vendor and maintained upstream sources. Checks used downloaded copies of the affected source files in `/tmp`; the Buildroot submodule and Pi patches were not modified.

| Candidate | Source-level result | Implication |
| --- | --- | --- |
| Vendor Linux 6.1.84, `fd366906451692033f1ba273e77e7e2f936c78db` | Already has `USB_CONFIGFS_UEVENT`, `create_function_device()` and parts of the `CONFIG_USB_CONFIGFS_F_ACC` hooks, but no `function/f_accessory.c` or accessory headers. `git apply --check` rejects the first Pi patch in Kconfig, configfs and composite.h. | A vendor path requires a scoped adaptation, not blindly applying both Pi patches or adding duplicate uevent code. Its `class_create(THIS_MODULE, ...)` API also differs from 6.12. |
| Upstream Linux 6.12.114, [`85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e`](https://github.com/gregkh/linux/tree/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e) | Both existing accessory patches pass `git apply --check` and apply in order. The resulting sources contain `ACCESSORY=START`, gadget state uevents and the registered-handler API. The first patch emits a pre-existing trailing-whitespace warning. | Preferred candidate for the first compatibility build. Patch application alone does not establish compilation, AIC/DT compatibility, boot or USB operation. |

Linux 6.12.114 was listed as non-EOL longterm by [kernel.org](https://www.kernel.org/releases.json) on 2026-10-21. This is an experiment pin, not a final release choice. The running Radxa OS kernel remains the separate 6.1.84 diagnostic reference. The AIC device tree and UART/reset requirements still need validating on upstream; the generic ZERO 3W DT must not silently substitute AP6212 initialization for this board.

### ARM64 compilation slice

The compatibility build used Clang/LLVM `23.1.3`, `bc` `1.07.1`, the upstream ARM64 `defconfig` and the exact archives below. The kernel archive matched kernel.org's `sha256sums.asc`; the AIC archive is pinned by its Git commit and recorded download hash.

| Source archive | SHA-256 |
| --- | --- |
| [linux-6.12.114.tar.xz](https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.12.114.tar.xz) | `7a8589912bd7a8adb07fed074283652cf482a35facef8954554654f0154b4af3` |
| [AIC source at fc7cbdd](https://codeload.github.com/radxa-pkg/aic8800/tar.gz/fc7cbdd1791416c2457fa27a59e508bf325c9c3f) | `cae09dc427fc6c4a7a1887b44612c8a30b39596fe04aeaaec66b8de6581eaa06` |

Compilation exposed three problems that patch-application checks did not detect:

| Reproduced failure | Scoped correction | Result |
| --- | --- | --- |
| `hid_report_raw_event` requires six arguments; accessory backport supplies five | `board/radxa/zero3w/patches/linux/0003-Pass-HID-buffer-size-for-Linux-6.12.114.patch` supplies the completed request length as both readable-buffer and report-data size | `libcomposite.o` and `usb_f_accessory.o` compile for ARM64 |
| `cfg80211_ops.set_monitor_channel` includes a net-device argument, but the patched SDK enables that path only at 6.13+ | `patches/aic8800/0001-Handle-monitor-callback-in-Linux-6.12.114.patch` enables the existing signature and both internal call sites for the pinned 6.12.114 candidate | Callback type error resolved |
| Two RX preallocation definitions use `()` despite existing `(void)` declarations, rejected by Clang's strict-prototype check | `patches/aic8800/0002-Use-strict-RX-preallocation-prototypes.patch` matches the existing header declarations | All three AIC aggregate objects compile for ARM64 |

The AIC patch paths above are relative to `aa_wireless_dongle/board/radxa/zero3w/`. These are preparation patches for the pinned candidates. No active defconfig consumes them yet. Future integration must apply the existing two shared accessory patches **before** the Radxa HID patch, and the official AIC Debian patch series **before** the two scoped AIC patches. Give Radxa its own Linux download hash; do not select the Pi Linux hash or apply the Radxa-only patches to the retained Pi pin.

To reproduce on fresh, verified source extractions, set `RADXA_LINUX_SRC`, `RADXA_AIC_SRC`, `RADXA_OUT` and `RADXA_REPO` to absolute paths. `RADXA_AIC_SRC` is the archive root containing `src/` and `debian/`. Host tools must include LLVM/Clang, make, flex, bison and bc.

```sh
set -eu
for patch in "$RADXA_REPO"/aa_wireless_dongle/patches/linux/*.patch; do
    git -C "$RADXA_LINUX_SRC" apply "$patch"
done
git -C "$RADXA_LINUX_SRC" apply "$RADXA_REPO/aa_wireless_dongle/board/radxa/zero3w/patches/linux/0003-Pass-HID-buffer-size-for-Linux-6.12.114.patch"
while read -r patch rest; do
    case "$patch" in ''|\#*) continue ;; esac
    git -C "$RADXA_AIC_SRC" apply --include='src/SDIO/**' "$RADXA_AIC_SRC/debian/patches/$patch"
done < "$RADXA_AIC_SRC/debian/patches/series"
for patch in "$RADXA_REPO"/aa_wireless_dongle/board/radxa/zero3w/patches/aic8800/*.patch; do
    git -C "$RADXA_AIC_SRC" apply "$patch"
done
make -C "$RADXA_LINUX_SRC" O="$RADXA_OUT" ARCH=arm64 LLVM=1 defconfig
"$RADXA_LINUX_SRC/scripts/config" --file "$RADXA_OUT/.config" \
    --module USB_LIBCOMPOSITE --module USB_CONFIGFS \
    --enable USB_CONFIGFS_UEVENT --enable HID --enable USB_CONFIGFS_F_ACC \
    --module CFG80211 --enable MMC --module BT --module BT_HCIUART
make -C "$RADXA_LINUX_SRC" O="$RADXA_OUT" ARCH=arm64 LLVM=1 -j8 olddefconfig modules_prepare
make -C "$RADXA_LINUX_SRC" O="$RADXA_OUT" ARCH=arm64 LLVM=1 -j8 \
    drivers/usb/gadget/libcomposite.o drivers/usb/gadget/function/usb_f_accessory.o
make -C "$RADXA_LINUX_SRC" O="$RADXA_OUT" ARCH=arm64 LLVM=1 -j8 \
    M="$RADXA_AIC_SRC/src/SDIO/driver_fw/driver/aic8800" \
    aic8800_bsp/aic8800_bsp.o aic8800_fdrv/aic8800_fdrv.o aic8800_btlpm/aic8800_btlpm.o
```

All five resulting files were inspected as ELF 64-bit ARM aarch64 objects. No compiler checks were disabled; existing nonfatal SDK warnings remain. The existing proxy socket/diagnostics regression test passed with local socket access enabled. This verifies object compilation only: full kernel/module linking, target DT/boot-chain integration, a Buildroot image and physical operation remain pending. Build logs were kept locally under `/tmp/radxa-build-check/` (`compile.log`, `compile-after-hid.log`, `compile-after-aic.log`, `compile-after-prototypes.log`); these temporary files are not release artifacts.

## Consequences and next evidence

- Source research can proceed now, but task #5 stays open. Dependent tasks retain their tracker prerequisites.
- PCB V1.12M and AIC8800D80 identification are resolved. Complete the compatible source/firmware selection using the recorded baseline and source checks.
- Verify accessory patch/configuration compatibility and the selected radio build before promoting this ADR to Accepted.
- MicroSD boot, AP/Bluetooth coexistence, USB enumeration/negotiation, power and connection reliability remain physical acceptance checks in subsequent tasks.
- Do not publish a supported image or close hardware criteria based on this source investigation.

## Verification performed

On 2026-10-14, checked the existing Buildroot version and Pi source/patch configuration using task #5's commands and inspected the cited source snapshots. On 2026-10-21, collected the physical diagnostic evidence above, resolved the AIC package tag, matched all six loaded firmware/configuration files against that source, performed vendor/upstream accessory patch checks and reproduced/fixed the three ARM64 object-compilation failures above. No Buildroot target image or car-operation result is established by these checks.
