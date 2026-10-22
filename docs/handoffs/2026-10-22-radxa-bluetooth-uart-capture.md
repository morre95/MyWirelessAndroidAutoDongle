# Radxa Bluetooth UART failure capture — 2026-10-22

## V3 result and recovery checkpoint

The owner confirmed Radxa power disconnected and the card back in the reader
at about **19:18:13 UTC**, after the requested twelve-minute minimum. Exact
physical power-on/off timings were not independently measured. Fresh identity
matched the selected reader/capacity and both v3 filesystem UUIDs below.

All **26 captured files** were copied from a read-only log mount and individually
SHA-256-verified into
`buildroot/output/radxa-bluetooth-test-20261022-v3/evidence-20261022T191827Z/`.
Private `evidence.json` and `analysis.json` preserve provenance and findings.
There is one boot directory; embedded inputs match the v3 manifest.

Firmware readiness and HCI Reset succeeded. The attachment failure snapshot
completed with exit/status zero and shows **hci0 registered**, with hciattach
in state **S**, waiting in `do_sys_poll` / `__arm64_sys_ppoll` (syscall 73).
This establishes local H4/line-discipline/controller registration, not working
Bluetooth command/event transport, a powered BlueZ adapter or pairing.
No D-state attachment task was observed. BlueZ/pairing and final capture files
are absent, and `cleanup-result.txt` is empty.

The concrete diagnostic defect is now reproduced: the selected static BusyBox
has both `CONFIG_KILL=n` and `CONFIG_ASH_JOB_CONTROL=n`. Its ash has no kill
builtin, and none of the three packed archives installs a kill command.
Running that exact ARM64 shell with an isolated PATH returns
`kill: not found` / 127. Consequently `alive()` falsely rejects the live
attachment, TERM/KILL calls do nothing, and `finished()` mistakes a failed
probe for an exited child before blocking in `wait`. The captured state matches
that path. Earlier host and QEMU stage fixtures inherited host PATH, masking
this missing dependency. The empty attachment log is compatible with buffered
stdout and does not establish an initialization hang.

The full postboot 234,881,024-byte test range is preserved as
`postboot-card-20261022T192023Z.img` in the v3 bundle, SHA-256
`7b50f21bde6c5967f10d3a11a64c2132a8ed9909d1f253aae9d8b145bb199561`.
Full reference restoration started at **19:20:25 UTC** and is **in progress**.
Monitor `reference-restore-20261022T192023Z.json` in the v3 bundle; do not move
the card or start another writer until restoration/readback finishes. Runtime
reference recovery has not yet been verified for this run.

A v4 image fixing the process-control dependency has been built locally and
reviewed; source changes are saved in local commit `123f1fb`. Selected candidate:
`buildroot/output/radxa-bluetooth-test-20261022-v4/radxa-bluetooth-test.img`,
234,881,024 bytes, SHA-256
`4a0186870d04bbca2bf73ded9b20f7ab0926723123c9e2820e4d4ea9603776ce`.
It has not been written or physically tested. Forty-one host checks and
twenty-two ARM64/QEMU helper/stage checks pass, including an isolated PATH with
no host kill, actual child signal delivery and packed-executable probes. No
required review findings remain; an ESRCH-result mutation is detected. These
checks do not establish physical Bluetooth acceptance. Complete this recovery
before any further hardware test. The full v4 recipe and limits are at the top
of [bluetooth-test.md](../../aa_wireless_dongle/board/radxa/zero3w/checks/bluetooth-test.md).

## Historical written-card/start checkpoint

The owner authorized the next diagnostic after the
[v2 attachment failure and verified recovery](2026-10-22-radxa-bluetooth-test.md).
**The card now contains the written and readback-verified v3 diagnostic.**
The owner reported connecting Radxa power; that report was recorded at
**19:03:59 UTC / 21:03:59 Europe/Stockholm**. Keep power connected for at least
twelve minutes from that report: **19:15:59 UTC / 21:15:59 local** before
disconnecting power and moving the card. One start was requested, with the
phone's Bluetooth settings open. The owner reports that the test device is
not visible in the phone Bluetooth scan; no discovery/pairing success is
observed. LED behavior has not been supplied. Captured logs are still needed
to localize this run's failure. Private timing/operator state is
`operator-test-session.json` in the selected v3 bundle. The reference is
currently not restored on the card.

A guarded SSH/TTY shutdown request returned zero at
18:51:05 UTC after checking reference kernel/root; the owner entered credentials
directly in a local terminal. No password or terminal stream was captured.
This is a successful shutdown-command receipt, not independent confirmation
of disconnected physical power. The owner subsequently confirmed moving the
card to the reader in response to the power-disconnect/card-movement checklist.
Fresh inventory matched reader model/serial/capacity, GPT and all three
reference filesystem UUIDs/sizes before writing.

The selected v3 image and compressed recovery backup hashes were verified.
The guarded exclusive UDisks writer wrote and read back all 234,881,024 bytes
with matching image SHA-256; it also cleared the stale backup GPT signature.
Private receipt: `card-write-20261022T190035Z.json` in the v3 bundle. The DOS
table and both new filesystem UUIDs/sizes were verified, then the filesystems
were unmounted and the reader safely powered off. Receipt:
`card-ready-for-bluetooth-v3.json` in the bundle.

| Partition | Filesystem | UUID | Size (bytes) |
| --- | --- | --- | ---: |
| AICBOOT | ext4 | `e2f047ed-fa0a-4141-925f-e6b29a5bdf2d` | 134,217,728 |
| AICBOOTLOGS | FAT | `A1EF-30AC` | 67,108,864 |

Prepared local helpers are `/tmp/radxa-capture-bluetooth-v3.py`,
`/tmp/radxa-restore-after-bluetooth-v3.py` and
`/tmp/radxa-check-reference-after-bluetooth-v3.py`. They target this v3 bundle
and the new filesystem UUIDs above; capture/restoration have not been run.
Reidentify the device path on card return before using the restore helper.
The prepared writer is `/tmp/radxa-write-bluetooth-v3.py`; do not rerun it on
the test card, since its guards require the reference layout.

The selected private artifact is
`buildroot/output/radxa-bluetooth-test-20261022-v3/radxa-bluetooth-test.img`,
234,881,024 bytes, SHA-256
`9d30fc90d6c2ef38dd6ab2bba332677727a68f422bd6d4e0155ae690f731a32a`.
The source/build recipe and full check results are in
[bluetooth-test.md](../../aa_wireless_dongle/board/radxa/zero3w/checks/bluetooth-test.md).
Thirty-five host checks, six ARM64 supervisor cases and eleven ARM64 BusyBox
stage cases passed. Independent review's required findings were fixed.
Actual uninterruptible tasks and PID-1/hardware execution remain unverified.
Source changes are saved locally in commit `2de39a1`; no push or merge was made.
Private shutdown receipt: `reference-shutdown-for-v3.json` in the v3 bundle.

V3 adds bounded snapshots before attachment, at failure before cleanup and at
final capture. The snapshots record kernel logs, attachment process status,
wait location, current syscall and kernel stack, modules/interrupts/controller
state and live DT. Bluetooth packet data, process memory and bond storage are
excluded. Baudrate/flow, kernel/DT, firmware/modules, BlueZ and pairing acceptance
remain the v2 inputs. This is evidence collection, not an asserted UART fix.

## Physical test and recovery

Prepare the image/checks first, then shut down the reference cleanly. Disconnect
Radxa power before moving its card. Reidentify model `uSD SDDR-289`, serial
`<private>`, size 31,266,439,168 and all reference UUIDs/sizes from the v2
handoff. Adapt the guarded Bluetooth writer to the **v3** path/hash; do not run
the old v2 helper unchanged. Unmount, use the exclusive UDisks handle, clear the
stale backup GPT signature and write/readback all 234,881,024 bytes. Verify the
new DOS partitions and record the newly generated filesystem UUIDs before
adapting capture/restoration guards. Safely unmount/power off the reader.

Have phone Bluetooth settings open, use the same computer USB-A–USB-C setup,
and make **one start**. If `Radxa Mainline Test` appears, attempt pairing within
the three-minute window and record the displayed result/LED behavior. Wait
**twelve minutes after the reported start** even if the LED goes dark. No
automatic restart/retry. Disconnect power before returning the card.

Capture every log file privately from a read-only mount, hash each file and
preserve the entire postboot written range before restoration. Inspect
`failure-process.txt`, `failure-kernel.txt`, `failure-result.txt`, snapshot exit
receipts and `cleanup-result.txt`; a final snapshot timeout/read failure must
not count as completed capture. A process state/stack observation narrows the
UART failure without proving a proposed remedy.

Restore the same owner-selected **entire** reference backup:
`buildroot/output/radxa-recovery/radxa-os-20261021-172921.img.zst`.
Compressed SHA-256:
`720c2d888099df709ab2508a0f68ddf46110d3919fc0717c44d6c9435a3d2819`.
Verify all 31,266,439,168 restored bytes against raw SHA-256
`35be4ea0a847505d390aad10c9c95e9d18406ddb11421bd726011d1bfb1a6679`.
Refresh partition metadata with whole-disk UDisks Rescan if needed; wait for
the new inventory before verification. Verify GPT and the three original
filesystems, unmount and safely power off the reader. Boot the reference and
recheck Debian/kernel/root, Wi-Fi, SSH, hciattach, BlueZ, powered hci0 and both
AIC SDIO bindings. The last full restore/readback took 26.5 minutes.

Keep all device/phone identifiers and keys private. Remove any temporary phone
test bond after capture. No issue update, image publication, source-baseline
change, shipping prerequisite removal or Android Auto acceptance is part of
this diagnostic.
