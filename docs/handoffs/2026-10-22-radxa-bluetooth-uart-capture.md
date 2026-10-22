# Radxa Bluetooth UART failure capture — 2026-10-22

## Current checkpoint

The owner authorized the next diagnostic after the
[v2 attachment failure and verified recovery](2026-10-22-radxa-bluetooth-test.md).
The card still contains the restored Radxa OS reference. **No v3 image has
been written or booted.** A guarded SSH/TTY shutdown request returned zero at
18:51:05 UTC after checking reference kernel/root; the owner entered credentials
directly in a local terminal. No password or terminal stream was captured.
This is a successful shutdown-command receipt, not independent confirmation
of disconnected physical power. The owner has been asked to disconnect power
and move the card to the reader; that confirmation is pending.

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
