# Radxa boot-test card — 2026-10-22

Continue from the [prepared test procedure](../../aa_wireless_dongle/board/radxa/zero3w/checks/boot-test.md)
and [source-selection handoff](2026-10-21-radxa-zero3w.md).

## Current physical state

The owner's single microSD card now contains the **boot-only diagnostic image**,
not Radxa OS. The owner moved it to the reader and explicitly selected the
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
powered off the reader. The card is ready to remove. No physical mainline boot
or collected boot log is established yet.

Private write/readback evidence is saved under
`buildroot/output/radxa-boot-test-20261022-v3/card-write-20261022T093418Z.json`.
The artifact and manifest remain beside it. Do not publish private access or
configured-card recovery files.

## Next physical step

Insert the card in the **unpowered Radxa**, connect the known bench power and
allow at least three minutes. This image provides no Wi-Fi or SSH. Remove power
and return the card to the computer's reader so the log partition can be read.
The image attempts to flush/unmount its logs and power off without rebooting.

Reidentify the card on return; do not reuse an earlier device name. Preserve
the FAT logs read-only before repair, rewriting or restoring anything. An empty
log partition is inconclusive without UART; do not claim boot failure at a
particular stage or perform repeated blind writes. Follow the prepared
procedure's evidence interpretation and full-card restoration steps using the
owner-selected `radxa-recovery/radxa-os-20261021-172921.img.zst` backup.

The status update remains a [local draft](2026-10-22-issue-5-update.md).
No GitHub publication, push or merge was performed. Firmware terms and #5's
dependent-task prerequisites remain unresolved.
