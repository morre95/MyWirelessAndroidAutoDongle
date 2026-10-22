# Controlled mainline boot experiment — prepared 2026-10-22

This is a local feasibility experiment for
[issue #5](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5),
using the inputs selected in [ADR-0001](../../../../../docs/adr/0001-radxa-zero3w-platform.md).
It does not add a shipping Buildroot target or release image. The owner has
only the current microSD card; a UART adapter is not assumed available.
Preparation initially left the card untouched. The subsequent physical test
and recovery state are recorded in the [dated handoff](../../../../../docs/handoffs/2026-10-22-radxa-boot-test.md):
three boot snapshots reached Linux 6.12.114 diagnostic userspace. The image
intentionally requests poweroff immediately after saving logs; the three-minute
operator wait below is a conservative allowance, not a delay in the init script.

## Prepared artifact

The reviewed bundle is in ignored local output:
`buildroot/output/radxa-boot-test-20261022-v3/`.
`radxa-boot-test.img` is **224 MiB / 234,881,024 bytes**. Its exact checksum is
in the adjacent `SHA256SUMS` and `manifest.json`; verify that file before use.
The earlier directory without a suffix and `-v2` are superseded preparation outputs.

| Location | Contents |
| --- | --- |
| Raw offset 32 KiB | Previously checked U-Boot 2026.01 + DDR 1.23 / BL31 1.44 |
| Partition 1, offset 16 MiB, size 128 MiB | Bootable ext4: Linux 6.12.114 Image, AIC-only DT, extlinux configuration and diagnostic initramfs |
| Partition 2, offset 144 MiB, size 64 MiB | FAT32 `AICBOOTLOGS`, initially empty; stores one directory per boot UUID |

The initramfs contains static ARM64 BusyBox 1.37.0 and `boot-test-init.sh` as
PID 1, with console/null device nodes. It mounts proc/sysfs/devtmpfs/debugfs,
waits up to 60 polling attempts for the labeled MMC log partition, records
diagnostics, syncs/unmounts it and requests poweroff. If poweroff returns, it
waits without rebooting. It refuses direct execution outside PID 1 before any
mount or power operation. The remaining 16 MiB at the end of the image is unused.

No radio firmware, external modules, Wi-Fi credentials, SSH server, BlueZ,
hciattach, reset helper or dongle application is included. The test checks boot,
MMC/SDIO enumeration, GPIO/pinctrl state, UART presence and USB-controller
visibility. It cannot establish AP, pairing, HCI Reset or accessory negotiation.

`manifest.json` identifies the exact input Image/DT/bootloader, kernel config,
BusyBox, init script, generator and disk-image hashes. Input hashes deliberately
identify existing experiment builds, not reproducible release outputs. If they
change, review the rebuilt inputs and update this experiment explicitly.

## Local reproduction and checks

Existing checked kernel/boot-chain outputs are prerequisites; their commands
and source/archive hashes remain in the ADR and checks README. The builder
refuses changed input hashes, existing output directories, output outside
`buildroot/output`, symlinked output paths and dynamic/non-ARM64 BusyBox.
It formats only new regular image files, without root, loop mounts or access
to physical block devices. Failed partial output is kept for inspection; use
a new output directory when retrying.

BusyBox source is the unmodified 1.37.0 archive, verified against
`buildroot/package/busybox/busybox.hash`:
`3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4`.
The extracted source, full `.config` and build/config logs are preserved in
`buildroot/output/radxa-boot-test-prep/busybox-1.37.0/` and its parent. This is
a minimal diagnostic build, not the future Buildroot BusyBox package.

To reconstruct the minimal config in a fresh extraction, run `make allnoconfig`,
then enable these symbols and run `make oldconfig`:

```text
STATIC BUSYBOX SHOW_USAGE ASH ASH_ECHO ASH_PRINTF ASH_TEST SH_IS_ASH
FEATURE_SH_MATH CAT CP DMESG LS MKDIR MOUNT FEATURE_MOUNT_FLAGS UMOUNT
SLEEP SYNC UNAME POWEROFF BLKID FEATURE_BLKID_TYPE FEATURE_VOLUMEID_FAT
```

Build with the existing Bootlin GCC 14.3.0 toolchain. Set `CROSS_COMPILE` to
the absolute `radxa-bootchain-check/host/opt/ext-toolchain/bin/aarch64-linux-`
prefix and `CC` to its `aarch64-linux-gcc.br_real`. The `.br_real` invocation
avoids the old container wrapper's `/app` path. `ARCH=arm64`, `-j8` and the
`busybox` make target reproduce this isolated build. Keep source and config
with the private artifact; do not publish it as an approved release.

From the repository root, use a **new** output path:

```sh
python3 aa_wireless_dongle/board/radxa/zero3w/checks/make-boot-test.py \
  --busybox buildroot/output/radxa-boot-test-prep/busybox-1.37.0/busybox \
  --output buildroot/output/radxa-boot-test-rebuilt
RADXA_BOOT_TEST_DIR=buildroot/output/radxa-boot-test-rebuilt \
  python3 tests/radxa_boot_test_test.py
```

Host tools: Python 3.11+, `mkfs.ext4`, `mkfs.fat`, `sfdisk`, `debugfs`, GNU
`cpio`, `qemu-aarch64-static` and the existing kernel-output `usr/gen_init_cpio`.
Ten tests check refusal paths, actual disk layout/payloads, boot configuration,
archive contents and hashes. QEMU user emulation checks BusyBox applets and
shell syntax; it does not boot the kernel or emulate the Radxa board.
An intentionally disabled input-hash guard was rejected by its regression test.

## Physical test and recovery procedure

Preparation ends here. A later execution session must have the owner ready to
move the card between board and reader. With the single card, the diagnostic
temporarily replaces Radxa OS and all SSH access. Recovery is by the computer's
card reader, independent of the experimental kernel; there is no automatic
return to Radxa OS and no fallback boot entry.

1. While Radxa OS is still available, confirm no connected Bluetooth clients,
   record its working baseline and shut it down cleanly. Remove power before
   moving the card. Reidentify the reader/card by current model, serial and
   exact capacity; never reuse an old `/dev/sdX` name. Unmount its partitions.
2. Take a **fresh full-card backup** into a new private file. Verify compressed
   and decompressed hashes and the decompressed byte count before writing.
   The older `radxa-recovery/radxa-os-20261021-172921.img.zst` snapshot was
   reverified on 2026-10-22: both recorded SHA-256 values and all
   **31,266,439,168** decompressed bytes match its private metadata. Preserve
   that snapshot too; it is not a guarantee of today's exact card state.
3. Confirm the identified card's contents may be temporarily replaced. Inspect
   existing partition signatures, including any backup GPT at the physical
   end of the larger card. Remove stale signatures on that verified card as
   part of the write operation, then write the complete diagnostic image.
   Sync and hash-read back exactly **234,881,024** bytes against `SHA256SUMS`.
   Re-read the partition table and confirm the boot/log partitions. Device
   paths and write commands must be constructed from that session's inventory.
4. Safely eject, insert in the unpowered Radxa and use the known bench power
   connection. Expect no network connection. Allow at least three minutes
   before removing power and moving the card back to the reader. A hang can
   prevent orderly poweroff; preserve the resulting image/logs before any
   filesystem repair or retry.
5. Read the FAT log partition read-only. Save its UUID directory privately,
   together with the original manifest/image hash, power/cable description and
   observed elapsed time. Collect `result.txt`, `hardware.txt`, `dmesg.txt`
   and `live.dtb` when present. An empty partition is an **inconclusive boot**:
   without UART it cannot distinguish boot-ROM, DDR, U-Boot, kernel or logging
   failure. Stop and plan serial diagnosis before repeated blind writes.
6. Restore the **fresh pre-test full-card backup**, sync, then hash-read back
   its entire recorded raw byte count against its raw SHA-256. Safely eject
   and boot Radxa OS. Recheck SSH, Wi-Fi client, hciattach, powered hci0 and
   BlueZ. Keep both backup and test evidence until recovery is confirmed.

## Interpreting the result

`CAPTURE_FINISHED=1` only means the collection sequence reached its final marker;
individual diagnostics may still report errors. Require `EXPECTED_KERNEL=1`,
the V1.12M/AIC model in hardware/live-DT evidence and usable kernel logs before
claiming the kernel reached diagnostic userspace. Inspect SDIO enumeration,
MMC errors and GPIO ownership/directions against the ADR. U-Boot may fix up
the loaded DT, so compare relevant properties rather than requiring the live
DTB's full hash to equal the input DTB.

A successful result supplies one mainline boot snapshot. It does not establish
electrical timing, repeated cold starts, Wi-Fi/Bluetooth operation or Android
Auto. A subsequent radio experiment must separately add matching modules and
private reference firmware, preserve the firmware-ready → reset → hciattach →
BlueZ contract, and have its own failure/recovery procedure. Firmware terms
and issue #5's downstream prerequisites remain unresolved.

The disk offset follows the pinned [U-Boot Rockchip instructions](https://github.com/u-boot/u-boot/blob/v2026.01/doc/board/rockchip/rockchip.rst).
The explicit kernel/DT/initramfs paths follow its [extlinux/PXE parser documentation](https://github.com/u-boot/u-boot/blob/v2026.01/doc/usage/pxe.rst).
Static linking follows [BusyBox 1.37.0's configuration](https://github.com/mirror/busybox/blob/1_37_0/Config.in).
