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
| `aawgd.conf` | As built (country `SE`, phone-first strategy), until the AC-7 check below |

## Results

| Spec criterion | Result | Notes |
| --- | --- | --- |
| AC-3 first use | **Passed** | The phone paired with the dongle from its Bluetooth settings. No shell, extra phone app or dongle-side step was needed. Android Auto started on the head unit |
| AC-4 cold start | **Failed: over 30 s** | The dongle reconnected automatically without re-pairing every time. Three timed starts, from the car and head unit fully off to Android Auto running: **46.3 s, 36.8 s, 37.8 s**. The spec requires under 30 s. Tracked in [#30](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/30) |
| AC-5 power reconnect | **Initial pass** | The car's off/on cycle removes USB power, and recovery was automatic. Five cycles and their timing are outstanding. The bench run in #12 also reconnected without re-pairing after power removal on four boots |
| AC-6 session | **Initial pass, 10 minutes** | Spotify audio and Google Maps navigation worked with no dropouts or audio cut-outs. Display, touch, the car's controls and voice worked. The owner noted fewer dropouts than with the Pi unit used before. The 30-minute session and log review are outstanding |
| AC-7 settings | **Passed** | `AAWG_UNIQUE_NAME_SUFFIX=Test` was set in `aawgd.conf` on the `WirelessAA` partition from a computer. After a cold start the phone listed the dongle as `WirelessAADongle-Test` and still reconnected without re-pairing |

## Startup timing

Each time includes the head unit's own boot, the board's boot from car USB power,
Bluetooth reconnection, the phone joining the AP and the USB accessory switch. In the
#12 bench runs, which used computer USB power and no head unit, the board's radio was
up 4 s after boot. `aawgd` was listening at 7 s, and the phone's TCP connection
arrived 21 s after boot. How the car-side time splits between the head unit and the
dongle has not been measured. No Pi baseline time on this car is recorded.

## Outstanding for the final-hardware task

- Startup under 30 s (AC-4), then 10 timed cold starts and 5 timed power reconnects (AC-5).
- A 30-minute session with logs (AC-6).
- Recording the cable and car USB port.
