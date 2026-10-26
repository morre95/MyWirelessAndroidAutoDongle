# Radxa ZERO 3W: final-hardware acceptance — 2026-10-26

Handoff for [task #16](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/16)
of the [Radxa support spec](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/4).
This handoff replaces the task table of the
[documentation handoff](2026-10-26-radxa-documentation.md).

## What changed

Docs only, on branch `docs/radxa-final-hardware`.

- **`docs/hardware-validation/radxa-zero3w.md`:** the final-hardware results on the
  release candidate, with every timing, the Pi baseline and the evidence limits.
  The #13 record is kept below it as the initial test.
- **`README.md`:** the Radxa entry says physical acceptance passed. The limitations
  give the new cold-start times and the session result.

## Owner decisions (2026-10-26)

1. AC-4 keeps its 30 s threshold. A Pi is timed on the same car as a baseline
   ([decision on #16](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/16#issuecomment-6419654882)).
2. No logs are collected for AC-5 and AC-6; they rest on in-car observation
   ([decision on #16](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/16#issuecomment-6423749720)).
3. The first cold-start series, with one start at exactly 30 s, was rerun in full.

## Verified

| Check | Result |
| --- | --- |
| Candidate CI run 40103814333 | All six board builds and `merge` succeeded; every `.sha256` verifies |
| Host tests | The proxy C++ test, `tests/build_sh_test.py` and all 16 `tests/radxa_*_test.py` pass |
| Car tests | AC-3 to AC-8 as recorded by the owner; see the validation record |
| AC-9 | The Radxa overlay holds only `etc/fstab` and `etc/hostapd.conf.in`; `package/aawg/` has no board-specific code |

## Gaps

- No logs for AC-5 and AC-6 (owner decision 2 above).
- Times are stopwatch readings in whole seconds.
- The cause of the faster cold starts compared with the initial test (37–46 s) was
  not measured.

## Task state

| Task | State | Notes |
| --- | --- | --- |
| #16 Physical acceptance and Pi regression | PR open | This handoff |
| #17 Public release check | Open | Needs a real `v*` release, which the owner creates. It also switches the README from "in testing" to supported |
