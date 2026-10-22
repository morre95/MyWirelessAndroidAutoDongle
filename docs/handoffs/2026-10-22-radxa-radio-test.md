# Radxa radio-test card — 2026-10-22

Continue from the [radio-test procedure](../../aa_wireless_dongle/board/radxa/zero3w/checks/radio-test.md)
and [boot-test/recovery handoff](2026-10-22-radxa-boot-test.md).

## Card preparation

After preparation, the owner moved the single card from Radxa to the reader to
proceed with the test. The card matched the previously recorded reader model,
serial, **31,266,439,168-byte** capacity and reference rootfs UUID. Its config
partition was unmounted. The selected image and compressed recovery backup
matched their recorded hashes before writing. The owner-selected previous-day
backup remains the recovery point; no new full-card backup was requested or made.

The exclusive UDisks descriptor was checked against the identified block device,
capacity and sector size. The stale backup-GPT signature at the physical end
was cleared, and the complete **234,881,024-byte** radio image was written,
flushed and read back after requesting cache eviction. All written bytes match:

```text
SHA-256 1d1ab91f8e31dd9ac1fa60f3159914f98c2f5b4509868b15784f42f0a22ee90f
```

The system detected a DOS partition table with `AICBOOT` (128 MiB ext4) and
`AICBOOTLOGS` (64 MiB FAT32). Both desktop automounts were unmounted, and UDisks
successfully powered off the reader. The card is ready to remove. It now
contains the radio diagnostic, replacing Radxa OS until recovery; no radio-test
boot or hardware result has yet been observed at this checkpoint.

Private image, manifest and write/eject evidence are under
`buildroot/output/radxa-radio-test-20261022-v2/`:
`card-write-20261022T111138Z.json` records the write/readback hashes, partition
identifiers, original recovery source and successful unmount/poweroff state.
Build-time `physical_test_performed` flags are unchanged; later hardware
evidence must be recorded separately. Keep firmware, backup and raw logs private.

## Next physical step

Insert the card into the **unpowered** Radxa, then apply the same computer
USB-A–USB-C power connection for comparison. Perform **one start** and allow
**six minutes**, even if the LED goes dark earlier. The diagnostic deliberately
powers off after its capture sequence. Do not infer success or failure from
the LED and do not repeat blind power cycles.

After the allowance, disconnect power and return the card to the reader. Identify
it again, unmount desktop mounts, collect the diagnostic partition read-only
and preserve/hash its files before repair, retry or restoration. Inspect
`radio-result.txt`, `progress.txt`, `capture-result.txt` and kernel logs together.
Only successful firmware readiness plus a matching HCI Reset establishes the
limited radio result; AP, pairing, coexistence and Android Auto remain untested.

Then preserve the post-test card image and restore the owner-selected complete
Radxa OS backup, using full-card readback verification and the reference checks
from the earlier handoff. Reidentify device paths on each insertion.
