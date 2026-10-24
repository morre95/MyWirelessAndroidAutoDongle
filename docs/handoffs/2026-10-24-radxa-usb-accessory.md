# Radxa ZERO 3W: USB accessory negotiation — 2026-10-24

Handoff for [task #9](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/9)
of the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
The approved task spec is the 2026-10-24 comment on #9. The code merged in PR #25.
This handoff replaces the task table and next steps of the
[AIC driver handoff](2026-10-24-radxa-wireless-driver.md). The build environment,
hardware state, card helpers and privacy rules of the
[2026-10-23 continue point](2026-10-23-radxa-continue.md) still apply.

## What changed

- `board/radxa/zero3w/linux.fragment`: `USB_LIBCOMPOSITE=y` and `USB_CONFIGFS=y`.
  The image has no hotplug module loader, and nothing loaded the former modules.
- `tests/radxa_platform_build_test.py`: checks that the gadget stack (DWC3 dual role,
  libcomposite, configfs, `USB_F_ACC`, `USB_F_FS`, INNO USB2 PHY) is built in.
- `board/radxa/zero3w/checks/aoa-host-test.py`: a standard-library host tool. It waits
  for the default gadget, sends the AOA handshake, waits for the accessory and resets
  it from the host. Run it with sudo; it writes a JSON-lines log without serial numbers.
- `board/radxa/zero3w/checks/usb-accessory-test.conf`: the test-only block appended to
  a test card's `aawgd.conf`. It selects USB-first mode and logs to
  `/persist/usb-test/boot-N/`. Never ship it.

Buildroot's kmod package also installs `S11modules`, which loads
`/etc/modules-load.d/*.conf`. Built-in was chosen because it needs no file to keep in
sync. #12's AIC loading has its own ordered, gated contract anyway.

## Hardware run

| Item | Value |
| --- | --- |
| Production image | `257f3549ff9af68f532c2d4306fb3dfad8a4d2217895ab5bcaa576ff56aea4ed`, 385,875,968 bytes |
| Test card image | `7e31e20fe63ee0734dc44c5592ef5683be92d58278fa6c689938b589b72ed845`, differs only in the FAT partition |
| Card write | Verified by two readbacks |
| Host | This PC as headunit; the board powered from its OTG port |
| Boot 1 | Host tool passed; card copy `b198f802…7ad49` |
| Boot 2, after power removal | Host tool passed; card copy `0351bd88…840bb` |

Each boot: default gadget `18d1:4ee1` at 480 Mbit/s, AOA protocol 2, `ACCESSORY=START`
delivered to `aawgd`, re-enumeration as `18d1:2d00` 0.8 s later, then a host reset
followed by `CONFIGURED` again. The ADR section "USB accessory negotiation on the
board: 2026-10-24" has the step-by-step table and the two harmless kernel messages.

Board log SHA-256 (private bundle, `persist-usb-test/boot-N/`):

| File | Boot 1 | Boot 2 |
| --- | --- | --- |
| `uevents.txt` | `457ebea4193dcd87e19039c859db0a9df23e74123fa6b235dcdea7f5d097c882` | `145ffbd2cd6eb1d7c72b759141ebfa4842c13fbb81bfbddb0a6a455d9bfef4aa` |
| `messages.txt` | `ee4a13c8973a9250f9c63e78bb2d3912a028f6d66bfcc1e6f25fe07816c657cc` | `90266d0c13d0ff8739b1737e6e066654720cc77f46d860d519f463009e246c14` |
| `dmesg.txt` | `d368f4cd85d1f8430af468b959a19d7376f44e752d8b3164992a261f35d54756` | `b71ff1506d69ecba80a60f8ba67d4774cf78cf7d3a7946307e14693fc8772096` |

The logs contain no MAC addresses, SSIDs or real serial numbers; the gadget serial is
the placeholder `0123456` from `S92usb_gadget`.

## Private bundle

Kept in the ignored `buildroot/output/radxa-usb-20261024/`:

- `tools/radxa_usbtest_flash.py`, `tools/radxa_usbtest_capture.py`: dated copies of
  the 10-23 helpers with this image's hash and layout.
- `host-1.jsonl`, `host-2.jsonl`: host tool logs.
- `boot-N/card.img`, `capture.json`: read-only card copies.
- `boot-N/persist-usb-test/`: board logs extracted from them with `debugfs`.

## Card state

The card holds the **test** image after two boots. Its `aawgd.conf` still selects
USB-first mode and runs the capture block. Reflash the production image, or the
next task's image, before using the card as evidence again. The Radxa OS backup
remains the recovery point.

## Task state

| Task | State | Notes |
| --- | --- | --- |
| #9 USB accessory | Code merged (PR #25); evidence in this handoff | Bidirectional transport deferred to #12 by owner decision |
| #11 firmware terms | Open | [radxa-pkg/aic8800#109](https://github.com/radxa-pkg/aic8800/issues/109) had no reply |
| #12 Wi-Fi AP and Bluetooth | Blocked by #11 | Owes #8's boot log and #9's bidirectional transport over the accessory |

## Next steps

1. Settle #11 (firmware terms).
2. #12: bring up Wi-Fi and Bluetooth. Once a phone connects, check that data flows both
   ways through `/dev/usb_accessory`, using `aoa-host-test.py` as a starting point for
   the host side, and record #8's boot log.
