# Radxa ZERO 3W: Compose, CI and release packaging — 2026-10-24

Handoff for [task #14](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/14)
of the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
The approved task spec is the
[2026-10-24 comment on #14](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/14#issuecomment-6385253642).
This handoff replaces the task table and next steps of the
[radio startup handoff](2026-10-24-radxa-radio-startup.md). Its build environment,
card helpers and privacy rules still apply.

## Where things stand

- **Merged:** [PR #31](https://github.com/morre95/MyWirelessAndroidAutoDongle/pull/31)
  merged to `main` as `b86bf48` at 14:44 UTC on 2026-10-24, with three code commits
  (`0f04315`, `5e79ba9`, `b91ea71`).
- **CI:** PR run [`40101754727`](https://github.com/morre95/MyWirelessAndroidAutoDongle/actions/runs/40101754727)
  finished at 16:03 UTC: all six `build (...)` jobs and `merge` succeeded, `release`
  skipped. The `main` push run `40103814333` for `b86bf48` also succeeded.
- **Issue:** PR #31 had no closing keyword, so #14 stayed open after the merge.
- **This handoff** reaches `main` through its own docs PR, since the feature branch was
  already merged.

## What changed

- **Compose:** new `radxa-zero3w` service (`BOARD_NAME=radxa-zero3w`), writing
  `images/sdcard-radxa-zero3w.img`. Documented in `BUILDING.md`.
- **`build.sh`:**
  - Boards are the Compose services named `rpi*` or `radxa*` (owner decision: a
    prefix list).
  - Adds the label "Radxa ZERO 3W" and a wider help column.
  - The error now reads "defines no rpi* or radxa* board services".
- **`tests/build_sh_test.py`:** runs the real `build.sh` with a fake `docker`; 5 tests.
- **`.github/workflows/build.yml`:**
  - `radxa-zero3w` is in the matrix.
  - A "Free disk space" step runs for that job only (owner approved). The local
    Radxa build tree is about 14 GB.
  - Every job uploads `<defconfig>-sdcard.img.xz` and `<defconfig>-sdcard.img.xz.sha256`.
  - The release job downloads `WirelessAndroidAutoDongle-raspberrypi*` and
    `WirelessAndroidAutoDongle-radxa*`, never `-all`, and publishes
    `images/*.img.xz images/*.sha256`.
- **Owner decisions:** `.sha256` files for all six boards; README support claims wait
  for #15 to #17.

## Verified so far

| Check | Result |
| --- | --- |
| `python3 tests/build_sh_test.py` | 5 passed; it failed before the change |
| `./build.sh --help` | Lists `radxa-zero3w` and the five Pi boards, with labels |
| `docker compose config --services` | Includes `radxa-zero3w`; Pi services unchanged |
| `docker compose run --rm --build radxa-zero3w` | Exit 0; wrote `images/sdcard-radxa-zero3w.img` (385,875,968 bytes) |
| Radxa image tests against that build | `radxa_image_test`, `radxa_platform_build_test`, `radxa_radio_startup_test`, `radxa_wireless_driver_test`, `radxa_wireless_firmware_test` pass |

The local Compose build was incremental: the build tree from #12 was already complete, so
it took 10 s. Image bytes differ between builds, because genimage output is not
reproducible. CI does the clean build. The #11 image that sat at
`images/sdcard-radxa-zero3w.img` was renamed to `images/sdcard-radxa-zero3w-11.img`.

## Release selection (run `40101754727`, 2026-10-26)

No tag and no `gh release`. The two release patterns downloaded exactly six images and
six checksums, nothing from `-all`. `sha256sum -c` passed for every file in its own folder.

```sh
gh run download 40101754727 -p 'WirelessAndroidAutoDongle-raspberrypi*' -D "$d/pi"
gh run download 40101754727 -p 'WirelessAndroidAutoDongle-radxa*' -D "$d/radxa"
```

| File | Bytes | SHA-256 |
| --- | --- | --- |
| `raspberrypi0w-sdcard.img.xz` | 35,916,816 | `d102a13c6a4df5afad116c1a0951f019d5164288a333c8acf674d8e0fe5a67e7` |
| `raspberrypizero2w-sdcard.img.xz` | 36,564,428 | `b2b190cc062adbb1c670354019261c2960d337e2eb8c974fe0c526cae12d8424` |
| `raspberrypi3a-sdcard.img.xz` | 36,573,184 | `6b377445762b991da92a6d5acbcd610ad5d6f99208e587cadaf3e520332f2009` |
| `raspberrypi4-sdcard.img.xz` | 38,163,760 | `0fd7220747142d9ce187969a9dc25403bc46221df09ed9c5030861b4425088b0` |
| `raspberrypi5-sdcard.img.xz` | 38,574,616 | `340c56d5f1b20d0f641744d65cb503e013d4559995bcf295bf5f9b31ef6c7012` |
| `radxa-zero3w-sdcard.img.xz` | 33,180,428 | `1c08fdc644cec1844eacaadbb2788c21d60462a7a9a51a469dbab518944b41f3` |

## CI Radxa image

`radxa-zero3w-sdcard.img.xz` decompresses to 385,875,968 bytes, the same size as the local
Compose build. Its partition table matches that build: bootable FAT32 (`0x0C`) at 16 MiB,
64 MiB; ext4 rootfs at 80 MiB, 256 MiB; ext4 persist at 336 MiB, 32 MiB.

`radxa_image_test.py` ran in the build container with `RADXA_OUTPUT` pointing at a tree
made from the CI image: its three partitions cut out with `dd`, the DTB copied from its
boot partition, and `host/` and `u-boot-rockchip.bin` from the local Compose build.
Result: 11 of 12 passed. Partition contents compare against themselves here, so
`test_partitions_hold_the_built_filesystems` proves only the partition sizes.

`test_bootloader_is_raw_at_sector_64_before_the_first_partition` failed, as expected for a
different build. 112 of 9,632,768 bytes differ from the local bootloader. The only
differing strings are the U-Boot and SPL build stamps (`2026.01`, Oct 24 14:59:01 in CI
against Oct 23 20:21:48 locally). The DTB is byte-identical to the local build.

## Next steps

1. The owner closes #14, or lets the docs PR that carries this handoff close it.
2. Remaining tasks are #15 (docs and cost), #16 (physical acceptance and Pi regression)
   and #17 (public release check).

## Task state

| Task | State | Notes |
| --- | --- | --- |
| #14 Compose, CI, release | PR #31 merged; verified | This handoff |
| #15 Documentation and cost | Open | README support claims belong here or in #17 |
| #16 Physical acceptance and Pi regression | Open | AC-4's 30 s limit is unchanged in the spec; the owner closed #30 (head-unit boot time) |
| #17 Public release check | Open | Needs a real `v*` release, after #16 |
