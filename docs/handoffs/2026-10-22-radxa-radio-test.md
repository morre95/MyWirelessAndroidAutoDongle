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

## Physical result

The returning card matched its recorded model, serial, capacity and both test
partition UUIDs. Desktop mounts were unmounted, and `AICBOOTLOGS` was mounted
read-only. One boot directory, `19f036ad-b596-4a94-b66f-1320d05112da`, contained
all nine expected files; every copied file's SHA-256 matched the source.
Private evidence is in
`buildroot/output/radxa-radio-test-20261022-v2/evidence-20261022T115544Z/`;
`evidence.json` records file hashes, and `analysis.json` records cross-checks.

Linux **6.12.114** reached diagnostic userspace with the expected V1.12M/AIC
model. Both SDIO IDs bound to their expected drivers. The four selected modules
were live, with no btlpm. The kernel logged all six selected firmware/config
paths, and the embedded input record matched the selected image manifest.

The progress markers show kernel validation at 1.06 s, waiting for SDIO at
1.07 s, rfkill/cfg80211/BSP/fdrv loads beginning at 2.09/2.10/2.15/2.16 s,
firmware readiness at 3.69 s, HCI Reset beginning at 3.72 s and completion at
**3.74 s**. These are kernel-uptime markers, not measured power-on/shutdown times.
`radio.log` contains `AIC firmware load ordering ready: wlan0` and
`HCI Reset complete`; `RADIO_RESET_RESULT=success`, `RADIO_STAGE_EXIT=0` and
`CAPTURE_FINISHED=1` agree. The helper requires a matching HCI Reset Command
Complete with status zero. Its newly static ARM64 build has now executed
successfully on the real board, resolving the pending native-execution check;
the QEMU-user ioctl limitation remains a separate host-emulation issue.

All five candidate DT property groups also passed against `live.dtb`: Bluetooth
GPIO defaults, mux/pulls, SDIO power sequence, four UART flow-control pins and
antenna/SDIO settings. The GPIO snapshot shows PC1 low, PC0 physical high,
antenna PD3 low, PB3 input low and PB4 input high. This captures initialized
directions/levels, not electrical timing or long-term stability.

No panic/Oops/BUG/call-trace signatures were found in the saved kernel log.
Do not describe it as error-free: it records missing `regulatory.db`, permissive
custom regulatory rules, an early BSP power-control timer `bus down` message
and UART1 DMA-property/request warnings, plus out-of-tree taint and earlier
ITS/static-GPIO/console-DMA warnings. The timer reports its `BUS_DOWN_ST` branch
during initialization; subsequent firmware readiness and reset succeed. Its
long-term significance has not been established. Regulatory configuration must
be reviewed before AP/channel acceptance; UART-DMA fallback needs assessment
with sustained traffic. No driver workaround was applied from this snapshot.

This is **one brief successful initialization/reset**, not Wi-Fi association/AP,
hciattach/BlueZ operation, pairing, coexistence, repeated cold starts or Android
Auto acceptance. The owner confirmed one start, the same computer USB-A–USB-C
cable and a wait of at least six minutes. No separate LED observation or exact
power-on/shutdown timing was supplied.

## Recovery after radio test

The log partition was unmounted after verified capture. Before restoration,
all **234,881,024 bytes** of the post-test diagnostic card region were preserved
as `postboot-card-20261022T115621Z.img` under the private bundle directory.
Its SHA-256 is recorded in `reference-restore-20261022T115621Z.json` beside it.

Full-card recovery from the previously selected
`radxa-recovery/radxa-os-20261021-172921.img.zst` is complete. The compressed
backup hash was reverified, and all **31,266,439,168 bytes** were written,
flushed and read back after requesting cache eviction. The source and full
readback SHA-256 both match the recorded raw-backup hash. The private recovery
record includes byte counts, hashes and completion timestamps.

After refreshing UDisks metadata, the original GPT and `config`/`efi`/`rootfs`
filesystem identities were verified. The config desktop automount was unmounted
and UDisks successfully powered off the reader. The card now contains **Radxa OS
again**, is safe to remove and is no longer a radio diagnostic card.

Return it to the unpowered Radxa and boot the reference. Post-recovery SSH,
Wi-Fi association, hciattach and powered-hci0/BlueZ checks are pending that
physical step; they have not been inferred from the raw-card verification.
