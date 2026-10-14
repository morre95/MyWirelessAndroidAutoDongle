# ADR-0001: Radxa ZERO 3W platform sources

## Status

Proposed. Source investigation for [task #5](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5) is recorded; final platform selection remains pending the received board's PCB revision/radio and kernel/driver compatibility checks. This record does not establish a working image or complete task #5.

## Date

2026-10-14

## Context

The approved [specification](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4) targets a Radxa ZERO 3W with 1 GB RAM, no eMMC and microSD boot. The owner confirmed that the board has not arrived. Its PCB revision and onboard wireless module are therefore unknown.

The first delivery needs onboard Wi-Fi AP and Bluetooth, an Android accessory USB gadget, computer-editable configuration, persistent pairing and normal car USB power operation. Existing Pi targets must remain supported. eMMC-equipped variants are outside this delivery.

The repository pins Buildroot 2026.02.3 at `679b9ead7620bbf193620d1ebf56f53c1764d37a`. Its Pi kernel and accessory patches are a working Pi baseline, not a Radxa BSP.

## Decision established by the approved plan

Keep Buildroot and the existing external tree. Add board-local boot/image/runtime integration and reuse the common application. Do not update the Buildroot submodule or change Pi source pins as a side effect.

Final kernel/radio/firmware source selection is deferred until the actual radio is identified. The snapshots below are **audit references and candidates, not a selected release bill of materials**. Before a defconfig is implemented, record the complete selected source combination, hashes and required patch adaptations.

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

If the board uses the audited AIC SDIO driver, [its Makefile](https://github.com/radxa-pkg/aic8800/blob/e9e43ed79c50483080e9bcdfb08caeeb869d7191/src/SDIO/driver_fw/driver/aic8800/Makefile) enables `aic8800_bsp`, `aic8800_fdrv` and `aic8800_btlpm`. Its default Ubuntu path derives the kernel directory/version from the host's `uname`; it also sets `CONFIG_USE_FW_REQUEST = n`. A Buildroot package must control the target kernel/module build and verify the driver's firmware-loading route instead of using host DKMS or installing Debian packages into the image.

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

## Consequences and next evidence

- Source research can proceed now, but task #5 stays open. Dependent tasks retain their tracker prerequisites.
- Once the board arrives, record its PCB revision and radio marking/identifier, then select and pin the complete compatible source/firmware combination.
- Verify accessory patch/configuration compatibility and the selected radio build before promoting this ADR to Accepted.
- MicroSD boot, AP/Bluetooth coexistence, USB enumeration/negotiation, power and connection reliability remain physical acceptance checks in subsequent tasks.
- Do not publish a supported image or close hardware criteria based on this source investigation.

## Verification performed

Checked the existing Buildroot version and Pi source/patch configuration using task #5's commands. Inspected the cited official upstream/Radxa snapshots, source Makefiles/DTs and local Buildroot package metadata. No target image was built and no physical test was performed in this documentation slice.
