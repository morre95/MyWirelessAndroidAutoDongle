# Radxa Bluetooth UART failure capture — 2026-10-22

## V4 result and completed reference recovery — 2026-10-23

The owner moved the restored card back and confirmed Radxa power connected.
After owner-entered local SSH login, **all seven read-only runtime checks
passed at 11:15:52 UTC**: Debian 12, kernel `6.1.84-10-rk2410-nocsf`, root
`/dev/mmcblk1p3`, associated/up Wi-Fi, active SSH/hciattach/BlueZ, present and
powered hci0, and both AIC SDIO bindings. Private receipt:
`reference-status-after-v4.json` in the v4 bundle. An initial association probe
returned 125 and is preserved as `reference-status-after-v4-first-probe.json`;
the repeat used an explicit system-tool PATH and all checks passed with no
query errors. The PATH regression was reproduced and fixed without weakening
the Wi-Fi check. No password or terminal stream was captured.

**Card and running-reference recovery are complete. Radxa is left running the
restored reference, with power connected.** The mainline diagnostic pairing
still failed as recorded below. The next source-supported hypothesis is
explicit `ControllerMode=bredr`; no v5 image has been built or tested. Keep
the reference running while preparing any next diagnostic.

Full reference restoration ran from **10:17:17 to 10:44:19 UTC** (27.0
minutes). All **31,266,439,168 bytes** were restored and read back with raw
SHA-256 `35be4ea0a847505d390aad10c9c95e9d18406ddb11421bd726011d1bfb1a6679`.
Whole-disk rescan, GPT and all three original filesystem UUIDs/sizes passed;
all partitions were unmounted and the reader safely powered off. Both desktop
automounters were confirmed resumed; no operator-error receipt was created.
Private receipts: `reference-restore-v4.json` and
`reference-card-ready-v4.json` in the v4 bundle.

**The card now contains the fully readback-verified Radxa OS reference.** It
has been moved back and reference boot/runtime recovery passed as recorded
above. Do not treat reference recovery as mainline Bluetooth diagnostic success.

All **74 files across two boot directories** were copied from a read-only log
mount and individually SHA-256-verified into the private v4 bundle's
`evidence-20261023T101114Z/`. Both embedded inputs match the selected v4
manifest. `evidence.json` and `analysis.json` preserve provenance and findings.
The full postboot **234,881,024-byte** test range is preserved as
`postboot-card-20261023T101114Z.img`, SHA-256
`18ff55c6ef3e4a345df99fee6ea140c06a2f95ef3257fa0420469196fbb09ada`.
Capture receipt: `capture-v4.json`.

Both boots passed setup and radio reset, registered hci0 and passed the live
attachment gate (`hciattach.log`: `Device setup complete`), then started D-Bus
and BlueZ. Both failed at `STAGE=bluez_start`, exit **13**. BlueZ 5.79 reports
`getsockopt(L2CAP_OPTIONS): Operation not supported (95)`, then failure to
create the GATT database and register the adapter. `org.bluez.Adapter1` is
absent, and the pairing agent/window never starts. Failure snapshots and final
snapshots exit zero, both report `CAPTURE_FINISHED=1`, and all three children
are reaped with `CLEANUP_FINISHED=1`. Attachment was sleeping in `do_sys_poll`,
not observed in D state. These logs support completed diagnostic capture and
cleanup, not physical pairing or Android Auto acceptance. The init's normal
poweroff path is consistent with the reported LED going dark.

The exact built BlueZ 5.79 `src/adapter.c` lines 9297–9302 skip GATT database
and advertising setup when `ControllerMode=bredr`. Its default `main.conf`
documents dual mode; the selected kernel configuration has `CONFIG_BT_LE=n`.
Explicit BR/EDR mode is therefore a source-supported next diagnostic hypothesis
that can avoid this LE/GATT initialization path without changing the kernel.
It is **not implemented or physically verified** at this checkpoint; optional
plugin warnings do not by themselves explain the fatal adapter error. Do not
claim that enabling kernel LE or disabling arbitrary plugins is required.

All evidence is preserved and full-card recovery is complete as recorded
above. `/tmp/radxa-restore-v4.sh` is a **completed historical entrypoint**, not
a command to rerun. The private helper refuses an existing restore receipt.
All twelve private operator checks pass, including real zstd decompression and
full temporary-file recovery, rejection of corrupted readback, and refusal to
write if preserved evidence has changed. After verified card recovery, the
prepared local `/tmp/radxa-check-reference-v4.sh` performs the read-only runtime
checks through owner-entered SSH login with the existing strict host-key
record; this local finalization entrypoint is now completed. It captures only
the remote probe's JSON stdout, not password input.

## V4 physical and writing history — 2026-10-23

The owner reported two starts at **09:57:52 UTC**, neither showing the test
device in the phone Bluetooth scan, with the LED going dark shortly after
power application. Exact physical start times and durations were not measured.
Power was disconnected at **12:10 local / 10:10 UTC**, to minute precision,
after the conservative twelve-minute wait; the card was returned to the reader.
Both partitions were automatically mounted by the host on insertion. Capture
paused desktop automounters, unmounted them and collected files from a read-only
log mount. The preserved raw range can therefore include host mount metadata;
it is not claimed to be an untouched power-off image. Private operator timing
and final state are in `operator-test-session.json` in the v4 bundle.

Before physical testing, the first write started at **09:33:26 UTC** but its
readback differed after the host mounted AICBOOT read-write at **09:33:36 UTC**.
The original helper had closed its exclusive handle and rescanned before
verification. The corrected helper temporarily pauses only the owner's udiskie
and GVfs volume monitors, verifies under the exclusive writer and again through
a fresh handle after rescan, then refuses any unexpected mount before ejection.
It resumes previously running monitors on exit and changes no desktop settings.

The complete failed preboot range was preserved before repair as
`failed-preboot-card-20261023T095051Z.img`, SHA-256
`7b8f7774d36e6d7746137989f222a83620f2d1e2b083697ac2977f51f66bd23c`.
`pre-repair-v4.json` records 87 differing bytes across six sectors, all within
boot ext4, consistent with the recorded writable mount. Original evidence is
retained as `card-write-v4-failed-original.json`,
`operator-v4-before-automount-fix.py` and `failed-write-mount-journal.txt`.

An intervening repair startup failed before opening the card because process
inventory resolved an unrelated pCloud executable through a protected FUSE
mount. `startup-diagnosis-20261023T094759Z.json` and
`operator-v4-before-proc-filter.py` preserve this failure. Filtering process
names first and inspecting only known monitors' executable symlinks fixed it;
selected-monitor access errors still fail closed. Both actual desktop monitors
passed a host pause/resume check without card access. No second card-write
failure was established.

The corrected preboot write passed both full-image readbacks of 234,881,024
bytes against selected v4 SHA-256
`4a0186870d04bbca2bf73ded9b20f7ab0926723123c9e2820e4d4ea9603776ce`.
DOS table, sizes/labels, boot UUID `fec47bc7-62b5-4400-85fd-0cb2535463dc` and
log UUID `381C-EB2B` passed; the stale backup GPT signature was cleared. The
reader was safely powered off at **09:51:07 UTC**. Preboot receipts:
`card-write-v4.json` and `card-ready-v4.json`.

## Local v4 helpers and checks

Historical `/tmp/radxa-*.py` helpers from v3 were absent. The replacement
private `operator-v4.py` is preserved with the v4 bundle, pins selected
image/backup/device/filesystem identities, verifies preserved capture before
restoration and refuses repeated completed operations. It saves program
exceptions as `operator-error-<timestamp>.json`. Local terminal entrypoints
record program results while passwords are entered directly by the owner.
The completed write/capture/restore helpers must not be rerun on the reference.

Fresh selected image and compressed-backup hashes and all ten actual-image
checks passed before writing. Nineteen initial guard/I/O checks passed without
card writes. The twelve final private operator regressions cover writable
mount interference, preserved snapshots/evidence, genuine corruption, strict
ejection, process selection/resume and real zstd/full-file recovery. Removing
automount suspension in an isolated helper copy reproduces the regression;
the protected-FUSE and command-PATH failures were also reproduced before their
fixes. These checks and the physical evidence above do not establish pairing.

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
Full reference restoration ran from **19:20:25 to 19:46:56 UTC** (26.5 minutes).
All **31,266,439,168 bytes** were read back and matched raw SHA-256
`35be4ea0a847505d390aad10c9c95e9d18406ddb11421bd726011d1bfb1a6679`.
Receipt: `reference-restore-20261022T192023Z.json` in the v3 bundle. Whole-disk
UDisks Rescan plus a bounded wait refreshed the partition metadata; GPT and all
three original filesystem UUIDs/sizes passed verification. The config partition
was unmounted and the reader safely powered off. Receipt:
`reference-card-ready-after-bluetooth.json` in the v3 bundle.

The card now contains the **fully readback-verified Radxa OS reference**. The
owner moved it back and confirmed power connected. After boot and an
owner-entered local SSH login, **all read-only runtime recovery checks passed**:
Debian 12, kernel `6.1.84-10-rk2410-nocsf`, root `/dev/mmcblk1p3`, associated
Wi-Fi, active SSH/hciattach/BlueZ, present and powered hci0, and AIC SDIO bindings
`c8a1:0082` → `aicwf_sdio`, `c8a1:0182` → `aicbsp_sdio`. Receipt:
`reference-status-after-bluetooth.json` in the v3 bundle. No password or terminal
stream was captured. Radxa is left running the restored reference, with power
connected. Card and runtime recovery are complete. Local finalization helper:
`/tmp/radxa-finalize-v3-recovery.py` (completed).

A v4 image fixing the process-control dependency has been built locally and
reviewed; source changes are saved in local commit `5c20818`. Selected candidate:
`buildroot/output/radxa-bluetooth-test-20261022-v4/radxa-bluetooth-test.img`,
234,881,024 bytes, SHA-256
`4a0186870d04bbca2bf73ded9b20f7ab0926723123c9e2820e4d4ea9603776ce`.
It has not been written or physically tested. Forty-one host checks and
twenty-two ARM64/QEMU helper/stage checks pass, including an isolated PATH with
no host kill, actual child signal delivery and packed-executable probes. No
required review findings remain; an ESRCH-result mutation is detected. These
checks do not establish physical Bluetooth acceptance. Reference card and
runtime recovery are complete as recorded above. The
v3 temporary capture/restore helpers are completed historical helpers, not
ready-to-run v4 helpers: adapt bundle/hash/UUID guards and obtain fresh device
identity before the next write. The full v4 recipe and limits are at the top
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
Source changes are saved locally in commit `7f044a6`; no push or merge was made.
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
