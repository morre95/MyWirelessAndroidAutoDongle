# ZERO 3W source compatibility checks

These checks investigate the candidates in [ADR-0001](../../../../../docs/adr/0001-radxa-zero3w-platform.md).
They do not define a supported target or produce a complete dongle image.

## Boot chain

From the repository root, use the existing Docker build environment and pinned
Buildroot submodule:

```sh
docker compose run --rm --no-deps bash bash -ec '
    make O=output/radxa-bootchain-check \
        BR2_DEFCONFIG=/app/aa_wireless_dongle/board/radxa/zero3w/checks/bootchain_defconfig defconfig
    make O=output/radxa-bootchain-check uboot
    test -s output/radxa-bootchain-check/images/u-boot-rockchip.bin
'
```

Buildroot checks its pinned download hashes, builds the required host tools and
uses its Bootlin AArch64 glibc toolchain. The check selects U-Boot 2026.01's
`radxa-zero-3-rk3566` configuration with RK3566 DDR 1.23 and RK3568 BL31 1.44
from Buildroot's existing rkbin pin. The RK3568 BL31 filename is intentional;
the RK3566 build uses that shared firmware.

The output lives in the Compose `output` volume. It contains a bootloader only:
there is no Radxa kernel/root filesystem, partition layout, provisioning or
hardware boot result. Do not flash it as a complete SD-card image. See the ADR
for source revisions, blob hashes, verification results and remaining checks.

## Kernel and radio modules

Use the verified source archives, patch order and configuration in ADR-0001's
ARM64 compilation section. Finish the full kernel build before linking external
modules; `modules_prepare` alone does not supply the symbol table required by
MODPOST. With the same absolute source/output variables and LLVM toolchain:

```sh
make -C "$RADXA_LINUX_SRC" O="$RADXA_OUT" ARCH=arm64 LLVM=1 -j8 \
    olddefconfig Image modules rockchip/rk3566-radxa-zero-3w.dtb
make -C "$RADXA_LINUX_SRC" O="$RADXA_OUT" ARCH=arm64 LLVM=1 -j8 \
    M="$RADXA_AIC_SRC/src/SDIO/driver_fw/driver/aic8800" modules
```

Keep MODPOST errors enabled. Inspect the three AIC `.ko` files and the USB
accessory/composite modules as ARM64 ELF files with the matching kernel vermagic.
The upstream DT compiled here is a reference: the AIC board's antenna, reset and
UART initialization still require board integration and physical verification.

## V1.12M AIC device-tree candidate

After applying all shared and board-local Linux patches in the ADR's order:

```sh
make -C "$RADXA_LINUX_SRC" O="$RADXA_OUT" ARCH=arm64 LLVM=1 -j8 \
    rockchip/rk3566-radxa-zero-3w-aic8800d80.dtb
```

Patch `0004` adds this separate build-only target. It describes the no-eMMC
board, antenna GPIO and AIC SDIO settings. It retains upstream UART flow control
and USB OTG mode; Bluetooth reset/wake handling remains a runtime prerequisite.
Compilation and compiled-property checks are recorded in the ADR. This target
has not been booted and does not replace the generic upstream ZERO 3W DT.

Patch `0005` then requests the reference Bluetooth GPIO directions: PC1 output
low with pull-down, PB3/PB4 input with pull-up. UART1 retains all four
hardware-flow-control pins. GPIO/UART Schmitt and drive levels match the
reference readback; the ADR records raw drive fields because the diagnostic
mA labels cannot be copied as RK3566 drive-strength levels. Slew-rate control
is not provided by the pinned mainline driver. PC0 stays owned by MMC pwrseq.
The input hogs reserve the wake lines and provide no IRQ or suspend/wakeup handling;
review their ownership before enabling GPIO wake or `aic8800_btlpm`.

Rebuild both compiled targets and check them from the repository root:

```sh
make -C "$RADXA_LINUX_SRC" O="$RADXA_OUT" ARCH=arm64 LLVM=1 -j8 \
    rockchip/rk3566-radxa-zero-3w.dtb \
    rockchip/rk3566-radxa-zero-3w-aic8800d80.dtb
python3 tests/radxa_aic_dtb_test.py
```

The six tests use `pylibfdt`, either installed for the host interpreter or from
the existing boot-chain check's matching Python `site-packages`. The default
DTB directory is the host `output/radxa-platform-check/linux/arch/arm64/boot/dts/rockchip`
under `buildroot/`; set `RADXA_DTB_DIR` when using another build output. The
generic-tree hash is tied to the pinned 6.12.114 source. These checks prove
compiled properties; full schema and physical mainline validation remain pending.

## Bounded Bluetooth UART reset candidate

The standalone `aic-hci-reset.c` helper prepares the reset step observed in
Radxa OS without the factory tool's TCP server. Build and test on a Linux host:

```sh
cc -std=c11 -Wall -Wextra -Werror -Wconversion -Wshadow \
    aa_wireless_dongle/board/radxa/zero3w/checks/aic-hci-reset.c \
    -o /tmp/radxa-hci-reset
python3 tests/radxa_hci_reset_test.py
```

The tests use pseudo-terminals, not the physical board. They check actual serial
configuration, transmitted bytes, fragmented/maximum-length/unrelated events,
controller rejection, malformed input, fixed timeout, TTY restoration and
exclusive-device/file rejection. `RADXA_HCI_RESET_BIN` can select another host
binary. Cross-compile the C source with the target toolchain for an ARM64 build.

The candidate invocation on the board is `aic-hci-reset /dev/ttyS1`, **after**
radio power/firmware setup and **before** `hciattach`. It configures 1.5 Mbaud,
8N1 and RTS/CTS, disables software flow control, sends one H4 HCI Reset and
requires a successful matching Command Complete within a fixed two-second I/O
deadline. Normal success/error exits restore termios and release exclusive mode.
It refuses an exclusive UART or a non-N_TTY line discipline; existing raw-TTY
readers must still be stopped by the board startup sequence.

This helper is not installed by a package or startup service. One physical test
on the Radxa OS 6.1.84 reference passed: the attached-UART guard refused access,
the freed UART completed reset in approximately 5 ms, and hciattach/BlueZ were
restored with identical selected GPIO levels. Temporary test files were removed.
The reference's boot reset overlapped firmware loading and timed out; establish
firmware readiness before calling this helper and do not attach after failure.
Mainline GPIO/pin defaults, a concrete readiness gate and Buildroot/cold-start
verification remain pending. See the ADR for protocol references and limits.

## Firmware load-ordering predicate candidate

`aic-firmware-ready.sh` checks the pinned D80 SDIO candidate without changing
radio state. Host verification needs only Python 3, a POSIX shell, `cat`, `grep`
and `readlink -f`:

```sh
sh -n aa_wireless_dongle/board/radxa/zero3w/checks/aic-firmware-ready.sh
python3 tests/radxa_firmware_ready_test.py
```

For a read-only check as root on a board running the audited modules, invoke
`sh aic-firmware-ready.sh wlan0` (default interface: `wlan0`; an explicit name
can be used for the reference OS). It requires both `aic8800_bsp` and
`aic8800_fdrv` module `initstate` values to be `live`, normal BSP work mode,
and an interface backed by SDIO `c8a1:0082` using `aicwf_sdio`. The current
mode attribute is `/sys/devices/platform/aic-bsp/aicbsp_info/cpmode`.
If a driver module-owner link is exposed, it must point to `aic8800_fdrv`;
the audited vendor 6.1 kernel/SDK does not expose that link, whereas 6.12
sets the SDIO owner automatically. Exit status is 0 for the ordering predicate,
1 for not-ready or missing evidence, and 2 for invalid arguments. `RADXA_SYSFS_ROOT` redirects
reads for host fixtures only; runtime integration must use the real `/sys`.

The source chain and its limits are in ADR-0001's firmware-readiness section.
In the audited D80 configuration, synchronous BSP loading completes BT patch
uploads before fdrv module initialization succeeds. Module-directory presence,
netdev presence or the driver's internal completion signal alone is weaker:
the latter ignores a platform-init return and precedes host-wake IRQ setup.

Future startup integration must serialize these stages, stopping on every error:

1. Load the pinned BSP/fdrv modules synchronously with the audited build flags
   (`CONFIG_MCU_MESSAGE=n`) and normal work mode.
2. Require `aic-firmware-ready.sh` success.
3. Require bounded `aic-hci-reset /dev/ttyS1` success on the unattached UART.
4. Start hciattach, then BlueZ after attachment is established.

This script takes one snapshot; it neither polls nor starts any later stage.
It assumes startup owns module/power/mode changes. It does not establish
firmware identity, UART response, mainline pin correctness or cold-start
reliability. It is not installed in a runtime overlay. Seventeen fixture tests
pass. One read-only run on the Radxa OS 6.1.84 reference passed on `wlan0`
with status 0; a missing-interface check failed with status 1. The first board
run exposed the missing `aicbsp_info` path component and the vendor kernel's
absent owner link; the fixtures now cover both differences. Bluetooth and
hciattach remained active and the temporary script was removed. Mainline and
repeated cold-start verification remain pending; see ADR-0001 for evidence limits.

## Guarded reference-OS startup experiment

`make-startup-test.sh` emits configuration into a **new** output directory. It
does not install files, stop services or reboot anything:

```sh
sh board/radxa/zero3w/checks/make-startup-test.sh /tmp/new-aic-startup-bundle
```

Run that example from `aa_wireless_dongle/`, or prefix the script path with it
from the repository root. Host rollback regression tests run from the root:

```sh
python3 tests/radxa_startup_test.py
```

The bundle is specifically for the audited Radxa OS/systemd 252 reference.
Its reset drop-in loads the Debian package name `aic8800_fdrv_sdio`, checks
firmware readiness, then runs the ARM64 reset helper. The internal sysfs module
names remain `aic8800_bsp` / `aic8800_fdrv`. This packaging suffix must not be
copied into a Buildroot runtime without checking its actual module filenames.
The attach and BlueZ drop-ins use both `Requires=` and `After=` so failed reset
blocks attachment and BlueZ. Reset remains active after success for that boot.

An operator must first verify zero connected Bluetooth devices, powered hci0,
Wi-Fi autoconnect and enabled SSH. Copy the verified readiness script, ARM64
helper and generated `rollback.sh` to root-owned
`/var/lib/radxa-aic-startup-test/`. The three drop-ins map `reset.conf`,
`attach.conf`, `bluez.conf` to the reset instance, hciattach instance and
`bluetooth.service`, respectively, under `/etc/systemd/system/<unit>.d/`, using
the unique filename `90-radxa-aic-startup-test.conf`. Refuse existing experiment
files rather than overwriting another configuration. Preserve all vendor units.

Install the generated rollback service/timer and enable the timer **without
starting it in the current boot**: its monotonic boot deadline would already
be past. Verify all effective units with `systemd-analyze verify --man=no`,
exercise rollback before arming, then restore the test drop-ins and enable the
timer for the next boot. The timer runs at boot +180 s with 1 s accuracy and
restores the reference service configuration even after successful testing.
The rollback service retries failures; its completion marker is `rolled-back`
under the experiment directory. It must not use `reset-failed` on never-started
units, which may be unloaded after daemon-reload.

Use an orderly shutdown before the owner removes all power for a cold start.
Collect same-boot journal monotonic timestamps, reset exit status, attachment
and BlueZ state before rollback changes those states. Confirm automatic
restoration, then remove the disabled rollback units, experiment data and any
remaining temporary files. This diagnostic does not install a shipping startup
sequence or establish Buildroot/mainline cold-start acceptance.

The 2026-10-21 physical experiment verified one successful cold start with
readiness at 10.677 s, successful HCI Reset at 10.722 s, hciattach active at
11.156 s and BlueZ active at 11.897 s. The corrected automatic rollback completed
at 183.087 s with powered hci0 and N_HCI restored; experiment files were removed.
An earlier boot with an incorrect package-load name verified failure blocking
and exposed the unloaded-BlueZ rollback bug covered by the host tests. See the
ADR for the exact clocks, corrections and remaining hardware acceptance limits.
