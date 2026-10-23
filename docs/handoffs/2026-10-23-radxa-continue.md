# Radxa ZERO 3W: where to continue — 2026-10-23

Session handoff for the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
Each task follows `/spec-driven-development`: the spec goes on the issue as a comment
after owner approval, then implementation on a `feature/` branch with a PR against `main`.

## Task state

| Task | State | Notes |
| --- | --- | --- |
| #5 platform sources | Closed | [ADR-0001](../adr/0001-radxa-zero3w-platform.md) stays Proposed until #11 settles firmware terms |
| #6 Pi init relocation | Closed (PR #21) | Pi Zero 2 W smoke test passed |
| #7 kernel and boot build | Closed (PR #22) | GCC-built 6.12.114, AIC DT, U-Boot 2026.01 |
| #8 microSD image | **PR #23 open** | Owner decision: **close #8 only after the #10 boot log is recorded** |
| #9 USB accessory | Blocked by #8 | Needs PR #23 merged; physical enumeration and uevents required |
| #10 wireless driver | Unblocked (by #7) | Also delivers the deferred #8 boot log |
| #11 firmware terms | Open | [radxa-pkg/aic8800#109](https://github.com/radxa-pkg/aic8800/issues/109) had no reply |
| #12–#17 | Later stages | #14 has a comment that `build.sh` only discovers `rpi*` services |

## Next steps

1. Merge [PR #23](https://github.com/morre95/MyWirelessAndroidAutoDongle/pull/23).
2. Start #9 or #10 with `/spec-driven-development`. #10 is the shorter path to a
   network: once SSH over Wi-Fi works, capture `dmesg` and the init output from a
   boot of the #8 image, add them to the
   [microSD image handoff](2026-10-23-radxa-microsd-image.md), then close #8.
3. For #10, follow the ADR's startup contract: `CONFIG_MCU_MESSAGE=n`,
   `CONFIG_PLATFORM_ROCKCHIP=n`, `CONFIG_PLATFORM_ROCKCHIP2=n`, `CONFIG_GPIO_WAKEUP=n`,
   `AICBT_LPM_ENABLE_DEFAULT=0`; apply the AIC Debian SDIO patch series, then
   `board/radxa/zero3w/patches/aic8800/0001`–`0002`. Do not load `aic8800_btlpm`.
   The global patch dir already includes `board/radxa/zero3w/patches`, so a package
   named `aic8800` picks those patches up automatically.

## Build environment

- Build in Docker from the repository root:
  ```sh
  docker compose run --rm --no-deps bash bash -ec '
    make BR2_EXTERNAL=../aa_wireless_dongle O=output/radxa-zero3w radxa-zero3w_defconfig
    make -C output/radxa-zero3w
    cd /app && python3 tests/radxa_platform_build_test.py && python3 tests/radxa_image_test.py'
  ```
- `buildroot/output` inside the container is the Compose `output` volume, not the
  host directory of the same name. Copy images out through `/app/images/`.
  Mount host evidence into the container with `-v <host dir>:/evidence:ro`.
- `tests/radxa_aic_dtb_test.py` needs Buildroot's host Python and pylibfdt:
  `PYTHONPATH=$O/host/lib/python3.14/site-packages $O/host/bin/python3 …` with
  `RADXA_DTB_DIR` set. Its generic-DT case does not apply to this target.
- Buildroot `check-package` cannot run: `python-magic` is missing on the host and in the image.
- The ARM64 defconfig installs about 69 MB of modules. Trimming the kernel config
  needs its own task.

## Hardware state

- **Card:** the owner's only microSD card carries the radxa-zero3w image after two
  boots and several host read-write mounts. **Reflash the verified image before
  using it as evidence again.**
- **Recovery point:** the verified full-card Radxa OS backup in the ignored
  `buildroot/output/radxa-recovery/`. Its hashes are pinned in the private v4 operator.
- **No serial adapter.** The console is UART2 at 1,500,000 baud: header pin 6 GND,
  pin 8 TX, pin 10 RX, 3.3 V, VCC unconnected. A USB device `2207:350a` is the board
  in MaskROM mode, not a console. It means no bootable card was found, which
  happened once because the card was inserted upside down.
- **Power:** all tests so far used computer USB power, not car power.

## Card helpers

The session helpers are preserved in the ignored
`buildroot/output/radxa-image-20261023/tools/`. They reuse the UDisks functions of
`buildroot/output/radxa-bluetooth-test-20261022-v4/operator-v4.py`. They pin exact
image hashes and layouts, so treat them as dated one-offs and adapt the constants
for a new image. Run them as `sudo python3 <helper> <repo> [...]`; UDisks requires
admin authorization.

| Helper | Purpose |
| --- | --- |
| `radxa_flash.py` | Write the image over the Radxa OS reference layout, two readbacks |
| `radxa_reflash.py` | Rewrite a card that already carries the image, then power off the reader |
| `radxa_capture.py <repo> N` | Read-only copy of the card into `boot-N/` |
| `pi_flash.py`, `pi_restore.py`, `pi_reference_check.py` | Pi smoke-test write, Radxa OS restore, and read-only SSH check of the reference |
| `overlay_manifest.py` | Effective rootfs overlay per defconfig at a git revision |

Pitfalls seen in this session:

- **Desktop automount:** `udiskie` and the GVfs monitor mount every partition
  read-write as soon as the card appears, and they replay ext4 journals.
  - The helpers pause them only while they run, so a helper that exits early lets
    them mount the card.
  - For captures, start the helper first and plug in the reader only when it says so.
  - Never pull the reader while partitions are mounted.
  - Before writing another capture helper, make the reader power off on every exit path.
- **Reader power:** a UDisks power-off keeps the reader off until it is unplugged
  and plugged back in.
- **Bundle ownership:** create bundle directories as the normal user before running
  a helper with sudo. Otherwise later non-root writes fail.

## Privacy

Keep device and phone identifiers, card-reader serials, MAC addresses, SSIDs, Wi-Fi
passwords and LAN addresses out of commits, issues and PRs. The owner types passwords
in their own terminal; do not capture terminal streams. Confirm before writing a card
or taking any outward-facing action.
