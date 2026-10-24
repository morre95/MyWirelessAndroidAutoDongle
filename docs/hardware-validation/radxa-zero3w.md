# Radxa ZERO 3W hardware validation

First-use and reconnection record for [task #13](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/13)
of the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
These are initial results from the candidate image. The final-hardware task reruns the
full acceptance matrix on the exact release image.

## Test setup (2026-10-24)

| Item | Value |
| --- | --- |
| Image | `images/sdcard.img` of `radxa-zero3w_defconfig` at `main` `7359ee9` (PR #28), 385,875,968 bytes, SHA-256 `b9ad97c042969a6bc5b5442cce155f7debdb4a380349734f4b2ccc777ad9b7ed` |
| Card | Freshly written with that image, verified by two full readbacks; no stored pairing, no SSH and no test configuration |
| Board | Radxa ZERO 3W, PCB V1.12M, 1 GB RAM, no eMMC; radio AIC8800D80 over SDIO, Bluetooth on UART1 |
| Phone | Samsung Galaxy S24, SM-S921B/DS |
| Head unit | Part number 3Q0035824C, hardware 724, software 0890, media codec 1.2.0 (from its system information screen) |
| Connection | The board's USB data/power port to the car's USB port. The cable and which car port were not recorded |
| `aawgd.conf` | Unchanged from the image (country `SE`, phone-first strategy) |

## Results

| Spec criterion | Result | Notes |
| --- | --- | --- |
| AC-3 first use | **Passed** | The phone paired with the dongle from its Bluetooth settings. No shell, extra phone app or dongle-side step was needed. Android Auto started on the head unit |
| AC-4 cold start | **Initial pass, not timed** | After turning the car off and on, the dongle reconnected automatically without re-pairing. Time to usable Android Auto was not measured; the 10-start timing matrix is outstanding |
| AC-5 power reconnect | **Initial pass** | The car's off/on cycle removes USB power, and recovery was automatic. Five cycles and their timing are outstanding. The bench run in #12 also reconnected without re-pairing after power removal on four boots |
| AC-6 session | **Initial pass, 10 minutes** | Spotify audio and Google Maps navigation worked with no dropouts or audio cut-outs. Display, touch, the car's controls and voice worked. The owner noted fewer dropouts than with the Pi unit used before. The 30-minute session and log review are outstanding |
| AC-7 settings | **Not tested** | `aawgd.conf` was not edited. Pairing persistence across power removal is shown above |

No failure was found, so no fix issue was opened.

## Outstanding for the final-hardware task

- 10 timed cold starts (AC-4) and 5 timed power reconnects (AC-5).
- A 30-minute session with logs (AC-6).
- A settings change through `aawgd.conf` on the `WirelessAA` partition that survives a cold start (AC-7).
- Recording the cable and car USB port.
