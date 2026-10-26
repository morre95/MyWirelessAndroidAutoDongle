# Radxa ZERO 3W hardware validation

Hardware record for the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
The [final-hardware acceptance](#final-hardware-acceptance-2026-10-26) ran the full
acceptance matrix on the release candidate image ([task #16](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/16)).
The [initial test](#initial-test-2026-10-24) is the earlier first-use record of
[task #13](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/13), kept as history.

## Final-hardware acceptance (2026-10-26)

The owner ran these tests in the car and recorded the times with a stopwatch, in
whole seconds, started at car power-on. **HU ready** is when the head unit's home
screen is usable. **AA** is when Android Auto is on screen and responds to touch.

### Setup

| Item | Value |
| --- | --- |
| Candidate | CI run [40103814333](https://github.com/morre95/MyWirelessAndroidAutoDongle/actions/runs/40103814333) on `main` `b86bf48`. All six board builds and `merge` succeeded. Later commits on `main` change only docs |
| Radxa image | `radxa-zero3w-sdcard.img.xz`, SHA-256 `4ee48edc490c0f76b08ac173186aeb0591b94341e05d268810a26f34b76057ed`; decompressed SHA-256 `d79c85e5f31497829ad20e0eaf2297158947ebf88eb9921fe28581ee8c587a4e`. Written to a fresh card; the owner reported that the readback matched |
| Pi image | `raspberrypizero2w-sdcard.img.xz` from the same run, SHA-256 `00717adbfa84e1d408741098d309ae73665361ad1b1beae040952f94e1392ea7`, on a fresh card |
| Boards | The Radxa ZERO 3W from the [initial test](#test-setup); a Raspberry Pi Zero 2 W on its OTG port |
| Phone | Samsung Galaxy S24, SM-S921B/DS, Android 16. Old dongle Bluetooth entries removed before the test |
| Head unit | As in the [initial test](#test-setup) |
| Connection | The car's front USB port, a USB-C to USB-A cable, into the Radxa's USB-C 1 port |
| `aawgd.conf` | As built, then `AAWG_UNIQUE_NAME_SUFFIX=Test` from the AC-7 check onwards, including the passing cold-start series |

### Results

| Spec criterion | Result | Notes |
| --- | --- | --- |
| AC-1 build | **Passed** | Every board builds in the candidate run. The Radxa image checks are in the [distribution handoff](../handoffs/2026-10-24-radxa-distribution.md) |
| AC-3 first use | **Passed** | Paired from the phone's Bluetooth settings with no extra steps; Android Auto started |
| AC-4 cold start | **Passed** | 10 cold starts in a row, all under 30 s: 21–27 s, average 24.3 s, with no re-pairing or touching anything. An earlier series failed; see [cold starts](#cold-starts) |
| AC-5 power reconnect | **Passed, on observation only** | 5 unplug/replug cycles, each recovered without re-pairing in 23–29 s from plug-in. No logs; see [evidence limits](#evidence-limits) |
| AC-6 session | **Passed, on observation only** | 50 minutes with Google Maps navigation and Spotify: no disconnects, no audio stutter. Display, touch, the steering-wheel buttons and voice worked. No logs; see [evidence limits](#evidence-limits) |
| AC-7 settings | **Passed** | `AAWG_UNIQUE_NAME_SUFFIX=Test` was set in `aawgd.conf` from a computer. After a cold start the phone listed the dongle as `WirelessAADongle-Test`. The passing cold-start series below ran with this setting: all 10 starts reconnected without re-pairing |
| AC-8 host tests and Pi | **Passed** | The proxy C++ test, `tests/build_sh_test.py` and all 16 `tests/radxa_*_test.py` pass ([record on #16](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/16#issuecomment-6419654882)). The Pi Zero 2 W passed first pairing, a settings change across a cold start, a 5-minute session and 5 timed cold starts |
| AC-9 shared code | **Passed** | The Radxa overlay adds only `etc/fstab` and `etc/hostapd.conf.in`; `package/aawg/` has no board-specific code. The checklist is [docs/adding-a-board.md](../adding-a-board.md) |
| AC-10 docs and cost | **Passed, with a reviewed deviation** | Docs from [#15](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/15). The cost is over target, accepted by the owner; see the [bill of materials](#bill-of-materials-recorded-2026-10-26) |

AC-2, the published release, is checked in [task #17](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/17).

### Cold starts

Each start began with the car and head unit fully off. AC-4 is judged on the
final series of 10.

| Run | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HU ready (s) | 3 | 3 | 2 | 3 | 2 | 3 | 2 | 2 | 3 | 2 |
| AA (s) | 21 | 23 | 24 | 26 | 23 | 26 | 27 | 22 | 25 | 26 |

The first series did not pass. Its run 10 took exactly 30 s, which is not under
30 s, and an eleventh start could not replace it. The series was rerun in full.

| Run | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HU ready (s) | 2 | 3 | 2 | 3 | 3 | 4 | 3 | 3 | 3 | 5 | 3 |
| AA (s) | 29 | 27 | 28 | 22 | 27 | 25 | 24 | 22 | 21 | 30 | 25 |

### Power reconnects

Car and head unit on with Android Auto running; the cable was unplugged from the
board for 10 s. Times are from plug-in.

| Cycle | 1 | 2 | 3 | 4 | 5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| AA (s) | 23 | 24 | 29 | 28 | 24 |

### Pi baseline

The Raspberry Pi Zero 2 W in the same car, with the same phone and USB port.

| Run | 1 | 2 | 3 | 4 | 5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HU ready (s) | 2 | 3 | 3 | 2 | 3 |
| AA (s) | 16 | 23 | 24 | 18 | 23 |

The Pi averaged 20.8 s and the Radxa 24.3 s in its passing series.

### Evidence limits

- **No logs.** The spec asks for logs for AC-5 and AC-6. No computer was in the car, and the owner decided on 2026-10-26 not to collect them ([decision on #16](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/16#issuecomment-6423749720)). A crash or OOM kill of `aawgd`, or a power reset, would have dropped Android Auto, and that never happened. Problems the screen does not show were not checked: a background service killed for lack of memory, driver errors the board recovered from, or memory running low.
- **Whole seconds.** The stopwatch times are rounded to the second.
- **One of each.** One board, one phone, one head unit and one car port.
- **Faster than the initial test.** These cold starts took 21–30 s, against 37–46 s in the initial test. The cause was not measured. The head unit was ready in 2–5 s in this test; its boot time in the initial test was not recorded.

## Initial test (2026-10-24)

These are initial results from an earlier image, before the release candidate.

### Test setup

| Item | Value |
| --- | --- |
| Image | `images/sdcard.img` of `radxa-zero3w_defconfig` at `main` `7359ee9` (PR #28), 385,875,968 bytes, SHA-256 `b9ad97c042969a6bc5b5442cce155f7debdb4a380349734f4b2ccc777ad9b7ed` |
| Card | Freshly written with that image, verified by two full readbacks; no stored pairing, no SSH and no test configuration |
| Board | Radxa ZERO 3W, PCB V1.12M, 1 GB RAM, no eMMC; radio AIC8800D80 over SDIO, Bluetooth on UART1 |
| Phone | Samsung Galaxy S24, SM-S921B/DS |
| Head unit | Part number 3Q0035824C, hardware 724, software 0890, media codec 1.2.0 (from its system information screen) |
| Connection | The board's USB-C 1 (OTG and power) port to the car's USB port, with a USB-C to USB-A cable (owner, 2026-10-26). Which car port was not recorded |
| `aawgd.conf` | As built (country `SE`, phone-first strategy), until the AC-7 check below |

### Results

| Spec criterion | Result | Notes |
| --- | --- | --- |
| AC-3 first use | **Passed** | The phone paired with the dongle from its Bluetooth settings. No shell, extra phone app or dongle-side step was needed. Android Auto started on the head unit |
| AC-4 cold start | **Failed: over 30 s** | The dongle reconnected automatically without re-pairing every time. Three timed starts, from the car and head unit fully off to Android Auto running: **46.3 s, 36.8 s, 37.8 s**. The spec requires under 30 s. Tracked in [#30](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/30) |
| AC-5 power reconnect | **Initial pass** | The car's off/on cycle removes USB power, and recovery was automatic. Five cycles and their timing are outstanding. The bench run in #12 also reconnected without re-pairing after power removal on four boots |
| AC-6 session | **Initial pass, 10 minutes** | Spotify audio and Google Maps navigation worked with no dropouts or audio cut-outs. Display, touch, the car's controls and voice worked. The owner noted fewer dropouts than with the Pi unit used before. The 30-minute session and log review are outstanding |
| AC-7 settings | **Passed** | `AAWG_UNIQUE_NAME_SUFFIX=Test` was set in `aawgd.conf` on the `WirelessAA` partition from a computer. After a cold start the phone listed the dongle as `WirelessAADongle-Test` and still reconnected without re-pairing |

### Startup timing

Each time includes the head unit's own boot, the board's boot from car USB power,
Bluetooth reconnection, the phone joining the AP and the USB accessory switch. In the
#12 bench runs, which used computer USB power and no head unit, the board's radio was
up 4 s after boot. `aawgd` was listening at 7 s, and the phone's TCP connection
arrived 21 s after boot. How the car-side time splits between the head unit and the
dongle has not been measured. The [final-hardware acceptance](#pi-baseline) has a Pi baseline on this car.

## Bill of materials (recorded 2026-10-26)

Cost of the tested setup against the spec's target of about SEK 400 (AC-10).
The amounts are what the owner paid, as the owner reported them on 2026-10-26.
They are not current market prices. The board arrived on 2026-10-21; the
order date was not recorded.

| Component | Product | Needed | Bought or owned | Shop | Price |
| --- | --- | --- | --- | --- | ---: |
| Board | Radxa ZERO 3W, 1 GB RAM, no eMMC (PCB V1.12M) | Yes | Bought | AliExpress | 683 kr |
| microSD card | SanDisk Ultra microSD, 32 GB | Yes | Bought | AliExpress | 159 kr |
| Data cable | USB-C to USB-A | Yes | Not in the purchase list | — | Not recorded |
| Power supply, hub or adapter | None: the board runs from the car's USB port | No | — | — | 0 kr |
| Shipping | For the AliExpress order | — | — | AliExpress | 176 kr |

VAT was not reported separately; whether it is included in the amounts above
was not recorded.

| Total | Amount | Against SEK 400 |
| --- | ---: | ---: |
| Parts (board and card) | 842 kr | +442 kr |
| Parts and shipping | 1,018 kr | +618 kr |

**Cost deviation, reviewed by the owner on 2026-10-26:** the SEK 400 target
did not cover every needed part. The owner accepts the higher cost, because the
build is still significantly cheaper than a Raspberry Pi Zero, which was the
goal to beat. No Raspberry Pi price is recorded here.
