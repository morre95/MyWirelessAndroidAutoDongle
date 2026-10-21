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
and an interface backed by SDIO `c8a1:0082` using `aicwf_sdio` from
`aic8800_fdrv`. Exit status is 0 for the ordering predicate, 1 for not-ready or
missing evidence, and 2 for invalid arguments. `RADXA_SYSFS_ROOT` redirects
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
reliability. It is not installed in a runtime overlay. Fourteen fixture tests
pass; board execution and repeated cold-start verification remain pending.
