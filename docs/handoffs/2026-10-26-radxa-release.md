# Radxa ZERO 3W: public release check — 2026-10-26

Handoff for [task #17](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/17)
of the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
This handoff replaces the task table of the
[final-hardware handoff](2026-10-26-radxa-final-hardware.md).

## What happened

1. PR #35 replaced the tag-triggered rebuild with a manually started `Release`
   workflow, so a release can carry the exact tested files.
2. That workflow failed twice with `HTTP 403: Resource not accessible by integration`
   when creating the release, the second time with the tag already pushed. The
   cause is not known. The owner chose not to track it in an issue.
3. The owner pushed `v0.2.0` on `b86bf48` and cancelled the rebuild it started
   (all jobs cancelled before any release step ran), then created the release by
   hand from the six candidate files of run 40103814333.
4. The Radxa section of the release notes was added after owner approval.

## Verified

| Check | Result |
| --- | --- |
| Release | [v0.2.0](https://github.com/morre95/MyWirelessAndroidAutoDongle/releases/tag/v0.2.0), published, latest, tag on `b86bf48`, 12 assets |
| Anonymous download | The Radxa and Pi Zero 2 W assets pass `sha256sum -c` |
| Exact image | The Radxa asset decompresses to `d79c85e5…587a4e`, the image tested in #16 |
| Manual release steps in `BUILDING.md` | Download and checksum commands run against run 40103814333: 6 artifacts, 12 files, all OK |

## What changed

Docs only, on branch `docs/radxa-release`.

- **`README.md`:** Radxa ZERO 3W moves from "In testing" to the supported list, with the v0.2.0 link.
- **`docs/hardware-validation/radxa-zero3w.md`:** the release result (AC-2) with URL and checksums.
- **`BUILDING.md`:** the manual release steps used for v0.2.0, and the workflow's 403.

## Task state

| Task | State | Notes |
| --- | --- | --- |
| #17 Public release check | PR open | This handoff |
| #4 Radxa support spec | All tasks done once this merges | The owner closes it |
