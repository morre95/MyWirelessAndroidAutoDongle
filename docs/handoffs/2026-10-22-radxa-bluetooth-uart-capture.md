# Radxa Bluetooth UART failure capture — 2026-10-22

## Current checkpoint

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
