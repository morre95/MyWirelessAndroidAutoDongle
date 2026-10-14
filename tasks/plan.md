# Implementation plan: Radxa ZERO 3W support

**Status:** Draft for owner review (Phase 2: Plan).
**Date:** 2026-10-14
**Specification:** [Approved hardware-support spec, issue #4](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
**Target:** Radxa ZERO 3W, 1 GB RAM, no eMMC, microSD boot.
**Task tracker:** GitHub Issues in `morre95/MyWirelessAndroidAutoDongle`.

## Overview and assumptions

Deliver a ready-to-flash microSD image for the owner's board, retain all five existing Raspberry Pi targets, and document how another board can reuse the common dongle application and image pipeline.

The specification has been approved. Its acceptance requirements include 10 cold starts, five power reconnects, an under-30-second subsequent connection and a 30-minute session. eMMC support and tests are deferred.

RAM and absence of eMMC are confirmed; PCB revision, wireless module, phone/headunit baseline and final cost accounting remain unresolved. This plan defines investigation and verification points rather than inventing a kernel or firmware selection.

Phase 3 will create implementable tasks in GitHub Issues after this plan is approved. Do not create `tasks/todo.md`: the project uses the external tracker. Phase 4 begins only after the task breakdown is reviewed. No code changes are part of this planning delivery.

## Proposed architecture

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

This is a sequence of user-visible verification slices, not separate product modules. Task breakdown will split stages where changes exceed five files or a focused session, especially boot construction and radio packaging.

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

**Canonical task list: GitHub Issues.** Issue #4 is the parent specification. No implementation task issues have been created in this Phase 2 draft.

After plan approval, Phase 3 will populate this section with ordered tracker links for the implementation slices and their dependencies. Each issue will contain acceptance criteria, executable verification where applicable, likely files (at most approximately five), and spec AC references. Checkpoints will remain in this plan or be linked as tracker items; avoid duplicating task state in a local checklist.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Different radios across ZERO 3W revisions | Wrong driver/firmware or missing AP/Bluetooth behavior | Identify the received board before final source selection; claim only tested revision(s) |
| Vendor or upstream kernel lacks compatible accessory functionality | A bootable image cannot serve as the dongle | Test patch/configuration compatibility early; preserve the known Pi path |
| OTG power from the car is insufficient | Resets or additional hardware outside the intended installation | Test power-on and sustained operation on the actual headunit; record setup and revisit requirements if needed |
| Pi assumptions leak into common initialization or mounts | New board fails or existing Pi support regresses | Board-local overlays/hooks, targeted shared changes, Pi build and physical smoke evidence |
| Release step still selects Pi-only assets | Radxa users cannot download the image | Explicit CI/release integration check and final asset URL/checksum verification |
| Hardware has not arrived | Physical acceptance cannot finish | Continue source/build preparation; keep physical checkpoints pending |
| Actual hardware/timing/cost misses spec | Quietly weakened requirements | Record the result, identify cause and update the spec through review before accepting a different target |

## Sequencing and independent work

Source research and preparation of documentation/test procedures can proceed independently of having the physical board. USB and radio investigation share kernel/defconfig dependencies; coordinate those edits and integrate sequentially once the source choice is stable. Complete connection tests depend on both paths.

CI packaging/documentation can be prepared after the artifact contract is fixed. Final physical acceptance and release verification are sequential against the same tested image. No agent delegation is needed for this plan.

## Remaining questions

- PCB revision and radio module of the ordered board.
- Phone/Android version, headunit/car and an existing Pi available for the comparison/smoke test.
- Whether the approximately SEK 400 target includes shipping/VAT and which microSD/data-cable costs must be newly incurred.

Bootloader/kernel/device-tree/radio versions and image layout are engineering decisions to resolve in Stage A, not additional user requirements. The acceptance counts were resolved by spec approval.

## Sources and approval boundary

Architecture proposals follow the approved [specification](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4), the existing repository build/runtime paths and the official [Buildroot external-tree documentation](https://buildroot.org/downloads/manual/manual.html). Revision, port and power investigation follows the [Radxa hardware guide](https://docs.radxa.com/en/zero/zero3/hardware-design/hardware-interface) and [FAQ](https://docs.radxa.com/en/zero/zero3/faq).

This plan is the Phase 2 review artifact. Owner approval of the spec does not by itself approve this plan, select unresolved platform sources, or authorize starting implementation before the subsequent workflow gates.

