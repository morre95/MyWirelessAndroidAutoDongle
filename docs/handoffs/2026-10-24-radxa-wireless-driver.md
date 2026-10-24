# Radxa ZERO 3W: AIC driver package — 2026-10-24

Handoff for [task #10](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/10)
of the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
The approved task spec is the 2026-10-24 comment on #10. This handoff replaces the
task table and next steps of the [2026-10-23 continue point](2026-10-23-radxa-continue.md).
Its build environment, hardware state, card helpers and privacy rules still apply.

## What changed

- New external package `aa_wireless_dongle/package/aic8800/`, selected by
  `configs/radxa-zero3w_defconfig`. It builds `aic8800_bsp` and `aic8800_fdrv` from
  the AIC commit pinned in [ADR-0001](../adr/0001-radxa-zero3w-platform.md) and
  skips `aic8800_btlpm`.
- Patch order: Radxa's `debian/patches/series` (pre-patch hook), then
  `board/radxa/zero3w/patches/aic8800/0001`–`0002` (global patch dir). The resulting
  `src/SDIO` tree is identical to the ADR's `git apply --include` method.
- No firmware, module loading, init script or kernel-config change. The board
  `linux.fragment` already carries the Wi-Fi and Bluetooth prerequisites.
- ADR-0001 has a new section, "AIC driver package: 2026-10-24", with module hashes
  and the license declaration.

## Verification

All passed on 2026-10-24, run from the repository root:

```sh
docker compose run --rm --no-deps bash bash -ec '
  make BR2_EXTERNAL=../aa_wireless_dongle O=output/radxa-zero3w radxa-zero3w_defconfig
  make -C output/radxa-zero3w
  cd /app && python3 tests/radxa_wireless_driver_test.py \
    && python3 tests/radxa_platform_build_test.py && python3 tests/radxa_image_test.py'
```

| Check | Result |
| --- | --- |
| `tests/radxa_wireless_driver_test.py` | 14 passed |
| `tests/radxa_platform_build_test.py` | 11 passed |
| `tests/radxa_image_test.py` | 12 passed |
| Proxy diagnostics test (`AUDIO-TROUBLESHOOTING.md` command) | Passed |
| `raspberrypi0w`, `raspberrypizero2w`, `raspberrypi3a`, `raspberrypi4` defconfigs | `# BR2_PACKAGE_AIC8800 is not set` |

The driver test reads modules with Buildroot's `host/bin/modinfo`, because the
container has no `modinfo` of its own. The new image's SHA-256 is
`09b03613c2e33a5cace64979505eaf882d5c36980a00c0816014e9ca8ae9b59a` (one local
build). It has not been flashed or booted; #10 needs no hardware check.

## Task state

| Task | State | Notes |
| --- | --- | --- |
| #8 microSD image | Open, PR #23 merged | Owner decision 2026-10-24: the boot log moves to #12 |
| #9 USB accessory | Unblocked | Needs physical enumeration and uevents |
| #10 wireless driver | Implemented on `feature/radxa-wireless-driver` | This handoff; PR to `main` next |
| #11 firmware terms | Open | [radxa-pkg/aic8800#109](https://github.com/radxa-pkg/aic8800/issues/109) had no reply |
| #12 Wi-Fi AP and Bluetooth | Blocked by #8, #11; also needs #10's modules | Also delivers the #8 boot log over SSH. #8's image is merged, so only its boot-log condition waits on #12 |

## Next steps

1. Open, review and merge the #10 PR.
2. #11: install the six D80 firmware files once their terms are settled. The BSP
   looks for them in `/lib/firmware/aic8800_fw/SDIO/aic8800D80`.
3. #12: load `aic8800_bsp`/`aic8800_fdrv` synchronously, then follow the ADR startup
   contract: run `aic-firmware-ready.sh`, then a bounded `aic-hci-reset /dev/ttyS1`,
   then attach the UART, then start BlueZ. Once SSH over Wi-Fi works, capture `dmesg`
   and the init output from a boot of the image, add them to the
   [microSD image handoff](2026-10-23-radxa-microsd-image.md), and close #8.
