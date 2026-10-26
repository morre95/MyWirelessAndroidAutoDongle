# Radxa ZERO 3W: documentation and cost — 2026-10-26

Handoff for [task #15](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/15)
of the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
The approved task spec is the
[2026-10-26 comment on #15](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/15#issuecomment-6414497520).
This handoff replaces the task table of the
[distribution handoff](2026-10-24-radxa-distribution.md).

## What changed

Docs only, on branch `docs/radxa-documentation`.

- **`README.md`:**
  - Radxa ZERO 3W is listed under a new "In testing" heading, limited to PCB V1.12M, 1 GB, no eMMC, AIC8800D80, booting from microSD. There's no release link yet.
  - Image names, the `sha256sum -c` check, card size, the USB-C 1 port with a USB-C to USB-A cable, and the 5 GHz AP.
  - A Radxa limitations section: 37–46 s cold start, one phone and one head unit tested.
- **`BUILDING.md`:** the Radxa build needs about 14 GB, the manual Radxa build name, and how to check a download against its checksum.
- **`docs/adding-a-board.md` (new):** the board-addition checklist, with the Radxa files as examples.
- **`docs/hardware-validation/radxa-zero3w.md`:** the cable, and a bill of materials with the deviation from SEK 400 and your review of it.

## Owner decisions (2026-10-26)

1. Radxa goes in the README now with an "in testing" status. #17 changes it to supported.
2. The car test used a USB-C to USB-A cable.
3. Purchases, all from AliExpress: board 683 kr, SanDisk Ultra 32 GB 159 kr, shipping 176 kr.
4. The total of 1,018 kr exceeds the SEK 400 target. The owner accepts it, because the build is still significantly cheaper than a Raspberry Pi Zero.

## Verified

| Check | Result |
| --- | --- |
| Relative links in the four files | All resolve |
| `docker compose config --services`, `./build.sh --help` | `radxa-zero3w` with the label "Radxa ZERO 3W", as documented |
| `sha256sum -c radxa-zero3w-sdcard.img.xz.sha256`, as written in the docs | OK, on the CI run `40101754727` artifact |
| `WirelessAA` label and `aawgd.conf` on the CI image | Passed in the [#14 image check](2026-10-24-radxa-distribution.md#ci-radxa-image) |
| Board-addition guide against the Radxa files | Every tracked Radxa file under `aa_wireless_dongle/` maps to one checklist item |
| Facts in the guide | Checked against the defconfig, `genimage.cfg`, `post-build.sh`, the overlay, the `aic8800*` packages, `build.sh` and the workflow |

## Gaps

- **Not recorded:** the cable's price, or whether it was already owned; the order date; whether VAT is included; which car USB port was used. The BOM says "not recorded" for each.
- Flashing a card from the release asset and the car test belong to #16 and #17.

## Task state

| Task | State | Notes |
| --- | --- | --- |
| #15 Documentation and cost | PR open | This handoff |
| #16 Physical acceptance and Pi regression | Open | Unblocked by #15 |
| #17 Public release check | Open | Needs a real `v*` release after #16; it also switches the README from "in testing" to supported |
