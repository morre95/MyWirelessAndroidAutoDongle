# Radxa boot-test card — 2026-10-22

Continue from the [prepared test procedure](../../aa_wireless_dongle/board/radxa/zero3w/checks/boot-test.md)
and [source-selection handoff](2026-10-21-radxa-zero3w.md).

## Card preparation record

The owner's single microSD card was written with the **boot-only diagnostic image**
for this experiment. The owner moved it to the reader and explicitly selected the
existing backup made yesterday as the recovery point. This supersedes the
procedure's fresh-backup step for this run; no new full-card backup was made.
Do not request another backup merely because the generic procedure says fresh.

Before writing, the card matched the recovery metadata's model, reader serial,
**31,266,439,168-byte** capacity and reference rootfs UUID. The automatically
mounted config partition was unmounted. The test image and preserved compressed
backup hashes matched their records. The full backup's raw hash and decompressed
byte count had also been verified earlier in this session.

Using the normal UDisks system-authorization dialog, an exclusive read/write
descriptor was obtained for that card. The old backup-GPT signature at its
physical end was cleared and the complete image written. After flushing and
requesting cache eviction, all **234,881,024 written bytes** were read back:

```text
SHA-256 7c6274d0d048d84760018a7f18424dc6db933d6cfb3c03be810adc336af74910
```

The system detected DOS partitions `AICBOOT` (128 MiB ext4) and `AICBOOTLOGS`
(64 MiB FAT32). Both desktop automounts were unmounted, and UDisks successfully
powered off the reader. At that checkpoint the card was ready to remove; the
physical results below were collected subsequently.

Private write/readback evidence is saved under
`buildroot/output/radxa-boot-test-20261022-v3/card-write-20261022T093418Z.json`.
The artifact and manifest remain beside it. Do not publish private access or
configured-card recovery files.

## Physical boot and evidence

The owner moved the card to Radxa and observed its LED going dark after about
five seconds, then returned the card to the reader. The owner confirmed three
separate power applications from a computer USB-A port through a USB-A–USB-C
cable. Exact port/cable models and power-removal durations were not measured.
The diagnostic deliberately
flushes/unmounts logs and requests poweroff immediately after capture; it does
not wait three minutes. The operator's three-minute wait was a conservative
allowance. No exact power-on/off timing or boot-stage serial banner was captured.

The returning card matched its recorded identity and diagnostic partitions.
Both automatic desktop mounts were unmounted; `AICBOOTLOGS` was remounted
read-only. Three boot UUID directories, each with all four expected files,
were copied privately and SHA-256-verified under
`buildroot/output/radxa-boot-test-20261022-v3/evidence-20261022T094234Z/`.
`evidence.json` records hashes/sizes; `analysis.json` records the checks.

All three reach Linux 6.12.114 diagnostic userspace, record expected-kernel and
capture-finished markers, expose UART1 and `fcc00000.usb` UDC, and show the
selected live-DT GPIO hogs/directions. PC1 is output low, PC0 reset physical
high/deasserted, antenna PD3 output low and PB3/PB4 input high. PB3's level/IRQ
differs from the initialized Radxa OS reference; no radio modules/firmware are
included in this test, so these snapshots do not establish operating-radio
pin equivalence.

Boot `2de0087f-418a-4aac-a684-c4369149f931` records SDIO IDs `c8a1:0082` and
`c8a1:0182`, with its last saved kernel line at 1.645943 s. The other two logs
end around 1.01 s while the SDIO host is still initializing. Missing SDIO entries
in those early captures are inconclusive; the next diagnostic must wait for
explicit enumeration/readiness and report timeout before taking its final logs.

There are no saved priority 0–3 messages or panic/Oops/BUG/call-trace signatures.
Warnings concern ITS/LPIs, static GPIO bases and console UART DMA. The observed
LED-off behavior is consistent with intentional poweroff after successful
capture. Final shutdown occurs after the saved dmesg, so it is not independently
logged. These are three brief boots, not three acceptance cold starts or proof
of mainline Wi-Fi/Bluetooth/accessory operation.

## Recovery

Full-card restoration from the owner-selected previous-day backup completed
on 2026-10-22. All **31,266,439,168 bytes** were written, flushed and read back;
the SHA-256 matches the backup's recorded raw hash. The original `config`
(FAT), `efi` (FAT) and `rootfs` (ext4) partitions and UUIDs were verified after
refreshing cached device metadata. The desktop config mount was unmounted and
UDisks successfully powered off the reader. The physical card now contains
**Radxa OS again** and is safe to remove.

Private evidence under `buildroot/output/radxa-boot-test-20261022-v3/`:

- `postboot-card-20261022T094434Z.img`: the first 234,881,024 bytes of the test
  card preserved before restoring, in addition to the extracted logs.
- `reference-restore-20261022T094434Z.json`: snapshot hash, selected recovery
  source, full write/readback hashes/counts and successful completion state.

Recovery used `radxa-recovery/radxa-os-20261021-172921.img.zst`. The owner then
returned the card to Radxa and powered it on. A read-only SSH check, with the
persisted host key strictly verified, confirmed Debian 12, reference kernel
`6.1.84-10-rk2410-nocsf` and root on `/dev/mmcblk1p3`. Wi-Fi `wlan0` was
associated with carrier/operstate up. SSH, hciattach and BlueZ were active;
`hci0` was present and its BlueZ `Powered` property was true.

BSP/fdrv were live in normal work mode, both expected SDIO functions were bound
to `aicwf_sdio` / `aicbsp_sdio`, and btlpm was absent. The temporary startup-test
directory was absent. The reference reset service was failed with exit status 2,
matching the previously documented reference condition despite active/powered
Bluetooth. Its journal yielded no records to this unprivileged SSH check;
no new timeout-cause claim is made and no service was restarted or altered.

Private structured evidence is under
`buildroot/output/radxa-boot-test-20261022-v3/`:
`reference-status-20261022T102328Z.json` records the initial check, and
`reference-status-20261022T102541Z.json` repeats it after the owner requested a
fresh SSH login. Both confirm the restored reference. Passwords were entered
directly in a local SSH terminal and not stored. The temporary SSH control
connection was closed after the checks; local access metadata now records the
verified reference state. Reidentify devices on each insertion rather than
reusing an earlier name.

The owner subsequently authorized publication of the
[status update](2026-10-22-issue-5-update.md), now verified as
[this comment on #5](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5#issuecomment-6338740112).
No push or merge was performed. Firmware terms and #5's dependent-task
prerequisites remain unresolved.

Local radio-test preparation is complete in commit `48629fc`; see the
[radio-test procedure](../../aa_wireless_dongle/board/radxa/zero3w/checks/radio-test.md)
for inputs, checksums, limitations and later card/recovery steps. The selected
private image is `buildroot/output/radxa-radio-test-20261022-v2/radxa-radio-test.img`,
SHA-256 `1d1ab91f8e31dd9ac1fa60f3159914f98c2f5b4509868b15784f42f0a22ee90f`.
All 15 radio tests pass; this includes failure ordering, log-write/sync failures
and inspection of the packed payload. The static ARM64 helper's hardware runtime
is pending: QEMU user emulation rejects its `TIOCGEXCL` ioctl, while the native
host UART suite passes. No radio-test image has been flashed or booted, and the
running reference remains untouched. Preparation does not authorize writing the
card or interrupting Radxa OS.
