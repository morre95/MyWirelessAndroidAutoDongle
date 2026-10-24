# Radxa ZERO 3W: redistributable AIC firmware — 2026-10-24

Handoff for [task #11](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/11)
of the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
The approved task spec is the 2026-10-24 comment on #11. This handoff replaces the task
table and next steps of the [USB accessory handoff](2026-10-24-radxa-usb-accessory.md).
The build environment, hardware state, card helpers and privacy rules of the
[2026-10-23 continue point](2026-10-23-radxa-continue.md) still apply.

## What changed

- **New package `aic8800-firmware`:** the four AIC8800D80 U02 v6.9.1.1 files and
  `LICENSE.aic` from linux-firmware tag `20261019` (GitLab project, same commit as
  git.kernel.org), each hash-checked. They are installed in
  `/lib/firmware/aic8800_fw/SDIO/aic8800D80/` with the license beside them.
- **`aic8800.mk`:** also installs `aic_userconfig_8800d80.txt` from the pinned AIC source.
- **Not shipped:** `fw_patch_8800d80_u02_ext0.bin`, because the v6.9.1.1 patch table
  declares no ext patch, and every other Radxa-packaged binary.
- **Tests:** a new `tests/radxa_wireless_firmware_test.py`. #10's "no firmware yet"
  test was removed, since this task makes it obsolete.
- **`checks/aic-firmware-smoke-test.conf`:** the test-only `aawgd.conf` block. Never ship it.
- **ADR-0001:** a new section, "Redistributable firmware baseline: 2026-10-24", which
  changes the firmware baseline explicitly. Promoting the ADR to Accepted is left to
  the owner.

## Verification

```sh
docker compose run --rm --no-deps bash bash -ec '
  make BR2_EXTERNAL=../aa_wireless_dongle O=output/radxa-zero3w radxa-zero3w_defconfig
  make -C output/radxa-zero3w
  make -C output/radxa-zero3w legal-info
  cd /app && for t in radxa_wireless_firmware_test radxa_wireless_driver_test \
      radxa_platform_build_test radxa_image_test; do python3 tests/$t.py; done'
```

| Check | Result |
| --- | --- |
| `radxa_wireless_firmware_test.py` | 7 passed |
| `radxa_wireless_driver_test.py` | 13 passed |
| `radxa_platform_build_test.py` | 12 passed |
| `radxa_image_test.py` | 12 passed |
| `legal-info` | `aic8800-firmware`, `20261019`, `LicenseRef-LICENSE.aic`, sources and license collected |

`legal-info` also prints "No hash found" for the `linux` package's license files
(`COPYING`, `LICENSES/…`). These come from the custom 6.12.114 kernel added in #7, are
non-fatal, and are not changed here.

## Smoke test on the board

| Item | Value |
| --- | --- |
| Production image | `cd5cd1eb3ee97cd34236ce4915933a656ffeb46f449dbf81b47342b23ea96d55` |
| Test card image | `74998ed68677cdc0067c30d3b6c460d80e2b8f6b1406c932264e08778d211f07`, differs only in the FAT partition |
| Card write | Verified by two readbacks |
| Boot | One boot from computer USB power; card copy `f45b5079…df42a2` |
| `load.txt` | Both `modprobe` calls returned 0, between uptime 61.26 s and 63.41 s |

Result: the BT ADID/patch and `fmacfw` uploads succeeded, the userconfig loaded, the
firmware reported `V1.0.7`, and `wlan0` appeared at 18.00 dBm with AP mode on both
bands. The ADR section has the details, plus the known `bus down` and
permissive-regulatory messages.

Board log SHA-256 (private bundle, `boot-1/persist-aic-test/boot-1/`):

| File | SHA-256 |
| --- | --- |
| `load.txt` | `cd576eeee6a81e03b07eb3f464d0478e781f81603d1f342f7831981991720737` |
| `dmesg.txt` | `1cf3c52dc59b3bd828819a99fb0257cec30d085e77fa4d21b57fa70769446571` |
| `messages.txt` | `825519e89e0dffa8c4be23b14f640daab7fac3182ece62eee7c71871164c65ca` |
| `radio.txt` | `4f053395f690aa6ebbc44104288534eb5d2160e5241c941c1c15d376236f112b` |

`dmesg.txt`, `messages.txt` and `radio.txt` contain the board's Wi-Fi MAC address, so
they stay in the ignored bundle `buildroot/output/radxa-aic-20261024/`. The bundle also
holds the dated flash and capture helpers and the card copy.

## Card state

The card holds the **AIC smoke-test** image after one boot. It loads the radio modules
60 s after every boot. Reflash before using the card as evidence again. The Radxa OS
backup remains the recovery point.

## Task state

| Task | State | Notes |
| --- | --- | --- |
| #11 firmware | Implemented on `feature/radxa-wireless-firmware` | This handoff; PR to `main` next |
| #12 Wi-Fi AP and Bluetooth | Unblocked once #11 merges | Owes #8's boot log and #9's bidirectional transport; follow up the regulatory domain and `bus down` |
| #13 first-use flow | Blocked by #12 | |
| #14 Compose, CI, release | Open | Firmware is redistributable; `build.sh` only discovers `rpi*` services |

## Next steps

1. Open, review and merge the #11 PR.
2. Decide whether ADR-0001 can move to Accepted.
3. #12: load the modules synchronously in a startup script, then follow the ADR
   contract: run `aic-firmware-ready.sh`, then a bounded `aic-hci-reset /dev/ttyS1`,
   then attach the UART, then start BlueZ. Then bring up the AP with the configured
   country code and record #8's boot log over SSH.
