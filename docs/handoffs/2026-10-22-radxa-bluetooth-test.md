# Next mainline Bluetooth test — 2026-10-22

## Physical test and recovery — 2026-10-22

This checkpoint supersedes the card-location and preparation-only state in the
historical checkpoint below. The owner confirmed Radxa power disconnected,
the card in the reader and the Android phone ready. Fresh inventory matched
reader model/serial, 31,266,439,168-byte capacity and all three reference
partition UUIDs/sizes. The selected Bluetooth v2 image and compressed recovery
backup matched their SHA-256 values below. All eight actual-image checks passed
again; the other sixteen checks were not rerun in this continuation.

The guarded writer was adapted to Bluetooth v2, with fixed image/backup hashes
and all three reference-partition guards. The image was written and all
**234,881,024 bytes** read back with matching SHA-256. The stale backup GPT
signature was cleared. Private write receipt:
`buildroot/output/radxa-bluetooth-test-20261022-v2/card-write-20261022T175355Z.json`.
The resulting DOS partition table and filesystems were verified:

| Partition | Filesystem | UUID | Size (bytes) |
| --- | --- | --- | ---: |
| AICBOOT | ext4 | `820ab2f1-d317-4dfb-a6d5-1402b80b0cd3` | 134,217,728 |
| AICBOOTLOGS | FAT | `CB4E-23E0` | 67,108,864 |

Both filesystems were unmounted and the reader safely powered off. Receipt:
`buildroot/output/radxa-bluetooth-test-20261022-v2/card-ready-for-bluetooth-test.json`.
The owner then reported connecting Radxa power; that report was recorded at
**17:55:59 UTC / 19:55:59 Europe/Stockholm**. Allow at least twelve minutes from
that report: **18:07:59 UTC / 20:07:59 local** before disconnecting power. One
start was requested, with the same computer USB-A–USB-C cable. At 17:58:46 UTC
the owner reported that the phone could not find Radxa. The expected advertised
name is `Radxa Mainline Test`; no discovery or pairing success is observed.
Captured logs now show failure before the pairing window. LED behavior
has not been reported. Private operator state is in
`buildroot/output/radxa-bluetooth-test-20261022-v2/operator-test-session.json`.

The owner reported the card back in the reader at about 18:00:47 UTC, roughly
five minutes after the power-on report, before the requested twelve-minute
minimum. Exact physical power-on/off times are not independently known. Keep
this limitation with the result; a completed diagnostic shutdown is not proven.

Fresh reader identity and both test UUIDs matched. All **ten captured files**
were copied from a read-only log mount and individually hash-verified into
`buildroot/output/radxa-bluetooth-test-20261022-v2/evidence-20261022T180105Z/`.
Private `evidence.json` and `analysis.json` record provenance, hashes and findings.
One boot directory was present. Embedded `inputs.json` matches the selected
image manifest.

- Radio firmware readiness and HCI Reset succeeded at about 14.85 seconds uptime.
- All eight Bluetooth module load commands returned success; the last progress
  entry is `14.98 hci_attach`.
- `bluetooth-result.txt` records `BT_PAIRING_RESULT=failed`, `STAGE=hci_attach`,
  `EXIT_CODE=11`. This gate fails if the attachment child is no longer alive or
  hci0 has not appeared within the bounded wait; these logs do not distinguish
  those cases. `hciattach.log` is empty.
- D-Bus/BlueZ/agent output and `bluez-objects.txt` are absent. No pairing window
  or discovery success is established. This accounts for the phone observation
  without attributing the failure to the phone.
- Final `capture-result.txt`, `dmesg.txt`, `hardware-after-cleanup.txt` and
  `live.dtb` are absent. The exact UART failure and reason the cleanup/final
  capture did not finish remain unknown; do not infer a kernel hang as proven.

Before restoration, the entire 234,881,024-byte postboot test range was preserved
as `postboot-card-20261022T180148Z.img` in the selected bundle, SHA-256
`66063c4b5f3c64abf6c8651dc605cab9f2ed7a3a411cf9d26d140a22d412424f`.
Full reference restoration ran from **18:01:50 to 18:28:20 UTC** (about
26.5 minutes). All **31,266,439,168 bytes** were read back and matched raw SHA-256
`35be4ea0a847505d390aad10c9c95e9d18406ddb11421bd726011d1bfb1a6679`.
Receipt: `reference-restore-20261022T180148Z.json` in the bundle. A whole-disk
UDisks `Block.Rescan` refreshed stale test-partition metadata; its asynchronous
refresh briefly left the first verification attempt seeing stale data. A fresh
inventory and repeated guarded finalization verified GPT and all three original
reference filesystem UUIDs/sizes. The mounted config partition was unmounted
and the reader safely powered off. Receipt:
`reference-card-ready-after-bluetooth.json` in the bundle.

The card now contains the **fully readback-verified Radxa OS reference**, not
the Bluetooth test image. The owner moved it back to Radxa and confirmed power
connected. After startup and an owner-entered local SSH login, the read-only
runtime probe **passed every recovery check**: Debian 12, kernel
`6.1.84-10-rk2410-nocsf`, root `/dev/mmcblk1p3`, associated Wi-Fi, active SSH,
hciattach and BlueZ, present/powered hci0 and both AIC SDIO bindings
(`c8a1:0082` → `aicwf_sdio`, `c8a1:0182` → `aicbsp_sdio`). Receipt:
`reference-status-after-bluetooth.json` in the bundle. No password or terminal
stream was captured. Radxa is left running the restored reference; physical
power remains connected. Recovery is complete; mainline Bluetooth attachment
and pairing remain unresolved.

Helpers are `/tmp/radxa-capture-bluetooth.py` (completed) and
`/tmp/radxa-restore-after-bluetooth.py` (completed). The latter uses the
new Bluetooth filesystem UUID guards above; the capture helper finds the reader
by model/serial/capacity. Reidentify the device path before any future use.
Keep phone identifiers and pairing evidence private; no successful test bond
was observed. No issue was updated or image published.

The next diagnostic should capture kernel/controller/process state at attachment
failure **before child cleanup**, including the attachment process state and
wait location. Preserve a bounded capture path and exclude Bluetooth keys. The
present evidence does not justify changing baudrate/flow control, enlarging the
discovery window or weakening the hci0 gate as a fix. The built kernel already
has `CONFIG_BT_HCIUART_H4=y`; a missing H4 selection is not supported by the
saved build configuration. Reproduce with improved evidence before choosing a
UART fix. Reference recovery and its runtime check are complete; any next
physical diagnostic must repeat identity-checked writing and preserve this
same selected recovery point.

## Historical preparation checkpoint

The owner requested a handoff and will continue this test later. **Preparation
is complete; no Bluetooth image has been written or booted.** Card movement to
the reader has not been confirmed. Its last confirmed location was in Radxa,
containing the restored Radxa OS reference. Physical power-off is not confirmed;
disconnect power before moving the card. Resume with the physical checklist
below, after the owner is ready with the card and Android phone.

The owner authorized proceeding after the
[radio-reset experiment and verified recovery](2026-10-22-radxa-radio-test.md),
and confirmed that an Android phone is available. The next private diagnostic
adds UART attachment, D-Bus/BlueZ and a bounded, owner-assisted pairing window.
See the [test procedure](../../aa_wireless_dongle/board/radxa/zero3w/checks/bluetooth-test.md)
for build commands, checks, operator timing and recovery.

The selected image is
`buildroot/output/radxa-bluetooth-test-20261022-v2/radxa-bluetooth-test.img`,
224 MiB, SHA-256
`a4f10f4159a11a7a47dac12b94599717eb2aa192f3285b5971c9440a7280e423`.
It has not been written or physically tested. The card still contains the
full-readback-verified Radxa OS reference; the selected existing full-card
backup remains its recovery point.

Buildroot 2026.02.3's pinned Bootlin profile built BlueZ 5.79/D-Bus 1.14.10 in
`radxa-bluetooth-userspace-container/`. The verified mainline Linux 6.12.114,
DT, boot chain, radio modules/firmware and reset helper are unchanged. Eight
additional matching kernel modules provide the Bluetooth dependency closure.
The native pairing agent accepts only the BlueZ bus owner, limits one candidate,
requires a real Paired event/property readback and closes discoverability and
pairability on success/timeout. It uses a three-minute `NoInputNoOutput` window
named `Radxa Mainline Test`, without trusting devices or authorizing profiles.

All 24 local checks pass (nine agent, seven stages, eight image), including
mutation detection, process cleanup and actual packed-archive inspection.
The same nine agent cases also pass with the actual ARM64 binary/GIO under
QEMU. This validates userspace bus behavior, not physical UART or pairing.
Classic Bluetooth/H4 are enabled; LE/RFCOMM remain disabled in the selected
kernel. Firmware distribution, regulatory/AP warnings, actual pairing and
full dongle acceptance remain unresolved. #5 stays open; no dependent shipping
task was unblocked or image published.

The next physical step is confirming power is disconnected and moving the card
to the reader for identity-checked writing and full image readback. The operator must
be ready on the phone before test power-on, perform one start, confirm pairing
within the three-minute window and allow twelve minutes before card return.
Preserve logs before restoring the selected full-card backup. Remove the phone's
temporary test bond after capture; its controller-side keys are intentionally
not persistent across recovery. Never print/copy link keys into public evidence.

## Reference shutdown checkpoint

After the image/checks completed, a strict-host-key SSH login reverified
reference kernel `6.1.84-10-rk2410-nocsf` and root `/dev/mmcblk1p3`. Passwordless
sudo was unavailable, so a local interactive SSH/TTY was opened for
`sudo systemctl poweroff --no-block`, guarded by the same kernel/root checks.
No password or terminal stream was captured. The session ended with SSH status
255; the control socket disappeared and the saved SSH endpoint was subsequently
unreachable. This is consistent with shutdown but is not an independent physical
power-state confirmation or a captured successful systemctl receipt.

Private receipts are `reference-shutdown-preparation.json` and
`interactive-shutdown-receipt.json` in the selected image directory. The card
still contains Radxa OS. **Disconnect Radxa power before moving the card to the
reader.** Reidentify its model/serial/capacity and reference partition UUIDs
before writing; do not reuse an old device path without those checks.

## Evidence and recovery point

The preceding radio test physically passed firmware readiness and HCI Reset on
Linux 6.12.114, with both AIC SDIO functions bound. Its private evidence is
`buildroot/output/radxa-radio-test-20261022-v2/evidence-20261022T115544Z/`
(`evidence.json`, `analysis.json` and captured logs). UART attachment, a powered
BlueZ adapter and phone pairing on mainline are the next unverified steps.

The entire selected reference backup was restored and read back successfully
after that radio test. Recovery receipts and the subsequent runtime check are:

- `buildroot/output/radxa-radio-test-20261022-v2/reference-restore-20261022T115621Z.json`
- `buildroot/output/radxa-radio-test-20261022-v2/reference-status-20261022T124019Z.json`

The latter confirmed Debian 12, kernel `6.1.84-10-rk2410-nocsf`, root
`/dev/mmcblk1p3`, associated Wi-Fi, active SSH/hciattach/BlueZ and powered hci0.
It does not establish mainline Bluetooth behavior.

Use the owner's already selected recovery source:
`buildroot/output/radxa-recovery/radxa-os-20261021-172921.img.zst`, with adjacent
`.img.zst.json` metadata. Compressed SHA-256:
`720c2d888099df709ab2508a0f68ddf46110d3919fc0717c44d6c9435a3d2819`.
The decompressed image is **31,266,439,168 bytes**, SHA-256
`35be4ea0a847505d390aad10c9c95e9d18406ddb11421bd726011d1bfb1a6679`.

Previously verified reader: model `uSD SDDR-289`, serial `<private>`.
Recheck these, card capacity and the reference GPT partitions before writing:

| Partition | Filesystem | UUID | Size (bytes) |
| --- | --- | --- | ---: |
| config | FAT | `21BD-9125` | 16,777,216 |
| efi | FAT | `21BD-F314` | 314,572,800 |
| rootfs | ext4 | `d3e135b3-8caf-4d6e-b97a-d1da670d91b7` | 30,918,295,040 |

Historical `/dev/sdc` is not a current device identification. The selected
Bluetooth image directory contains `manifest.json` and `SHA256SUMS`; verify the
actual image against the hash above before use. The earlier directory without
`-v2` is superseded. The v2 init requires provenance capture and sync before
starting radio actions. No rebuild is needed if the selected artifact remains
intact.

## Resume procedure

1. Confirm the owner is ready with the Android phone. Disconnect Radxa power,
   move the card to the reader and obtain a fresh device inventory. Verify the
   identity, reference partitions, selected backup and selected Bluetooth image.
2. Adapt the earlier guarded writer to this **Bluetooth v2** bundle and current
   device identity. Unmount card filesystems, use the identity-checked exclusive
   UDisks device handle, write exactly **234,881,024 bytes**, flush and read back
   the entire written range against the image SHA-256. Follow the existing
   procedure for clearing the stale backup GPT signature. Verify the test DOS
   partition table, 128 MiB boot partition and 64 MiB `AICBOOTLOGS` partition;
   save their new UUIDs, unmount and safely power off the reader.
3. Open phone Bluetooth settings before powering Radxa. Use the same computer
   USB-A–USB-C cable and one start. Pair with **Radxa Mainline Test** within three
   minutes of its discovery window. Record the phone result and LED behavior.
   Allow **twelve minutes** before disconnecting power and returning the card.
4. Mount logs read-only, copy and hash every captured file privately, and
   preserve the post-test written card range before restoration. Require radio
   and Bluetooth success, agent exit zero with actual Paired property readback,
   zero setup/radio/Bluetooth stage exits and completed capture. A dark LED or
   `CAPTURE_FINISHED` alone does not establish success. Inspect BlueZ's live
   object capture; hci0 may disappear in the later hardware cleanup snapshot.
5. Restore the **entire** selected reference backup and read back all
   31,266,439,168 bytes against the raw backup SHA-256. Previously this took
   about 26.5 minutes. Verify reference GPT/filesystems, unmount and power off
   the reader. UDisks may need a whole-disk `Block.Rescan` to refresh stale
   test-partition metadata before verification.
6. Boot the reference again and recheck kernel/root, Wi-Fi, SSH, hciattach,
   BlueZ, powered hci0 and both AIC SDIO bindings. Remove the temporary test bond
   from the phone after evidence collection. Summarize actual hardware findings
   locally before considering another issue update.

The historical helpers `/tmp/radxa-write-radio-test.py` and
`/tmp/radxa-restore-after-radio.py` contain **radio-test** bundle paths and UUID
guards. They are not ready to run for this Bluetooth test: adapt and review them
against the new bundle/device/UUIDs first. `/tmp` files and SSH control sockets
may disappear between sessions. `/tmp/radxa-reference-status.py` was the
read-only runtime probe; recreate it if missing. Private access metadata and
strict known-host records live under `buildroot/output/radxa-recovery/`; keep
credentials, phone identifiers and bond keys out of public documentation.

## Saved implementation

Branch: `feature/radxa-zero3w-hci-reset`. Prepared work is saved in commits
`2f9ed1f` (agent), `3c86dff` (userspace), `5a85e49` (stages), `8ff34f0` (image)
and `d3136c5` (initial handoff/shutdown checkpoint). No push or merge was made.
Source/build entry points are in
`aa_wireless_dongle/board/radxa/zero3w/checks/`: `bluetooth-test.md`,
`make-bluetooth-test.py`, `bluetooth-test-init.sh`, `aic-bluetooth-test.sh`,
`aic-pairing-test.c` and `bluetooth-test_defconfig`. Local build inputs/logs are
under `buildroot/output/radxa-bluetooth-test-prep/` and
`buildroot/output/radxa-bluetooth-userspace-container/`. These ignored private
artifacts do not travel with a Git checkout; preserve them for this experiment.

The last published #5 update is recorded in
[the issue-update receipt](2026-10-22-issue-5-update.md). This handoff adds no
external publication. Pairing evidence, firmware redistribution, regulatory/AP
review, persistent bonds, LE/RFCOMM and Android Auto acceptance remain separate
unfinished work.
