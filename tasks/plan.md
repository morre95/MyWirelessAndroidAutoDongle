# Implementation plan: Radxa ZERO 3W support

**Status:** Approved by the owner on 2026-10-14 (Phase 2: Plan).
**Plan approval:** Owner confirmed: "ja jag godkänner planen".
**Task breakdown:** Approved by the owner on 2026-10-14: "ja jag godkänner uppgiftslistan".
**Execution:** Phase 4 continues with task #5. The received V1.12M/AIC8800D80 board boots the official Radxa OS diagnostic image; exact versions, firmware hashes and first source-compatibility results are recorded in ADR-0001. Final Buildroot source selection remains in progress.
**Date:** 2026-10-14
**Specification:** [Approved hardware-support spec, issue #4](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
**Target:** Radxa ZERO 3W, 1 GB RAM, no eMMC, microSD boot.
**Task tracker:** GitHub Issues in `morre95/MyWirelessAndroidAutoDongle`.

## Overview and assumptions

Deliver a ready-to-flash microSD image for the owner's board, retain all five existing Raspberry Pi targets, and document how another board can reuse the common dongle application and image pipeline.

The specification has been approved. Its acceptance requirements include 10 cold starts, five power reconnects, an under-30-second subsequent connection and a 30-minute session. eMMC support and tests are deferred.

RAM and absence of eMMC are confirmed. On 2026-10-21 the owner identified PCB revision V1.12M, and runtime SDIO/kernel evidence identified AIC8800D80 (the DT variant is `aic8800ds2`). Phone/headunit baseline and final cost accounting remain unresolved. This plan defines investigation and verification points rather than inventing a kernel or firmware selection.

The owner has approved the Phase 3 implementation task breakdown in GitHub Issues. Do not create `tasks/todo.md`: the project uses the external tracker. Phase 4 may proceed in dependency order. Source research and physical reference versions for #5 are recorded in `docs/adr/0001-radxa-zero3w-platform.md`; final platform selection awaits the remaining kernel/radio/accessory compatibility and firmware redistribution checks.

## Approved architecture

### Continue using the existing Buildroot external tree

Keep board configuration in `aa_wireless_dongle/configs/` and board-local integration in `aa_wireless_dongle/board/radxa/zero3w/`. Reuse `package/aawg/`, the common dongle overlay and existing protocol handling. Retain the current Buildroot submodule unless investigation demonstrates a specific need for an independently reviewed update.

Use the spec's proposed board id `radxa-zero3w` consistently for defconfig, isolated build output, Compose service, CI and release assets. Preserve existing Pi identifiers.

### Keep hardware initialization at the board boundary

Move Pi-specific driver initialization out of the common runtime path, preserving the Pi behavior in its overlay, and provide the corresponding Radxa initialization in its board overlay. Keep shared gadget setup and daemon startup shared.

Preserve `wlan0` as the application's existing interface contract by configuring the Radxa interface at the board boundary where feasible. If that is not reliable, investigate a small board-neutral configuration mechanism; changing public setting keys or protocol behavior requires a spec update.

The daemon already discovers a USB device controller under `/sys/class/udc/`. Verify that the selected Radxa device tree exposes the intended OTG controller and that discovery/binding works. Do not add model-specific branches to Bluetooth or proxy logic.

### Separate boot/image construction from dongle behavior

Provide Radxa-specific bootloader/device-tree/image layout and mounts. Preserve a computer-visible configuration file and persistent pairing storage on microSD.

Extract only genuinely shared image preparation, such as placement of `aawgd.conf`, from the current Pi hooks when needed. Keep Pi boot packaging in Pi hooks; do not make Radxa call a Pi image generator or assume Pi partition numbering.

### Select sources using evidence

The first decision record must identify the actual radio hardware and a compatible, pinned bootloader/kernel/device-tree/driver/firmware combination. Evaluate official Radxa sources and upstream support against the same required capabilities: microSD boot, Wi-Fi AP, Bluetooth and Android accessory gadget operation.

The existing accessory patches were rebased to the Pi 6.12 kernel. Verify compatibility with the selected Radxa source; retain the working Pi patch path and use an explicitly scoped Radxa patch variant if necessary. An OTG controller without the required accessory function and uevents is insufficient.

## Component dependencies and build order

| Stage | Result | Depends on |
| --- | --- | --- |
| A: Platform feasibility | Identified hardware, pinned-source proposal and capability evidence | Approved spec; physical revision/radio information before final selection |
| B: MicroSD boot | Fresh image boots the no-eMMC board with correct mounts and configuration file | A |
| C: USB transport | Default/accessory gadget negotiation and bidirectional USB path operate | B; accessory kernel/patch compatibility established in A |
| D: Wireless operation | Onboard Wi-Fi AP and Bluetooth pairing operate together | B; radio driver/firmware selection established in A |
| E: Complete dongle flow | First pairing, automatic connection, configuration and persistence work | C and D |
| F: Image distribution | Reproducible build entry point, CI artifact, checksums and release integration | B and E |
| G: Release acceptance | Physical Radxa/Pi evidence, installation guide, board-addition guide and cost record | E and F |

Build order: **A → B → C/D → E → F → G**.

This is a sequence of user-visible verification slices, not separate product modules. The linked task breakdown splits boot construction, driver packaging, firmware packaging and hardware verification into focused slices. If the resolved source choice needs more than five files in a task, split the prerequisite before implementation.

## Verification checkpoints

### Checkpoint A: Platform choice

Record the PCB revision, wireless module, no-eMMC configuration, source revisions and firmware licenses. Confirm credible support for AP mode, Bluetooth and accessory gadget requirements before treating a platform choice as settled.

Prepare the source-choice ADR in `docs/adr/` during the corresponding implementation/investigation task. If the board has not arrived, source research can proceed, but revision-dependent selection and physical evidence remain pending.

Do not silently replace missing AP support with an external adapter or accept a separate power supply: those change the approved installation/cost assumptions.

### Checkpoint B: Fresh-card boot

Flash a fresh card and boot the target board headlessly. Verify the root/configuration/persistent mounts, readable `aawgd.conf` on a computer, and repeat boot after a full power removal.

Record image checksum, kernel/device-tree revisions and boot logs. A bench supply can support diagnosis; car USB power operation must be tested before acceptance.

### Checkpoint C/D: Required interfaces

Verify USB enumeration, the default and accessory gadgets, the accessory-start uevent expected by the daemon, and USB reconnection. Separately verify hostapd AP mode and noninteractive Bluetooth pairing with the selected firmware, then exercise them simultaneously.

Record useful initialization failures and affected logs. A working Wi-Fi client or a single successful USB enumeration does not complete this checkpoint.

Run the existing host regression test after affected shared changes. Run the representative Pi build/smoke checks if shared initialization or image preparation changes.

### Checkpoint E: Complete user flow

Follow the README-style procedure from an untouched release-candidate image: connect to the OTG port, pair, start Android Auto, power off, reconnect automatically, edit user settings, and verify persistence.

Start the accepted timing/reliability measurements here; rerun them on the exact image proposed for release at Checkpoint G.

### Checkpoint F/G: Distribution and final acceptance

Build all retained Pi targets and Radxa in CI. Extend the release artifact selection beyond its current Pi-only pattern while preserving existing assets. Verify compression/checksums, names, links and release packaging for the exact tested image.

Record every AC-1 through AC-10 result from the approved spec. The final Radxa image must pass 10 cold starts and five power reconnects, each subsequent connection under 30 seconds, plus the 30-minute navigation/music session. Verify settings/pairing persistence and at least one physical Pi smoke test.

Update installation/build documentation, the contributor board-addition guide, tested-hardware limitations and the dated cost breakdown. Final release acceptance needs the real asset URL and checksum, not merely a successful workflow artifact upload.

## Verification commands

Existing representative Pi build:

```sh
docker compose run --rm --build rpi02w
```

Existing host regression check:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -Iaa_wireless_dongle/package/aawg/src \
    tests/proxy_diagnostics_test.cpp -o /tmp/aawgd-proxy-test
/tmp/aawgd-proxy-test
```

Retained Pi targets before release:

```sh
docker compose run --rm --build rpi0w
docker compose run --rm --build rpi3a
docker compose run --rm --build rpi4
docker compose run --rm --build rpi5
```

Proposed Radxa commands (available only after the relevant integration tasks):

```sh
docker compose run --rm --build radxa-zero3w
make -C buildroot BR2_EXTERNAL=../aa_wireless_dongle O=output/radxa-zero3w radxa-zero3w_defconfig
make -C buildroot/output/radxa-zero3w
```

Task-specific checks will include image contents, hashes and the selected kernel configuration, plus focused tests for any added shared behavior. Hardware-specific commands depend on the verified driver/controller and belong in the test procedure after source selection.

## Task-list index

**Canonical task list: GitHub Issues.** Issue #4 is the parent specification. The 13 approved tasks are native GitHub sub-issues, with native blocked-by dependencies and standard triage labels recording readiness or missing information.

| Order | Stage | Task | Blocked by |
| --- | --- | --- | --- |
| 1 | A | [#5: Radxa: identify the board and select pinned platform sources](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5) | — |
| 2 | B | [#6: Radxa: isolate Raspberry Pi driver initialization](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/6) | [#5](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5) |
| 3 | B | [#7: Radxa: build the pinned kernel and boot components](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/7) | [#5](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5), [#6](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/6) |
| 4 | B | [#8: Radxa: generate a bootable microSD image](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/8) | [#7](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/7) |
| 5 | C | [#9: Radxa: enable and verify the Android accessory USB path](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/9) | [#8](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/8) |
| 6 | D | [#10: Radxa: package the selected wireless driver](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/10) | [#7](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/7) |
| 7 | D | [#11: Radxa: include redistributable wireless firmware](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/11) | [#10](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/10) |
| 8 | D | [#12: Radxa: start onboard Wi-Fi AP and Bluetooth pairing](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/12) | [#8](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/8), [#11](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/11) |
| 9 | E | [#13: Radxa: verify the complete first-use and reconnection flow](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/13) | [#9](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/9), [#12](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/12) |
| 10 | F | [#14: Radxa: add the image to Compose, CI and release packaging](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/14) | [#13](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/13) |
| 11 | G | [#15: Radxa: document installation, board additions and hardware cost](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/15) | [#13](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/13), [#14](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/14) |
| 12 | G | [#16: Radxa: complete physical acceptance and Raspberry Pi regression checks](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/16) | [#15](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/15) |
| 13 | G | [#17: Radxa: verify the public release image and download path](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/17) | [#16](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/16) |

Each approved issue contains acceptance criteria, verification, likely files, estimated scope and spec references. Task state lives in GitHub; this table is an index, not a second checklist.

Checkpoints follow platform selection (#5), fresh-card boot (#6–#8), kernel/radio packaging (#9–#11), required interfaces (#12), complete user flow (#13), and final distribution/physical acceptance (#14–#17). At each checkpoint, record completed results, unresolved failures and affected regressions before proceeding.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Different radios across ZERO 3W revisions | Wrong driver/firmware or missing AP/Bluetooth behavior | Identify the received board before final source selection; claim only tested revision(s) |
| Vendor or upstream kernel lacks compatible accessory functionality | A bootable image cannot serve as the dongle | Test patch/configuration compatibility early; preserve the known Pi path |
| OTG power from the car is insufficient | Resets or additional hardware outside the intended installation | Test power-on and sustained operation on the actual headunit; record setup and revisit requirements if needed |
| Pi assumptions leak into common initialization or mounts | New board fails or existing Pi support regresses | Board-local overlays/hooks, targeted shared changes, Pi build and physical smoke evidence |
| Release step still selects Pi-only assets | Radxa users cannot download the image | Explicit CI/release integration check and final asset URL/checksum verification |
| A working Radxa OS baseline is mistaken for a completed port | Buildroot boot or dongle behavior remains untested | Keep diagnostic versions separate from selected Buildroot sources and record acceptance on the actual candidate image |
| Actual hardware/timing/cost misses spec | Quietly weakened requirements | Record the result, identify cause and update the spec through review before accepting a different target |

## Sequencing and independent work

Source research and preparation of documentation/test procedures can proceed independently of having the physical board. USB and radio investigation share kernel/defconfig dependencies; coordinate those edits and integrate sequentially once the source choice is stable. Complete connection tests depend on both paths.

CI packaging/documentation can be prepared after the artifact contract is fixed. Final physical acceptance and release verification are sequential against the same tested image. No agent delegation is needed for this plan.

## Remaining questions

- Complete source provenance/pins, AIC compatibility and firmware redistribution terms; PCB V1.12M and AIC8800D80 are now identified.
- Phone/Android version, headunit/car and an existing Pi available for the comparison/smoke test.
- Whether the approximately SEK 400 target includes shipping/VAT and which microSD/data-cable costs must be newly incurred.

Bootloader/kernel/device-tree/radio versions and image layout are engineering decisions to resolve in Stage A, not additional user requirements. The acceptance counts were resolved by spec approval.

## Sources and approval boundary

The approved architecture follows the approved [specification](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4), the existing repository build/runtime paths and the official [Buildroot external-tree documentation](https://buildroot.org/downloads/manual/manual.html). Revision, port and power investigation follows the [Radxa hardware guide](https://docs.radxa.com/en/zero/zero3/hardware-design/hardware-interface) and [FAQ](https://docs.radxa.com/en/zero/zero3/faq).

The owner has approved the specification, Phase 2 plan and Phase 3 task breakdown. Phase 4 is authorized in dependency order. These approvals do not select unresolved platform sources or mark hardware acceptance complete. Task #5 remains open pending final source selection; PCB/radio identification is resolved.

## Execution evidence: 2026-10-21

The owner requested version documentation and continuation to the next step. ADR-0001 now records the official diagnostic image/checksums, kernel/U-Boot/AIC/BlueZ/rsetup versions, owner-read PCB revision and hashes of the firmware actually loaded. MicroSD boot, Wi-Fi client operation and a powered Bluetooth controller are observed; AP operation, pairing and accessory negotiation remain pending.

The next source-compatibility slice checked the existing accessory patches against the vendor 6.1.84 snapshot and maintained upstream 6.12.114. The vendor already contains partial uevent integration and rejects the Pi patch; both patches apply in order to the upstream candidate. The installed AIC package maps to source commit `fc7cbdd1791416c2457fa27a59e508bf325c9c3f`, whose six relevant firmware/configuration files match the board. These findings guide the first compatibility build; they do not complete #5 or bypass #6's prerequisite.

The follow-on ARM64 object build used LLVM 23.1.3 and the verified 6.12.114/AIC archives. It exposed and reproduced a changed HID argument list, the backported cfg80211 monitor callback signature, and two strict-prototype errors. Three board-scoped patches now correct these failures. USB composite/accessory and the three AIC aggregate objects compile as ARM aarch64 ELF files; the existing host regression test passes. ADR-0001 records hashes, patch order and reproduction commands. These preparation patches are not connected to an active defconfig; full linking, target DT/boot-chain integration and firmware redistribution verification remain prerequisites to finishing #5 and proceeding to #6.

The next slice completed full Linux 6.12.114 `Image`, modules and upstream ZERO 3W DT compilation, then linked the three AIC `.ko` files against the generated symbol table with MODPOST errors enabled. All five accessory/composite/AIC modules are ARM64 with matching vermagic. An isolated board-local check also built U-Boot 2026.01 with Buildroot's existing rkbin pin, RK3566 DDR 1.23 and RK3568 BL31 1.44. Packed-image checks verified the DDR/SPL/header hashes, FIT placement and all six BL31 load segments. The configuration and reproduction commands are saved under `board/radxa/zero3w/checks/`; they are not a shipping target. Live DT reads confirmed the recorded radio/antenna pins, and the installed startup scripts exposed a bounded UART HCI reset before `hciattach`. ADR-0001 records the results and limits. No SD card was flashed. AIC-specific DT/runtime integration, firmware terms, full image assembly and physical operation remain pending; #5 stays open and #6 retains its prerequisite.

After merge into main (`42ccde9`), a separate DT preparation slice adds a build-only V1.12M/AIC8800D80 variant with no eMMC, the observed antenna GPIO and vendor-reference SDIO settings. It compiles on the pinned 6.12.114 kernel; compiled-tree checks pass and the generic ZERO 3W DTB remains byte-identical. Bluetooth reset/wake initialization and physical testing remain pending. Upstream licensing discussion clarifies GPL v2 driver source versus GPL v3 packaging, but does not resolve the selected opaque firmware files. ADR-0001 records the source links and limits. Task #5 remains open; this does not bypass downstream prerequisites or provide a shipping image.

After that slice merged (`e7ef1f1`), a standalone UART HCI Reset candidate replaces the factory-server dependency in the source investigation. All 13 host pseudo-terminal tests pass for command/event handling, UART setup, error paths, fixed timeout and cleanup; ARM64 cross-compilation passes with strict warnings. It is not installed by a package or service. Physical GPIO/firmware sequencing and UART/HCI handoff remain pending. The owner inserted the reference Radxa OS card in the reader; no Buildroot image is ready to flash. A complete read-only recovery copy was saved locally and verified by decompression/SHA-256; the configured image and its private metadata stay in ignored build output. Task #5 stays open and downstream prerequisites remain unchanged.
