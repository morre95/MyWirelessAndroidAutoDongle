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
