# ADR-0001: Radxa ZERO 3W platform sources

## Status

Proposed for release; the engineering source baseline below is selected for subsequent integration as of 2026-10-21. Kernel/accessory/AIC linking, boot-chain packing, compiled-DT checks and three diagnostic Linux 6.12.114 boots support that choice. The 2026-10-22 boot-only experiment reached userspace with the selected DT; a later isolated radio boot confirmed firmware readiness and successful HCI Reset. Firmware redistribution terms remain unresolved. On 2026-10-23 the owner closed [task #5](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5) after tracker review, with the unresolved firmware terms recorded below and their resolution handed to [task #11](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/11). This ADR stays Proposed for release until #11 settles those terms; downstream dependencies are unchanged. This record does not establish a working Buildroot dongle image.

## Date

2026-10-14; engineering source selection updated 2026-10-21; diagnostic mainline boot and radio-reset evidence added 2026-10-22; mainline Bluetooth attachment result and task #5 closure review added 2026-10-23; shipping kernel/boot-component defconfig build added 2026-10-23.

## Context

The approved [specification](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4) targets a Radxa ZERO 3W with 1 GB RAM, no eMMC and microSD boot. The board arrived on 2026-10-21; the owner read its PCB marking as **V1.12M**. Linux identifies the radio as AIC8800D80 over SDIO. The module supplier/model beneath the QR sticker was not visually verified.

The first delivery needs onboard Wi-Fi AP and Bluetooth, an Android accessory USB gadget, computer-editable configuration, persistent pairing and normal car USB power operation. Existing Pi targets must remain supported. eMMC-equipped variants are outside this delivery.

The repository pins Buildroot 2026.02.3 at `679b9ead7620bbf193620d1ebf56f53c1764d37a`. Its Pi kernel and accessory patches are a working Pi baseline, not a Radxa BSP.

## Decision established by the approved plan

Keep Buildroot and the existing external tree. Add board-local boot/image/runtime integration and reuse the common application. Do not update the Buildroot submodule or change Pi source pins as a side effect.

Build the AIC SDIO path for this hardware rather than the older AP6212 path. Radxa OS is a temporary diagnostic reference; Buildroot remains the delivered image platform. The selected engineering baseline is recorded below; the later source-findings table preserves the earlier audit references. Matching a Debian package version to a source snapshot requires provenance evidence, not just the same kernel version number.

## Selected engineering source baseline: 2026-10-21

Use this combination for the V1.12M, 1 GB, no-eMMC AIC8800D80 target when the
remaining task #5 prerequisite is resolved. Selection fixes the inputs for
integration; it does not approve firmware distribution or hardware acceptance.
Existing Pi source pins and the Buildroot submodule remain unchanged.

| Component | Selected immutable input | Verification and scope |
| --- | --- | --- |
| Build system | Buildroot 2026.02.3, commit `679b9ead7620bbf193620d1ebf56f53c1764d37a` | Retained repository baseline; no Buildroot update required by the checks |
| Bootloader | U-Boot 2026.01, commit `127a42c7257a6ffbbd1575ed1cbaa8f5408a44b3`, release archive `u-boot-2026.01.tar.bz2`; `radxa-zero-3-rk3566_defconfig` | Isolated build/packing pass; card containing this boot chain reaches Linux diagnostic userspace; serial stage banners/training details not captured |
| DDR / BL31 | rkbin commit `f43a462e7a1429a9d407ae52b4745033034a6cf9`; `bin/rk35/rk3566_ddr_1056MHz_v1.23.bin` and `bin/rk35/rk3568_bl31_v1.44.elf` | Exact blobs verified inside the packed bootloader; retain rkbin notices; OP-TEE not selected |
| Kernel | Linux 6.12.114, commit `85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e`, release archive `linux-6.12.114.tar.xz` | Full Image/modules link; three physical boot-only snapshots reach diagnostic userspace; external modules not loaded by that experiment |
| Linux device tree | The same Linux input plus the board patches below; `rockchip/rk3566-radxa-zero-3w-aic8800d80.dtb` | Six compiled-property tests pass; five candidate property groups also pass against the radio boot's live DT; generic DT unchanged; schema and electrical timing remain unverified |
| Radio driver | Radxa AIC tag `4.0+git20241119.06da8476-1`, commit `fc7cbdd1791416c2457fa27a59e508bf325c9c3f`; `src/SDIO/driver_fw/driver/aic8800` plus the patch series below | All three modules link; selected BSP/fdrv path without btlpm reached firmware readiness and successful HCI Reset in one diagnostic boot; AP/pairing/stability remain untested |
| Radio firmware/configuration | Only the six D80 files listed under [Firmware observed loading](#firmware-observed-loading), from that same AIC commit | All six SHA-256 values match the working reference card; selection remains subject to clarification of redistribution/source obligations |

Use the source/archive hashes in [ARM64 compilation](#arm64-compilation-slice)
and [Boot-chain build and packing](#boot-chain-build-and-packing), together with
the six firmware hashes in the firmware table. Buildroot's checked-in `rockchip-rkbin.hash`
additionally pins source archive SHA-256
`4a70cdc877600b75c0a885a8ebe1aa68f0800a0010aa580c105cbd9386140fa7`.
That hash applies to Buildroot's generated
`rockchip-rkbin-f43a462e7a1429a9d407ae52b4745033034a6cf9-git4.tar.gz`,
not to a GitHub-generated tarball. Generated Image/DTB/bootloader hashes identify
particular build outputs and do not replace download verification. Mandatory
download checking must remain enabled when the shipping target is added.

The [2026-10-22 radio-test handoff](../handoffs/2026-10-22-radxa-radio-test.md)
records this limited physical result, input/evidence hashes and recovery state.
The saved kernel log also contains missing regulatory database/permissive custom
rules, an initialization-time BSP `bus down` timer message and UART-DMA warnings.
These require follow-up before AP/channel or sustained-traffic acceptance;
successful reset does not establish the complete radio runtime or clear #5.

### Required patches and startup contract

The repository patch set at commit `2247ca3` defines the selected adaptations.
Paths below are relative to `aa_wireless_dongle/`; apply each list in order.

1. Linux: shared `patches/linux/0001-Backport-and-apply-patches-for-Android-Accessory-mod.patch`,
   then `0002-Remove-cyclic-dependency-between-f_accessory-and-lib.patch` in the
   same directory. These provide the required accessory function and uevents.
2. Linux: `board/radxa/zero3w/patches/linux/0003-Pass-HID-buffer-size-for-Linux-6.12.114.patch`,
   then `0004-Add-V1.12M-AIC8800D80-device-tree.patch`, then
   `0005-Set-AIC-Bluetooth-GPIO-defaults.patch` in that directory. These supply
   the 6.12.114 HID API correction and the board-specific DT/pin defaults.
3. AIC: apply the SDIO portions of the pinned archive's `debian/patches/series`
   in listed order, then
   `board/radxa/zero3w/patches/aic8800/0001-Handle-monitor-callback-in-Linux-6.12.114.patch`
   and `0002-Use-strict-RX-preallocation-prototypes.patch` in that directory.
   Preserve the upstream packaging fixes; the raw imported SDK alone is not
   the checked source combination. Reproduction commands appear below.

Runtime integration must preserve normal BSP work mode, `CONFIG_MCU_MESSAGE=n`,
`CONFIG_PLATFORM_ROCKCHIP=n`, `CONFIG_PLATFORM_ROCKCHIP2=n`,
`CONFIG_GPIO_WAKEUP=n` and `AICBT_LPM_ENABLE_DEFAULT=0` from the audited path.
Load BSP/fdrv synchronously, require the `aic-firmware-ready.sh` predicate,
require successful bounded `aic-hci-reset /dev/ttyS1`, attach at
1.5 Mbaud/RTS-CTS, then start BlueZ after attachment is established. Stop on
failure; a fixed sleep is not the readiness contract. The helpers are in
`board/radxa/zero3w/checks/` at the repository commit above and are not yet
installed by a runtime package. Do not install the factory TCP test server or
automatically load `aic8800_btlpm`. Userspace package integration belongs to
later tasks; Debian's installed BlueZ/rsetup versions are diagnostic references.

### Why this combination and what remains unproven

Choose the upstream kernel/bootloader route because the required board support
exists, the accessory adaptations and radio modules pass full linking, and the
boot chain builds with the existing Buildroot/rkbin pins. This keeps the Pi
patch path and baseline intact. The AIC source is selected for its demonstrated
firmware provenance and compatibility, rather than replacing it with the newer,
unverified audit snapshot. The vendor kernel/BSP remains a fallback if physical
integration exposes a missing mainline capability; switching requires a new
source/patch compatibility assessment and an explicit update to this decision.

| Required capability | Evidence supporting the choice | Physical verification still required |
| --- | --- | --- |
| MicroSD boot | Reference boots; selected diagnostic card reaches Linux 6.12.114 userspace and writes FAT logs on the actual board | Complete Buildroot partition/mount layout and shipping userspace (#7–#8) |
| Android accessory and uevents | Shared patches/HID correction link; source contains required uevents; mainline `fcc00000.usb` UDC is visible | Gadget binding, enumeration, negotiation and actual uevent delivery (#9) |
| Wi-Fi AP | Pinned driver exposes AP operations; the reference advertises AP/AP-VLAN and operates as a Wi-Fi client | Selected driver/firmware on mainline, hostapd operation, channels and coexistence (#10–#12) |
| Bluetooth | Exact firmware match and ordered startup pass on Radxa OS; mainline GPIO hog directions/UART1 observed; both AIC SDIO IDs appear in one boot snapshot | Matching mainline modules/firmware, HCI reset/attachment, pairing and AP coexistence (#10–#12) |

The GPIO defaults now have mainline ownership/direction snapshots, without
radio firmware or drivers. Electrical timing, wake IRQ/suspend support and
slew-rate equivalence are not established. The controlled boot reduces
feasibility risk; complete image assembly and acceptance belong to later tasks.
Task #5 requires a source decision with evidence limits, not a completed dongle.
Its remaining external blocker is the selected firmware's terms, tracked in
[radxa-pkg/aic8800#109](https://github.com/radxa-pkg/aic8800/issues/109).
Resolve those terms and reconcile this decision with #5 before marking the ADR
Accepted or releasing downstream prerequisites. If the answer prevents using
these files, reopen the radio/firmware choice instead of treating this baseline
as an unconditional release bill of materials.

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

A follow-up found the maintainer's [licensing clarification in upstream issue #54](https://github.com/radxa-pkg/aic8800/issues/54): after checking with AIC, Radxa states that the driver source is GPL v2 and that the GPL v3 metadata came from its package template. This supports distinguishing driver-source terms from packaging terms. The discussion does not identify separate terms or corresponding source for the selected opaque D80 firmware files; binary redistribution remains unresolved. No vendor contact was made or firmware license inferred from a third-party repository.

### Capability evidence and limits

- Physical microSD boot and SSH succeeded on V1.12M. `/`, `/config` and `/boot/efi` are mounted from microSD in **Radxa OS**; the future Buildroot partition layout is not tested by this result.
- `wlan0` connected on 5 GHz, channel 100, 80 MHz width. `iw list` advertises AP and AP/VLAN modes. A hostapd AP, regulatory/channel behavior and Bluetooth coexistence have not been tested.
- `bluetoothctl show` reports a powered controller. Pairing, the dongle Bluetooth profiles and reconnection have not been tested.
- On the selected **Linux 6.12.114** baseline, a private diagnostic initramfs (2026-10-23, two boots) passed radio setup, bounded HCI Reset and live hci0 attachment, then failed BlueZ 5.79 adapter registration: `getsockopt(L2CAP_OPTIONS)` returned `EOPNOTSUPP` with `CONFIG_BT_LE=n`. No adapter or pairing window was reached. Explicit `ControllerMode=bredr` is an untested hypothesis for [task #12](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/12); see the [mainline Bluetooth diagnostic](../../aa_wireless_dongle/board/radxa/zero3w/checks/bluetooth-test.md).
- `/sys/class/udc/fcc00000.usb` exists. Accessory gadget binding, enumeration, accessory-start uevents and Android Auto have not been tested.
- The owner powered the board from a USB outlet for this diagnostic session. The exact supply/port/cable and car USB acceptance were not recorded or measured.

Reproduce the version inventory with `uname -a`, `dpkg-query -W`, the module/sysfs paths above, `iw dev`, `iw list`, `bluetoothctl show` and `lsblk`. Use a privileged kernel-log read to identify loaded firmware, then `sha256sum` on those files. Do not publish Wi-Fi credentials, SSIDs or Bluetooth/MAC addresses with the evidence.

### Radio pins and Bluetooth startup observed on the board

A read-only follow-up decoded the active `/proc/device-tree` GPIO phandles rather than comparing numeric phandle IDs between trees. The following properties match the audited vendor AIC DT at `fd366906451692033f1ba273e77e7e2f936c78db`; this does not establish that the entire running tree came from that commit.

| Function | Active DT property and pin |
| --- | --- |
| Wi-Fi power | `wireless-wlan/WIFI,poweren_gpio`: GPIO0 PC0, active high; `sdio-pwrseq/reset-gpios`: same pin, active low |
| Bluetooth reset | `wireless-bluetooth/BT,reset_gpio`: GPIO0 PC1, active high |
| Bluetooth wake / host interrupt | `BT,wake_gpio`: GPIO0 PB4; `BT,wake_host_irq`: GPIO0 PB3; both active high |
| UART RTS | `uart_rts_gpios`: GPIO2 PB5, active low; pinctrl states `uart1m0-rtsn` and `uart1-gpios` |
| Antenna selection | `board-antenna`: GPIO3 PD3, active low; fixed regulator, boot-on and always-on |

These are recorded vendor property meanings, not a proposed mapping to generic upstream bindings. In particular, do not translate `BT,reset_gpio` directly to an upstream reset descriptor without verifying the power/reset sequence and polarity semantics.

The installed `/usr/lib/rsetup/mod/aic8800.sh` invokes `bt_test -s uart 1500000 /dev/ttyS1` with a two-second timeout and checks for `hci recv thread ready (nil)`. Its systemd reset service runs before `hciattach -s 1500000 /dev/ttyS1 any 1500000 flow nosleep`. `bt_test` belongs to `aicrf-test` `4.0+git20241119.06da8476-1`, source package `aic8800`; the installed executable's SHA-256 is `c60aeeccaf382586ab4183206d4f5b15272c4e92d06134190761b9ddd82fec15`. This adds a userspace initialization requirement beyond compiling `aic8800_btlpm`. The follow-up did not rerun reset, reattach the UART or interrupt the working connection.

The pinned [`bt_test.c`](https://github.com/radxa-pkg/aic8800/blob/fc7cbdd1791416c2457fa27a59e508bf325c9c3f/src/tools/aicrf_test/bt_test.c) opens the UART, sets hardware flow control, sends HCI Reset (`01 03 0c 00`) and reads a response before printing the readiness marker. Its server path also binds TCP port 5001 to `INADDR_ANY`. Reproduce the bounded reset behavior during runtime integration; do not install the factory test server as a persistent dongle service. UART response handling, GPIO control and firmware readiness still need validating together on the target kernel.

The follow-up adds a standalone, MIT-licensed feasibility helper under `board/radxa/zero3w/checks/aic-hci-reset.c`, without copying the factory server or adding a runtime package. It uses nonblocking 1.5 Mbaud/8N1/RTS-CTS UART I/O with software flow control disabled. One monotonic two-second deadline covers command transmission and all event reads. Success requires a complete H4 Command Complete event for opcode `0x0c03` with zero status; unrelated events and successful Command Status are not success. It bounds event payloads to the HCI one-byte length, rejects other H4 packet types, and restores TTY settings/exclusivity on handled exits. It refuses an exclusive TTY or an already attached non-N_TTY line discipline; startup must also stop other raw-TTY users.

Protocol references are the [Bluetooth HCI specification](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-60/out/en/host-controller-interface/host-controller-interface-functional-specification.html), the recorded AIC reset bytes and [Microchip's HCI Reset command/event reference](https://onlinedocs.microchip.com/g/GUID-F06E537E-7E82-46B0-A4FA-15A47750A7D6-en-US-1/GUID-FC88356A-C981-4EF7-8195-A7C0730F1EE2.html). Serial configuration and exclusive-mode behavior follow Linux [termios](https://man7.org/linux/man-pages/man3/termios.3.html) and [TIOCEXCL](https://man7.org/linux/man-pages/man2/TIOCEXCL.2const.html). The helper deliberately does not infer GPIO semantics from protocol success.

All 13 host pseudo-terminal tests pass, verifying actual UART configuration/transmission, fragmented and maximum-length events, unrelated opcodes/events, controller rejection, malformed/partial frames, fixed deadline under continuous unrelated traffic, termios/exclusivity restoration, software flow-control disabling, and rejection of regular files/exclusive ports. The flow-control test first reproduced retained IXOFF/IXANY flags; explicitly clearing them fixes it. Host compilation uses `-Wall -Wextra -Werror -Wconversion -Wshadow` and GCC static analysis passes; the same warning flags pass with Bootlin GCC 14.3.0 for ARM64. That initial check established host simulation and target compilation only; no files were installed on the board in that slice. The physical follow-up is recorded below.

### Physical UART reset follow-up: 2026-10-21

After the owner restored the reference card to the board and booted Radxa OS, read-only inspection found `hciattach` and BlueZ active, `hci0` powered, UART1 at 1.5 Mbaud/RTS-CTS with no software flow control, and line discipline **15 (N_HCI)**. The installed AIC reset service had nevertheless failed with status 2 after timing out. These are separate observations: a registered UART service is not evidence that its preceding reset passed.

The **same journal monotonic clock** records reset-service start at 9.114 s, its reset-command log at 9.556 s, BT patch loading at 9.591 s, extended patch at 9.637 s and MAC firmware at 9.685 s. The reset times out at 11.377 s; hciattach starts at 11.519 s. The installed reset unit has no dependency on AIC firmware readiness. The reset attempt overlaps firmware loading; this supports a readiness-ordering hypothesis, not proof that it is the sole timeout cause or a measurement of UART wire timing. Raw dmesg timestamps differed from journal monotonic timestamps on this kernel and were not mixed into this comparison.

The vendor `bt_default` rfkill instance was software-blocked while `hci0` was unblocked and powered. GPIO0 PC1 (`bt_default_reset`) was output low, PB4 (`bt_default_wake`) input high, PB3 (`bt_default_wake_host`) input low/IRQ; Wi-Fi PC0 was output high and antenna GPIO3 PD3 output low. UART TX/RX/CTS belonged to the serial controller and RTS was in the vendor Bluetooth node's UART function. The audited [`rfkill-bt.c`](https://github.com/radxa/kernel/blob/fd366906451692033f1ba273e77e7e2f936c78db/net/rfkill/rfkill-bt.c) contains additional GPIO/RTS transitions when that rfkill instance is unblocked. Do not infer that those transitions are required for this AIC path, or drive PC1 high solely from the vendor DT property's name.

With **zero connected Bluetooth devices**, the ARM64 helper (SHA-256 `d5dcef4576a312f3044965115063ae111224f400298de0c8f2330339acb625c7`) was copied to a temporary path and tested:

1. While N_HCI was attached, it returned `Device or resource busy`; line discipline remained 15 and the controller stayed powered.
2. A recovery timer was armed, then BlueZ and hciattach were stopped. With UART line discipline 0 (N_TTY), the helper returned **`HCI Reset complete` in approximately 5 ms** and left the UART in N_TTY.
3. hciattach and BlueZ were restarted. Both were active, the controller was powered and N_HCI was restored. The selected GPIO directions/levels were identical before and after. The recovery timer was cancelled and removed, and both temporary test files were deleted.

Local evidence is `/tmp/radxa-build-check/hci-hardware-check.log`. No boot, DT, firmware, driver or persistent service configuration was changed. This proves one reset/reattach cycle on the **Radxa OS 6.1.84 reference**, not upstream 6.12.114 or Buildroot operation, pairing, AP coexistence or repeated cold-start reliability.

The next runtime contract must establish AIC firmware readiness **before** the bounded UART reset, proceed to hciattach only on reset success, and start BlueZ after UART attachment. Source inspection at the pinned AIC commit shows `rwnx_mod_init()` calling `aicbsp_set_subsys(AIC_WIFI, AIC_PWR_ON)` before registering the Wi-Fi driver, with the BSP downloading Bluetooth patches as well. The reference uses `aic8800_bsp` and `aic8800_fdrv`; `aic8800_btlpm` was not loaded. Treat Wi-Fi initialization as part of the readiness investigation; do not invent a fixed sleep or reuse the vendor reset unit's unconditional handoff after failure. Mainline GPIO/pin defaults and a concrete readiness gate still need target integration and cold-start verification.

### Firmware-readiness predicate: 2026-10-21

The readiness investigation re-downloaded the exact `fc7cbdd1791416c2457fa27a59e508bf325c9c3f`
AIC archive, matched SHA-256 `cae09dc427fc6c4a7a1887b44612c8a30b39596fe04aeaaec66b8de6581eaa06`
and applied the official SDIO Debian patch series. The following source chain
provides a concrete **load-ordering predicate**, scoped to this D80 candidate:

1. [`rwnx_mod_init()`](https://github.com/radxa-pkg/aic8800/blob/fc7cbdd1791416c2457fa27a59e508bf325c9c3f/src/SDIO/driver_fw/driver/aic8800/aic8800_fdrv/rwnx_main.c)
   calls `aicbsp_set_subsys(AIC_WIFI, AIC_PWR_ON)` before host-interface registration.
   It then waits up to 9,000 ms for `hostif_register_done`, returning `-ENODEV`
   on completion timeout or a reported host-interface failure.
2. [`aicbsp_set_subsys()`](https://github.com/radxa-pkg/aic8800/blob/fc7cbdd1791416c2457fa27a59e508bf325c9c3f/src/SDIO/driver_fw/driver/aic8800/aic8800_bsp/aicsdio.c)
   holds the power mutex while initializing SDIO and calling `aicbsp_driver_fw_init()`.
   It updates the powered-subsystem map only after success. A previously powered
   subsystem skips repeat loading. The fallback that delegates loading to fdrv
   is not the recognized D80 `c8a1:0082` / `c8a1:0182` path.
3. [`aicbsp_driver_fw_init()`](https://github.com/radxa-pkg/aic8800/blob/fc7cbdd1791416c2457fa27a59e508bf325c9c3f/src/SDIO/driver_fw/driver/aic8800/aic8800_bsp/aic_bsp_driver.c)
   sets `btenable = 1` for D80. With the audited `CONFIG_MCU_MESSAGE=n` and
   normal work mode, it synchronously runs `aicbt_init()` before `aicwifi_init()`.
   The BT path uploads ADID, patch and extended patch data, then writes the
   patch table including power-on entries. Reported failures propagate back
   through these calls. Preserve these build/mode assumptions at integration.
4. Linux 6.12.114 [`do_init_module()` and `show_initstate()`](https://github.com/gregkh/linux/blob/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e/kernel/module/main.c)
   establish `/sys/module/<name>/initstate=live` after a nonnegative module-init
   return. Directory presence alone can precede initialization. Likewise, a
   netdev can become visible before the remaining init code completes.

The host-interface completion is not a complete Wi-Fi-health guarantee:
[`aicwf_sdio_probe()`](https://github.com/radxa-pkg/aic8800/blob/fc7cbdd1791416c2457fa27a59e508bf325c9c3f/src/SDIO/driver_fw/driver/aic8800/aic8800_fdrv/aicwf_sdio.c)
ignores the return from `aicwf_rwnx_sdio_platform_init()` and calls
`aicwf_hostif_ready()` before host-wake IRQ registration. Consequently, use
both successful module initialization and the expected bound network device.
The driver sets the netdev parent to the SDIO device through `SET_NETDEV_DEV`,
`set_wiphy_dev()` and [`wiphy_dev()`](https://github.com/gregkh/linux/blob/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e/include/net/cfg80211.h).

Board-local `checks/aic-firmware-ready.sh` implements a read-only, one-shot
candidate predicate: both BSP/fdrv modules must be `live`, BSP testmode and
current cpmode must be normal work mode (0), and the selected interface must
belong to `c8a1:0082`, bound to SDIO driver `aicwf_sdio`. Any exposed driver
module-owner link must point to `aic8800_fdrv`; the vendor 6.1 kernel/SDK
does not expose that link (see the physical follow-up below).
Missing evidence or incomplete initialization returns failure. It does not
load/unload modules, wait a fixed sleep, touch GPIO/UART or change radio state.
The future startup owner must load the pinned modules synchronously, require
this predicate, require successful bounded HCI Reset, then attach HCI and
start BlueZ. Any failed stage stops that sequence.

This is an ordering check, not firmware attestation or proof that Bluetooth
responds. It assumes the audited source/build settings, no firmware-mode changes
after loading, and serialized startup without concurrent power-off, removal or
reload. It is not a generic predicate for another AIC SDK, built-in drivers,
resume or recovery. Keep the HCI Reset response as the next independent check;
do not use `live`, a log line or `wlan0` alone as Bluetooth readiness.

Verification: 17 host tests exercise the real shell script with isolated
sysfs-shaped files/symlinks, including early netdev visibility while either
module is `coming`, missing evidence, removal state, wrong identity/binding,
test modes and interface-name validation. The positive test failed before the
script existed; a mutation removing module-init checks was rejected by the
early-interface test. Shell syntax and whitespace checks passed.
The initial source-only session could not inspect the recorded SSH endpoint
noninteractively; the subsequent physical follow-up is recorded below.
Runtime packaging and mainline cold-start validation
remain pending; this does not complete #5 or resolve firmware terms.

### Physical readiness-predicate follow-up: 2026-10-21

After the owner confirmed SSH access, the exact tracked shell script was copied
to a private temporary directory on the unchanged Radxa OS reference, Linux
`6.1.84-10-rk2410-nocsf`, and invoked as root. The initial checks exposed two
incorrect fixture assumptions:

- The BSP mode attribute is under `aic-bsp/aicbsp_info/cpmode`, not directly
  under `aic-bsp`. The pinned AIC `aicbsp_attribute_group.name` is
  `aicbsp_info`; the real attribute reported normal work mode (0). Correcting
  the fixture reproduced the failure before the shell path was fixed.
- The SDIO driver has no `module` symlink on this reference. The pinned SDK
  leaves `sdio_driver.drv.owner` unset, and the audited vendor
  [`sdio_register_driver()`](https://github.com/radxa/kernel/blob/fd366906451692033f1ba273e77e7e2f936c78db/drivers/mmc/core/sdio_bus.c)
  does not supply an owner. In contrast, Linux 6.12.114's
  [`__sdio_register_driver()`](https://github.com/gregkh/linux/blob/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e/drivers/mmc/core/sdio_bus.c)
  sets the owner passed by its `THIS_MODULE` macro. The predicate now permits
  an absent link and rejects incorrect or dangling links when exposed. It
  still requires both modules to be `live` and the correct D80 driver binding;
  source provenance remains a precondition, not something this predicate proves.

After these corrections, all **17** host tests passed. Fixtures cover the real
grouped mode path, missing mode evidence even if an ungrouped attribute exists,
and absent/matching/incorrect/dangling owner links. Positive tests failed before
each fix. The corrected script had identical host/board SHA-256
`2e25e494c5d7007c8e93a0c79c745f5816a5a3c7020725033c949eb6272a5e24`.
The physical result was `AIC firmware load ordering ready: wlan0`, exit **0**;
an explicit nonexistent interface was rejected with exit **1**. Both modules
were `live`, BSP testmode/current mode were 0, and `wlan0` was backed by SDIO
`c8a1:0082` using `aicwf_sdio`.

Bluetooth and `rsetup-hciattach@ttyS1` remained active. The temporary script and
directory were removed. No module, GPIO, UART, service, firmware, DT or boot
configuration was changed; no credentials or private endpoint were saved in Git.
This verifies one post-boot status snapshot on the vendor reference. It does
not establish startup timing, reset/attach ordering, mainline operation,
pairing, AP coexistence or cold-start acceptance. Keep #5 open.

### Guarded reference-OS cold-start experiment: 2026-10-21

The owner performed two physical power removals/reconnections, each after an
orderly shutdown and with at least ten seconds without power. Both boots used
the unchanged Radxa OS/Linux 6.1.84 reference. Before interruption there were
zero connected Bluetooth devices, hci0 was powered, and Wi-Fi autoconnect plus
SSH were enabled. No Wi-Fi driver was unloaded or network configuration changed.

Board-local `checks/make-startup-test.sh` generates a diagnostic bundle, not an
installer or shipping startup sequence. Three uniquely named systemd drop-ins
replaced the vendor reset command with synchronous module loading, the
readiness predicate and the bounded ARM64 HCI Reset helper. Attachment requires
successful reset with `Requires=` plus `After=`; BlueZ similarly requires and
follows attachment. A boot-enabled rollback timer removes those drop-ins and
restores reference hciattach/BlueZ. Vendor unit files are preserved. Effective
units passed `systemd-analyze verify --man=no` on systemd 252.38. Its unrelated,
nonfatal warning about the reference's world-writable `rkaiq_3A.service` remains.

The first cold boot exposed an incorrect experiment assumption: `modprobe
aic8800_fdrv` failed at 9.850 s and again at 11.046 s. Neither hciattach nor
BlueZ executed, demonstrating that the dependency failure blocks later stages.
Radxa's Debian package indexes `aic8800_fdrv_sdio.ko.xz` and
`aic8800_bsp_sdio.ko.xz`; `modinfo -F name` reports the unsuffixed internal names
used by sysfs. `modprobe --show-depends aic8800_fdrv_sdio` resolves both packaged
files, and loading that name returns 0. This suffix belongs to the reference
package and is not a Buildroot module-naming decision.

The first automatic rollback started at 193.547 s (the initial timer used
systemd's default one-minute accuracy). It removed the test drop-ins, but an
unnecessary `reset-failed bluetooth.service` aborted restoration because the
never-started BlueZ unit was unloaded after daemon-reload. The reference was
restored manually before proceeding. The corrected rollback omits that
operation, and the timer now requests one-second accuracy at boot +180 s.
Four host regression tests check restoration of a never-started service,
failure propagation without a success marker, reproduction of the old failure
and refusal to overwrite an existing generated bundle. Corrected rollback also
passed on the board before rearming for the second cold start.

The second cold boot used the corrected package name and recovery script.
The same boot's journal monotonic clock and systemd monotonic properties record:

| Event | Seconds since boot |
| --- | ---: |
| Firmware load-ordering predicate succeeded | 10.677309 |
| Matching successful HCI Reset response logged | 10.721554 |
| Reset helper process exited with status 0 | 10.742534 |
| Reset oneshot became active | 10.743369 |
| hciattach became active | 11.155883 |
| BlueZ became active | 11.897063 |

All three services reported success; hci0 was powered and SSH returned over
Wi-Fi. Kernel firmware filename logging appeared at 8.968–9.270 s on the same
journal monotonic clock; these are log times, not measured upload completion.
The corrected automatic rollback started at **180.655468 s** and completed at
**183.086895 s**, with its completion marker present. hciattach/BlueZ were
active, hci0 powered and the UART line discipline was **15 (N_HCI)** afterward.
The disabled timer/service, owned drop-ins, helpers and experiment directory
were then removed; effective unit `DropInPaths` were empty and Wi-Fi/SSH remained
active. No kernel, DT, firmware or bootloader files were changed.

These are one successful cold-start sequence and one rejected sequence on the
vendor reference, not Buildroot/mainline validation,
UART wire timing, pairing/AP coexistence or the approved ten-start acceptance.
Task #5 and firmware terms remain unresolved.

## Source findings

This table preserves the initial audit references and the questions at that
stage. The selected baseline above and the subsequent build results take
precedence over these historical candidates and remaining-verification entries.

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

Recorded firmware-licensing state on 2026-10-23: the maintainer clarification in [radxa-pkg/aic8800#54](https://github.com/radxa-pkg/aic8800/issues/54) covers the GPL-2 driver source and GPL-3 packaging metadata only. The request for the six selected D80 files' redistribution terms, notices and source obligations, [radxa-pkg/aic8800#109](https://github.com/radxa-pkg/aic8800/issues/109), is open with no response. No redistribution permission is inferred. Resolving it, or explicitly changing the firmware selection, is part of task #11's distribution-rights criterion; no release image may include these files before then.

The checked-out Armbian firmware package sets `ARMBIAN_FIRMWARE_REDISTRIBUTE = NO` when firmware is selected. Its AP6212 option is therefore not sufficient evidence for including those files in this project's downloadable release image. If an older radio is received, identify an appropriate, documented firmware source before packaging it.

## Alternatives considered

### Mainline bootloader/kernel plus the appropriate radio package

Selected engineering route following the full linking, boot-chain and DT checks recorded below. Upstream ZERO 3 boot configuration and DT exist, and board-local configuration fits the current external tree. Physical radio and accessory operation remain explicit integration checks; source presence does not guarantee operation.

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

The AIC patch paths above are relative to `aa_wireless_dongle/board/radxa/zero3w/`. These are preparation patches for the pinned candidates. Since task #7, `configs/radxa-zero3w_defconfig` applies the Linux patches; no defconfig consumes the AIC patches yet. Future integration must apply the existing two shared accessory patches **before** the board-local Linux patches (HID correction, DT variant, then GPIO defaults below), and the official AIC Debian patch series **before** the two scoped AIC patches. Give Radxa its own Linux download hash; do not select the Pi Linux hash or apply the Radxa-only patches to the retained Pi pin.

To reproduce on fresh, verified source extractions, set `RADXA_LINUX_SRC`, `RADXA_AIC_SRC`, `RADXA_OUT` and `RADXA_REPO` to absolute paths. `RADXA_AIC_SRC` is the archive root containing `src/` and `debian/`. Host tools must include LLVM/Clang, make, flex, bison and bc.

```sh
set -eu
for patch in "$RADXA_REPO"/aa_wireless_dongle/patches/linux/*.patch; do
    git -C "$RADXA_LINUX_SRC" apply "$patch"
done
for patch in "$RADXA_REPO"/aa_wireless_dongle/board/radxa/zero3w/patches/linux/*.patch; do
    git -C "$RADXA_LINUX_SRC" apply "$patch"
done
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

All five resulting files were inspected as ELF 64-bit ARM aarch64 objects. No compiler checks were disabled; existing nonfatal SDK warnings remain. The existing proxy socket/diagnostics regression test passed with local socket access enabled. This initial check verified object compilation only; the full link follow-up is recorded below. Build logs were kept locally under `/tmp/radxa-build-check/` (`compile.log`, `compile-after-hid.log`, `compile-after-aic.log`, `compile-after-prototypes.log`); these temporary files are not release artifacts.

### Full kernel and module linking

The follow-up completed `olddefconfig Image modules rockchip/rk3566-radxa-zero-3w.dtb` using the same source, patch order, ARM64 configuration and LLVM 23.1.3. Building the complete kernel supplied `Module.symvers`; the external AIC `modules` target then passed MODPOST and linked all three `.ko` files. No undefined-symbol errors were downgraded or compiler checks disabled. The SDK still emits existing nonfatal warnings. Commands are preserved in the board-local [compatibility checks](../../aa_wireless_dongle/board/radxa/zero3w/checks/README.md).

| Linked ARM64 module | Recorded dependencies |
| --- | --- |
| `libcomposite.ko` | None listed |
| `usb_f_accessory.ko` | `libcomposite` |
| `aic8800_bsp.ko` | None listed |
| `aic8800_btlpm.ko` | `rfkill`, `aic8800_bsp` |
| `aic8800_fdrv.ko` | `cfg80211`, `aic8800_bsp` |

All five modules were inspected as ARM aarch64 ELF files with identical vermagic `6.12.114 SMP preempt mod_unload aarch64`. The kernel `Image` was identified as an ARM64 boot executable, and the upstream ZERO 3W DT compiled to a 54,587-byte DTB. The resolved kernel `.config` SHA-256 was `9fed7f3914a9a2af6a44e9dae3e1ed9c879c531ba436f78da0a8f66ad1908535`. Logs: `/tmp/radxa-build-check/full-kernel-link.log` and `full-aic-link.log`; kernel output: `buildroot/output/radxa-platform-check/linux` (ignored build artifacts).

This establishes source compilation and symbol compatibility, not module loading or radio/accessory operation on the board. The generic upstream DT is a reference and still lacks the recorded AIC antenna/runtime integration; it is not a verified V1.12M device tree. A complete Buildroot image and physical verification remain pending.

### V1.12M AIC device-tree preparation

Board-local Linux patch `0004-Add-V1.12M-AIC8800D80-device-tree.patch` adds a separate `rk3566-radxa-zero-3w-aic8800d80.dtb` target on Linux 6.12.114. It inherits the upstream ZERO 3W tree, disables the unpopulated eMMC controller, adds GPIO3 PD3 antenna control with the standard fixed-regulator active-low default, and matches the audited AIC SDIO sample phase (180 degrees), pull-ups and drive strength (12). It removes the inherited RK817 external-clock request, which is absent from the working vendor AIC reference. The upstream 100 ms power-on and 5,000,000 us power-off delays remain conservative experiment settings; their suitability is not hardware-verified.

The source uses the pinned kernel's [fixed-regulator binding](https://github.com/gregkh/linux/blob/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e/Documentation/devicetree/bindings/regulator/fixed-regulator.yaml), [MMC power-sequence binding](https://github.com/gregkh/linux/blob/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e/Documentation/devicetree/bindings/mmc/mmc-pwrseq-simple.yaml) and [Rockchip MMC binding](https://github.com/gregkh/linux/blob/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e/Documentation/devicetree/bindings/mmc/rockchip-dw-mshc.yaml), rather than copying unsupported vendor platform nodes or `enable-active-low`. Inherited UART1 hardware flow control and USB OTG behavior remain; Bluetooth reset/wake control is not invented in this patch.

The new target compiled without DTC diagnostics. Compiled-tree checks using libfdt verified controller aliases/status, the SDIO power-sequence phandle and GPIO polarity, all six SDIO pinmux/drive settings, antenna GPIO/pinctrl/polarity, the inherited delays, UART flow control and OTG mode. The generic ZERO 3W DTB remained byte-identical to its recorded hash. The experimental DTB is 55,029 bytes, SHA-256 `39deb5067daa1eea5c638f93aadbd82ba17d01169a0f2632642dd6e952722660`; local evidence is `/tmp/radxa-build-check/aic-dtb-build.log` and `check-aic-dtb.py`. Patch application and reverse checks also passed.

This is a compiled source candidate, not a complete AIC runtime or full schema/hardware validation. Since task #7, `configs/radxa-zero3w_defconfig` builds it as the board DT. Bluetooth GPIO/reset/UART initialization, a Buildroot target integration, firmware terms and physical boot/radio/accessory checks remain pending.

### Mainline GPIO ownership and power-sequence preparation: 2026-10-21

Read-only inspection after the reference cold-start experiment again found PC1
output low, PB3 input low/IRQ, PB4 input high, PC0 output high and antenna PD3
output low. UART RX/TX/CTS were owned by the serial controller; the vendor
Bluetooth node owned RTS in its UART function. Only BSP/fdrv were loaded, not
`aic8800_btlpm`. No pin, driver or service state was changed by this inspection.

The vendor [`rfkill_rk_probe()`](https://github.com/radxa/kernel/blob/fd366906451692033f1ba273e77e7e2f936c78db/net/rfkill/rfkill-bt.c)
initializes PC1 to `!enable` (physical low for the recorded active-high vendor
property) and marks its rfkill instance blocked. Its separate unblock path
drives reset/wake and temporarily switches RTS to GPIO; the powered reference
does not exercise that path. The pinned AIC BSP's normal D80 path loads BT
firmware through SDIO, with `AICBT_LPM_ENABLE_DEFAULT=0`. With
`CONFIG_PLATFORM_ROCKCHIP=n`, `CONFIG_PLATFORM_ROCKCHIP2=n` and
`CONFIG_GPIO_WAKEUP=n`, it does not provide the vendor GPIO power/wake calls.
Thus mainline must describe the board's pin state independently of that rfkill
driver; compiling `aic8800_btlpm` is not a substitute for the observed setup.

Patch `0005-Set-AIC-Bluetooth-GPIO-defaults.patch`, applied after `0004`, adds
three standard GPIO hogs to the AIC-only DT. GPIO0's default pinctrl state uses
dedicated groups with PC1 pulled down and PB3/PB4 pulled up, matching the live
reference pinconf. Schmitt input is enabled for these GPIOs and all four UART
signals. UART RX/TX retain pull-up; RTS/CTS retain disabled bias. GPIO hogs
acquire their lines when the GPIO controller probes, per the pinned
[`gpio.txt` binding](https://github.com/gregkh/linux/blob/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e/Documentation/devicetree/bindings/gpio/gpio.txt)
and [`gpiolib-of.c`](https://github.com/gregkh/linux/blob/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e/drivers/gpio/gpiolib-of.c).

| Signal | Mainline candidate owner and behavior |
| --- | --- |
| GPIO0 PC0, Wi-Fi power | Existing `mmc-pwrseq-simple`; no hog or second owner |
| GPIO0 PC1, vendor BT control | GPIO hog, physical output low; no pulse requested |
| GPIO0 PB3, vendor BT host-wake | GPIO hog, input; no IRQ/wakeup service provided |
| GPIO0 PB4, vendor BT wake | GPIO hog, input; its observed high value is not driven |
| GPIO2 PB3/PB4/PB5/PB6 | UART1 RX/TX/RTS/CTS, function 2; serial driver owns RTS |
| GPIO3 PD3, antenna | Existing active-low, always-on fixed regulator |

Drive strength needs special handling. The reference pinconf labels report
4/12 mA, but its RK3568 readback uses the generic two-bit lookup; those labels
are not the levels accepted by the RK3568 setter. Read-only regmap inspection
resolved the actual eight-bit fields:

| Register block and offset | Read value | Relevant pin fields | Requested level |
| --- | --- | --- | --- |
| PMUGRF `0x0084`, `0x0088`, `0x0090` | Each `0x00000101` | PB3/PB4/PC1 each `0x01` | 0 |
| GRF `0x0254` | `0x00000f03` | UART RX high byte `0x0f` | 3 |
| GRF `0x0258` | `0x00000f0f` | UART TX/RTS each `0x0f` | 3 |
| GRF `0x025c` | `0x00000303` | UART CTS low byte `0x03` | 1 |

The pinned mainline [`rockchip_set_drive_perpin()`](https://github.com/gregkh/linux/blob/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e/drivers/pinctrl/pinctrl-rockchip.c)
encodes RK3568 levels as `(1 << (level + 1)) - 1` with eight bits per pin;
the patch uses levels 0/3/1 to reproduce those fields, not the diagnostic mA
labels. The displayed pull argument `(1 ohms)` is also not a measured resistor
value. Slew rate is reported enabled on the reference, but the pinned mainline
driver exposes no slew-rate setter; this patch makes no electrical equivalence
claim for that setting. Existing Wi-Fi/antenna pin configuration is retained.

The pinned [`mmc-pwrseq-simple`](https://github.com/gregkh/linux/blob/85d82e0d7c2dfd3e75d34f35b7ebbf41f45c9c4e/drivers/mmc/core/pwrseq_simple.c)
asserts logical reset 1 before power-on, giving physical PC0 low for its
active-low descriptor, then deasserts to physical high after power-on. The
inherited 100 ms post-power-on and 5,000,000 us power-off parameters are retained;
the latter feeds a 5–10 s `usleep_range`, not a measured board requirement.
The candidate retains `serial1` at UART1 and has no Bluetooth serdev child or
invented upstream compatible. Input hogs reserve PB3/PB4: revisit ownership
before enabling GPIO wake, btlpm, suspend/resume or another GPIO consumer.

Verification used the re-downloaded, hash-verified Linux 6.12.114 source and
the existing LLVM ARM64 output/configuration. GPIO/pinctrl, MMC pwrseq,
Rockchip MMC/UART and fixed-regulator drivers are enabled in that configuration.
Both DT targets compile without DTC diagnostics. Six `pylibfdt` tests inspect
the compiled directions/polarity, pinctrl groups/pulls/drive levels/Schmitt,
sole PC0 owner, UART flow-control pins/alias, antenna/SDIO settings and unchanged
generic DT. The
Bluetooth-direction test first failed on missing hogs; an active-low mutation
of PC1 was also rejected. Pull/drive checks failed before the measured settings
were added; a CTS level-3 mutation was rejected after the fix. Patch
reverse/application checks pass.

The AIC DTB is **56,025 bytes**, SHA-256
`3bd46eb308d09a4fb62ca7ebe8a522a81de5d9953db094bbf99c106772ae956e`.
The generic DTB remains byte-identical, SHA-256
`eefcec9be8350d21e2f578bf9734279e4583779a87177411f4253feecc4b7d86`.
Full dt-schema validation was not run; the host lacks `dtschema`.
Buildroot `check-package` could not run on the host or in the existing build
container because both lack its `python-magic` dependency; no patch-metadata
lint pass is claimed.

This supplies deterministic requested states after driver probing, not proof
of glitch-free electrical behavior or acquisition order on hardware. It does
not establish that PC1 is physically required by the radio. A controlled boot
with the matching mainline kernel/DT must still validate GPIO acquisition,
SDIO power, UART reset/attachment and radio operation. No candidate kernel or
DT was installed on the reference card. Task #5 and firmware terms remain open.

### Boot-chain build and packing

The isolated `checks/bootchain_defconfig` uses the existing Buildroot 2026.02.3 pin, U-Boot 2026.01 (`radxa-zero-3-rk3566_defconfig`) and the existing rkbin commit `f43a462e7a1429a9d407ae52b4745033034a6cf9`. It enables mandatory download hashes and builds only the bootloader with Bootlin AArch64 glibc stable `2025.08-1`, GCC `14.3.0`. It is deliberately outside the external tree's shipping `configs/` directory.

| Input | SHA-256 |
| --- | --- |
| [u-boot-2026.01.tar.bz2](https://ftp.denx.de/pub/u-boot/u-boot-2026.01.tar.bz2) | `b60d5865cefdbc75da8da4156c56c458e00de75a49b80c1a2e58a96e30ad0d54` |
| rkbin `bin/rk35/rk3566_ddr_1056MHz_v1.23.bin` | `20e4bb076847bd019fcdeb7bdc15bd249890f07ecc76e9937101f22e50950982` |
| rkbin `bin/rk35/rk3568_bl31_v1.44.elf` | `65110f822fdbdd0163ce2dabc60591e7a8a0ffbc9471780e29eef0062f9ed7b6` |

The U-Boot archive matches `boot/uboot/uboot.hash`. The two blob hashes above identify files at the pinned rkbin source, not an independent signature. Buildroot additionally verifies its rkbin source archive and `LICENSE` hashes; the latter is `d2765124a2c24d71aba3cbc6cdd6975a5a297821264eb6c26378a4c16cd16e92`. Keep that notice with redistributed boot firmware. The RK3568 BL31 filename is shared by the RK3566 path; DDR remains the explicitly selected RK3566 binary. Building this combination does not establish DDR training or boot on the physical 1 GB board.

The `uboot` target completed successfully in the existing `aawg-buildroot` Docker environment. Both U-Boot and SPL were inspected as ARM aarch64 ELF executables. `images/u-boot-rockchip.bin` is 9,632,768 bytes, SHA-256 `9f98a8e8187f1c5666813684c4f471325c74e87104773e8b84bdaad5eb531fc6`. This identifies the local experiment output, not a reproducible release hash; U-Boot's build timestamp was not fixed. The build log is `/tmp/radxa-build-check/bootchain-buildroot.log`.

Packing verification decoded the Rockchip v2 header and checked its header/payload SHA-256 fields: the exact DDR input is at raw-image offset `0x800` and SPL at `0xf000`. Do not use the nested pre-`mkimage` offsets in `simple-bin.map` as final payload locations. The exact generated FIT is at `0x7f8000`; all six file-backed BL31 ELF load segments match its contents. `dumpimage -l` identifies the default ZERO 3W configuration, six ATF segments, U-Boot and both upstream 3W/3E bootloader DTs. Binman reports the optional `tee-os` blob absent; OP-TEE was not selected or validated. These offsets are within the bootloader file; raw SD placement and partition boundaries still belong to image integration.

The checked-in configuration matches the experiment's input. Buildroot's `check-package` processed its 21 lines without warnings (using an identical temporary `configs/*_defconfig` copy, because its parser intentionally ignores board-local defconfigs). The check produces no complete SD-card image and did not write to the owner's card or change the running Radxa OS.

### Diagnostic mainline boots: 2026-10-22

The owner booted the private 224 MiB diagnostic image containing the checked
U-Boot/kernel/AIC DT and a minimal static BusyBox initramfs. Its SHA-256 is
`7c6274d0d048d84760018a7f18424dc6db933d6cfb3c03be810adc336af74910`.
No external modules or radio firmware were included. All written image bytes
passed card readback verification before the physical test.

The owner confirmed three separate power applications, using a computer USB-A
port and a USB-A–USB-C cable to Radxa. The exact computer port/cable model and
power-removal durations were not measured; this is not car USB-power evidence.
Three distinct boot UUID directories were recovered from the FAT log partition,
mounted read-only after the card returned. Each contains `result.txt`,
`hardware.txt`, `dmesg.txt` and a 57,344-byte `live.dtb`. SHA-256-verified copies
and analysis are private ignored output under
`buildroot/output/radxa-boot-test-20261022-v3/evidence-20261022T094234Z/`.

| Boot UUID prefix | Last saved kernel timestamp | AIC SDIO IDs in snapshot |
| --- | --- | --- |
| `15fd25c3` | 1.010634 s | Not yet present |
| `2de0087f` | 1.645943 s | Both `c8a1:0082` and `c8a1:0182` |
| `8bc5185a` | 1.017161 s | Not yet present |

All three reach `/init` with Linux **6.12.114**, the V1.12M/AIC model and
`EXPECTED_KERNEL=1` / `CAPTURE_FINISHED=1`. MicroSD partitions are readable and
FAT logs persist. Live-DT checks confirm the selected GPIO hog directions and
polarity. Runtime GPIO ownership shows PC1 output low, PB3/PB4 input high,
PC0 reset physical high/deasserted and antenna PD3 physical low. PB3 differs
from the reference's input-low/IRQ observation: this experiment has no radio
driver/firmware and its hog provides no IRQ. Do not infer operating-radio
equivalence from these uninitialized levels.

UART1 appears at `fe650000.serial` / `ttyS1`, and `fcc00000.usb` is registered
under `/sys/class/udc/`. No modules are listed. The later snapshot records
SDR104 SDIO enumeration, successful phase tuning and both matching AIC SDIO
functions. The other two captures end while the host is still initializing;
their absence of SDIO entries is inconclusive. A later radio diagnostic must
wait for explicit enumeration/readiness and record timeout separately before
collecting the final snapshot.

No priority 0–3 kernel messages or panic/Oops/BUG/call-trace signatures appear
in the saved logs. Warnings concern unavailable ITS/LPIs, deprecated static GPIO
bases and disabled DMA for the console UART. The owner reported the LED turning
off after approximately five seconds. This is consistent with the init script's
intentional sync/unmount/poweroff after capture; it is not evidence of a crash.
The saved dmesg ends before the poweroff call, so completed shutdown and precise
power-on-to-off timing are not independently logged.

This establishes three brief diagnostic boots, not three acceptance cold starts,
SDIO reliability, radio operation or a complete Buildroot dongle. Boot-stage
serial banners were not captured. AP, Bluetooth HCI/reset/attachment/pairing,
USB accessory negotiation, sustained operation and car power remain untested
on mainline. The owner selected the verified previous-day full-card backup as
the recovery point; recovery state belongs in the dated
[boot-test handoff](../handoffs/2026-10-22-radxa-boot-test.md).

### Shipping kernel and boot-component build: 2026-10-23

Task [#7](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/7) adds `aa_wireless_dongle/configs/radxa-zero3w_defconfig`. It builds the selected kernel, the V1.12M AIC DT and the U-Boot/DDR/BL31 boot chain with the Bootlin AArch64 glibc stable toolchain and mandatory download hashes. It imports no Pi firmware, boot configuration, overlay, script or patch directory. It does not yet produce a microSD image or userspace (#8), and it does not package the AIC driver or firmware (#10, #11).

- **Kernel configuration:** upstream ARM64 `defconfig`, then `board/common/kernel.config`, then `board/radxa/zero3w/linux.fragment`. The fragment enables `BT_LE` and `BT_RFCOMM` explicitly, together with `BT`, `BT_HCIUART` and `BT_HCIUART_H4`; the mainline Bluetooth result above traced the adapter-registration failure to their absence. `BT_BNEP` stays disabled. The ARM64 defconfig builds `certs/extract-cert`, so the target selects host OpenSSL.
- **Patches and hashes:** the global patch directories are the shared `patches` followed by `board/radxa/zero3w/patches`, so Linux applies 0001–0005 in the order required above. `board/radxa/zero3w/patches/linux/linux.hash` pins `linux-6.12.114.tar.xz` to the kernel.org hash in [ARM64 compilation](#arm64-compilation-slice). Buildroot merges hash files across patch directories; the Pi `linux.hash` has no entry for this archive, and Pi targets never read the Radxa file. Buildroot's own `uboot.hash` and `rockchip-rkbin.hash` verify the U-Boot and rkbin archives, so no U-Boot hash file or configuration fragment is added; plain `radxa-zero-3-rk3566_defconfig` is the configuration that booted the board.
- **Compiler:** this is the first build of the patched kernel with GCC (Bootlin `14.3.0`, binutils `2.43.1`); the earlier link evidence used LLVM. It completed without source changes.

`make linux uboot` in the `aawg-buildroot` Docker environment produced:

| Output | Size (bytes) | SHA-256 |
| --- | --- | --- |
| Resolved kernel `.config` | — | `0dfc6b40e53c075fe86d513904f816089e100d865ac1fb1120a9f23848e3d503` |
| `images/Image` | 38,062,592 | `bd78de8fee4d31cbde32ab6e808378802007ccfe780b9a33b5ec9a0be099f135` |
| `images/rk3566-radxa-zero-3w-aic8800d80.dtb` | 56,025 | `3bd46eb308d09a4fb62ca7ebe8a522a81de5d9953db094bbf99c106772ae956e` |
| `images/u-boot-rockchip.bin` | 9,632,768 | `ce0ec7542f4eea97767184432029e84d2b33bf52ae0d0df159faa33a82d65bb3` |

These identify one local build, not reproducible release hashes. `tests/radxa_platform_build_test.py` checks the resolved kernel options, release `6.12.114`, the ARM64 `Image` header, the installed DT, both rkbin blob hashes, the DDR blob at offset `0x800` of `u-boot-rockchip.bin` and the defconfig's hash enforcement and Pi isolation. The five AIC property cases of `tests/radxa_aic_dtb_test.py` pass against this build's DTB using Buildroot's host Python and pylibfdt. The generic-DT case was not run because this target builds only the AIC DT. No Pi defconfig, Pi board file, `board/common` file or shared patch changed. Nothing from this build has been booted.

## Consequences and next evidence

- Use the selected engineering baseline and patch order above for subsequent integration. Task #5 is closed with firmware terms recorded as unresolved; task #11 owns their resolution and task #12 owns mainline BlueZ adapter registration and pairing. Dependent tasks retain their prerequisites.
- PCB/radio identification, source/link compatibility, packing, compiled-DT checks and the three boot-only mainline snapshots support the engineering choice. Radio operation and a complete Buildroot runtime remain unverified.
- Resolve the six firmware files' redistribution/source obligations before promoting this ADR to Accepted. Change the selected firmware/source baseline explicitly if the answer requires it.
- The complete Buildroot microSD layout/runtime, AP/Bluetooth coexistence, USB enumeration/negotiation, power and connection reliability remain physical acceptance checks in subsequent tasks.
- Do not publish a supported image or close hardware criteria based on this source investigation.

## Verification performed

On 2026-10-14, checked the existing Buildroot version and Pi source/patch configuration using task #5's commands and inspected the cited source snapshots. On 2026-10-21, collected the physical diagnostic evidence above, resolved the AIC package tag, matched all six loaded firmware/configuration files against that source, performed vendor/upstream accessory patch checks and reproduced/fixed the three ARM64 object-compilation failures above. The follow-up passed full kernel/module linking, built and inspected the isolated U-Boot/DDR/BL31 combination, and recorded the live radio pins and Bluetooth reset sequence. No complete Buildroot target image or car-operation result is established by these checks.

The source-selection documentation follow-up cross-checked the retained
Buildroot commit, board-local boot-chain configuration, existing patch filenames
and rkbin source/hash metadata. Fresh SHA-256 reads of the available Linux
archive, DDR/BL31 inputs and latest AIC DTB matched the values already recorded
above. No source, build configuration or board state changed in this follow-up;
the earlier build and physical evidence retains its original scope.
