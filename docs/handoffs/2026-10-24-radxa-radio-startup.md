# Radxa ZERO 3W: radio startup and pairing — 2026-10-24

Handoff for [task #12](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/12)
of the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
The approved task spec is the
[2026-10-24 comment on #12](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/12#issuecomment-6383646977).
This handoff replaces the task table and next steps of the
[firmware handoff](2026-10-24-radxa-wireless-firmware.md). The build environment, card
helpers and privacy rules of the [2026-10-23 continue point](2026-10-23-radxa-continue.md)
still apply.

## What changed

- **New package `aic8800-startup`:** `aic-firmware-ready.sh` and `aic-hci-reset.c`
  moved here from `checks/`, plus the init script `S38radio`. The diagnostic
  generators and tests now read the helpers from the package.
- **`S38radio`:** waits for the SDIO radio, loads `aic8800_fdrv custregd=0`, polls
  firmware readiness, loads `hci_uart`, resets the controller, starts `btattach` and
  waits for `hci0`. Each stage has a time limit, stops on failure and logs what is missing.
- **Regulatory:** `custregd=0` lets the kernel regulatory database and
  `AAWG_COUNTRY_CODE` apply instead of the driver's permissive rules.
- **Access point:** the board overlay's `hostapd.conf.in` uses 5 GHz channel 36 with
  802.11ac, like Pi 4/5.
- **Kernel patch `0006`:** backports upstream `5bd0dec150f5` ("net: call
  getsockopt_iter if available"). Linux 6.12.114 lacks it, so every L2CAP getsockopt
  returned `EOPNOTSUPP` and BlueZ never registered the adapter. This, not `BT_LE`, was
  the cause of the 2026-10-23 diagnostic failure.
- **`checks/aoa-host-test.py --version-exchange`:** after the AOA switch it sends an
  Android Auto version request on bulk OUT and requires the phone's response on bulk IN.
- **`checks/radio-startup-test.conf`:** the test-only `aawgd.conf` block. It enables
  SSH and saves radio state to `persist`. Never ship it.
- **Tests:** new `tests/radxa_radio_startup_test.py` and `tests/radxa_aoa_host_test.py`.
  `radxa_platform_build_test.py` gained the patch 0006 check. `radxa_wireless_driver_test.py`
  now really checks all five Pi defconfigs; its `rpi*` glob matched none.
- **ADR-0001:** the new section "Radio startup and pairing: 2026-10-24", and corrections
  where it blamed `BT_LE` for the adapter failure.

## Verification

```sh
docker compose run --rm --no-deps bash bash -ec '
  make BR2_EXTERNAL=../aa_wireless_dongle O=output/radxa-zero3w radxa-zero3w_defconfig
  make -C output/radxa-zero3w
  cd /app && for t in radxa_radio_startup_test radxa_firmware_ready_test radxa_wireless_firmware_test \
      radxa_wireless_driver_test radxa_platform_build_test radxa_image_test radxa_aoa_host_test; do
    python3 tests/$t.py; done'
cc -std=c11 -Wall -Wextra -Werror -Wconversion -Wshadow \
    aa_wireless_dongle/package/aic8800-startup/src/aic-hci-reset.c -o /tmp/radxa-hci-reset
python3 tests/radxa_hci_reset_test.py
```

| Check | Result |
| --- | --- |
| `radxa_radio_startup_test.py` | 15 passed; its 9 script cases also pass under the target BusyBox ash in qemu |
| `radxa_firmware_ready_test.py` | 17 passed |
| `radxa_hci_reset_test.py` | passed, built from the package path |
| `radxa_wireless_firmware_test.py` | 7 passed |
| `radxa_wireless_driver_test.py` | 13 passed |
| `radxa_platform_build_test.py` | 13 passed; the patch 0006 check failed before the kernel rebuild |
| `radxa_image_test.py` | 12 passed |
| `radxa_aoa_host_test.py` | 4 passed |
| `proxy_diagnostics_test.cpp` | passed |
| `radxa_radio_test_test.py`, `radxa_bluetooth_image_test.py`, `radxa_startup_test.py` | pass on the host, where the private diagnostic bundles are; in the Docker volume `radxa_radio_test_test.py` has 5 errors for missing bundles, the same as on `main` |

## Board run

| Item | Value |
| --- | --- |
| Production image | `b9ad97c042969a6bc5b5442cce155f7debdb4a380349734f4b2ccc777ad9b7ed` |
| Test card image | `9e30246595af0c82dda4f3cdb12bb2fdf51ab9e9e117d80ea09928e53a1c5ea5`, differs only in the FAT partition |
| Card write | Verified by two readbacks; it overwrote the first #12 test card |
| Power | Computer USB; the PC acted as headunit |

An earlier test card without patch 0006 (`ab16aaa7…`, production `21fb5a1f…`) booted
once. `S38radio` passed every stage and the AP came up, but BlueZ failed adapter
registration. That boot found the kernel fault.

With patch 0006 the card booted four times, including power removal between boots:

1. **Boot 1:** the phone paired with no prompt on the dongle. `aawgd` sent the Wi-Fi
   credentials, the phone joined the AP and connected over TCP, and the headunit
   tool's version request and the phone's response (1.7, status 0) crossed
   `/dev/usb_accessory`. `aawgd`'s proxy stats show 10 bytes USB→TCP and 12 bytes
   TCP→USB.
2. **Later boots after power removal:** the phone reconnected from the stored pairing
   without a prompt, and the version exchange passed again. `aawgd` logs
   `Found 1 bluetooth devices` 7 s after boot.

`iw reg get` reported `country SE: DFS-ETSI`. The AP ran on channel 36 at 20 MHz and
18 dBm. Without a real headunit the phone ends each session about 10 s after the
version exchange, and `aawgd` reconnects by itself.

Evidence SHA-256 (private bundle `buildroot/output/radxa-radio-20261024/`):

| File | SHA-256 |
| --- | --- |
| `image1-boot-1-ssh/messages.txt` (BlueZ failure) | `c305a8877d4251b2b898cb49ab0981de9c7f177e14dcc65973538c25550343f5` |
| `image2-boot-1-ssh/dmesg.txt` | `b8b5207d0f7ba626f1e1b1a569fbc578b16ce38083646f68c03217ec2b12a739` |
| `image2-boot-1-ssh/messages.txt` | `0efe6c99d4b6e0cc4da32ac42afe132793590bb81aff590c8089f719245348cf` |
| `image2-boot-1-ssh/state.txt` | `ad41a818c8380dddc0f35d1d946fc5f76fb7d8ae755f4ecdc0fd486f46e32c5b` |
| `image2-boot-4-ssh/messages.txt` | `1700ba176ca1dd373cb0fed0b2db8c7e9e4d7e8cf1b7f6c1812db791a31638a9` |
| `aoa-144608.jsonl` (headunit tool, after power removal) | `c712ace19a13119b018c959055ae846759e88bd43db4519e09f391aead9c830e` |
| `aoa-145359.jsonl` (headunit tool, card boot 4) | `c647c814adbe25fa05b4409a95a546fbaaa97919a71a88b744b7b26fc42a283d` |

The first boot's headunit log was not kept; its output is in the session transcript
and matches the proxy stats above. The logs contain the board's and the phone's
addresses, so they stay in the bundle. The bundle also holds the dated flash and
capture helpers and the AP password, which must never be committed.

#8's boot log comes from `image2-boot-1-ssh`; see the
[microSD image handoff](2026-10-23-radxa-microsd-image.md#boot-log-2026-10-24).

## Not established

- A real headunit and a full Android Auto session (#13).
- The spec's repeated-start, power-reconnect, connection-time and 30-minute session
  acceptance.
- Sustained traffic, other channels and widths, and car USB power.

## Card state

The card holds the patch-0006 radio test image after four boots. It enables SSH and has
a test AP password. Reflash before using the card as evidence again. The Radxa OS
backup remains the recovery point.

## Task state

| Task | State | Notes |
| --- | --- | --- |
| #12 Wi-Fi AP and Bluetooth | Implemented on `feature/radxa-radio-startup` | This handoff; PR to `main` next |
| #8 microSD image | Boot log delivered here | Close after the #12 PR merges |
| #13 first-use flow | Unblocked once #12 merges | Needs a real headunit |
| #14 Compose, CI, release | Open | `build.sh` only discovers `rpi*` services |

## Next steps

1. Review and merge the #12 PR, then close #12 and #8.
2. Decide whether ADR-0001 can move to Accepted.
3. Drop kernel patch `0006` when the pinned kernel contains upstream `5bd0dec150f5`.
