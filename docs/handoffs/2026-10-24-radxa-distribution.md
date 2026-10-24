# Radxa ZERO 3W: Compose, CI and release packaging — 2026-10-24

Handoff for [task #14](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/14)
of the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
The approved task spec is the
[2026-10-24 comment on #14](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/14#issuecomment-6385253642).
This handoff replaces the task table and next steps of the
[radio startup handoff](2026-10-24-radxa-radio-startup.md). Its build environment,
card helpers and privacy rules still apply.

## Where things stand

- **Branch:** `feature/radxa-distribution`, in [PR #31](https://github.com/morre95/MyWirelessAndroidAutoDongle/pull/31).
- **Pushed commits:** three code commits (`0f04315`, `5e79ba9`, `b91ea71`).
- **This handoff** is committed on the branch but **not pushed yet**. The PR changes the
  workflow, so every push starts a new six-board CI run. Push it together with the
  verification results once CI run `40101754727` has finished.
- **CI:** run [`40101754727`](https://github.com/morre95/MyWirelessAndroidAutoDongle/actions/runs/40101754727)
  started about 14:35 UTC on 2026-10-24. All six build jobs were still in progress at 14:41 UTC.

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

## Next steps

1. **Check the CI run:**
   ```sh
   gh run view 40101754727 --json jobs -q '.jobs[] | "\(.name): \(.conclusion)"'
   ```
   All six `build (...)` jobs and `merge` must succeed. `release` is skipped on a PR.
   - If the Radxa job fails for lack of disk, read its "Free disk space" output and the
     failing step. Report to the owner before changing anything beyond that step.
   - If a Pi job fails, compare it with the last green run on `main`, so a flaky
     download isn't mistaken for a regression.
2. **Verify the release selection without a release.** No tag and no `gh release`:
   ```sh
   d=$(mktemp -d)
   gh run download 40101754727 -p 'WirelessAndroidAutoDongle-raspberrypi*' -D "$d/pi"
   gh run download 40101754727 -p 'WirelessAndroidAutoDongle-radxa*' -D "$d/radxa"
   find "$d" -type f | sort
   ```
   `gh run download -p` puts each artifact in its own folder, unlike the action's
   `merge-multiple`, so flatten the files before comparing. Expect exactly six `.img.xz`
   and six `.sha256` files, named `<defconfig>-sdcard.img.xz[.sha256]`, with nothing from
   `-all`. Run `sha256sum -c` on each `.sha256` in its own folder. Record artifact sizes.
3. Decompress `radxa-zero3w-sdcard.img.xz`, then run `RADXA_OUTPUT`-independent checks
   on it, for example its size and partition table against `radxa_image_test.py`'s
   expectations.
4. Add the CI run, artifact list, sizes and checksum results to this handoff. Push the
   handoff with them, then report to the owner that PR #31 is ready to merge.
5. After the merge: #14 closes through the PR. Remaining tasks are #15 (docs and cost),
   #16 (physical acceptance and Pi regression) and #17 (public release check).

## Task state

| Task | State | Notes |
| --- | --- | --- |
| #14 Compose, CI, release | PR #31 open; CI running | This handoff |
| #15 Documentation and cost | Open | README support claims belong here or in #17 |
| #16 Physical acceptance and Pi regression | Open | AC-4's 30 s limit is unchanged in the spec; the owner closed #30 (head-unit boot time) |
| #17 Public release check | Open | Needs a real `v*` release, after #16 |
