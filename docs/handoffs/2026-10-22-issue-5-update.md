# Prepared update for issue #5 — 2026-10-22

Local draft for [issue #5](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues/5).
Not published. The text below can be appended to the existing issue without
replacing its history or changing its acceptance boxes/dependencies.
The separately prepared [boot experiment](../../aa_wireless_dongle/board/radxa/zero3w/checks/boot-test.md)
records the local diagnostic artifact and single-card recovery procedure.

---

## Engineering source selection and startup evidence (2026-10-22)

The engineering baseline is selected in `docs/adr/0001-radxa-zero3w-platform.md`
at local commit `2b8efb9`. It retains Buildroot **2026.02.3** and selects
Linux **6.12.114**, U-Boot **2026.01**, the existing rkbin pin with RK3566 DDR
**1.23** / RK3568 BL31 **1.44**, the separate V1.12M/AIC8800D80 DT with patches
through `0005`, and AIC commit `fc7cbdd1791416c2457fa27a59e508bf325c9c3f` with
the six reference-matched D80 firmware/configuration files. Immutable inputs,
hashes, patch order and evidence limits are recorded in the ADR.

Since the last issue update:

- The firmware-readiness predicate now checks live BSP/fdrv initialization,
  normal BSP work mode and the matching D80 SDIO interface/driver. Its 17 host
  tests cover the reference's actual sysfs layout. It was also checked read-only
  on Radxa OS. This is an ordering predicate, not proof of firmware identity or
  UART responsiveness (`9caf011`, `9355a6d`).
- One guarded **Radxa OS 6.1.84** cold start succeeded in this order: readiness
  at 10.677 s, successful bounded HCI Reset at 10.722 s, hciattach active at
  11.156 s and BlueZ active at 11.897 s. Automatic recovery restored the vendor
  configuration; temporary experiment files were removed. Four host tests cover
  rollback failures (`2d35d0d`). These timestamps share one boot's journal
  monotonic clock; this is not Buildroot/mainline cold-start acceptance.
- The AIC-only DT now requests the observed GPIO directions, pulls, Schmitt
  settings and measured drive-register levels. Six compiled-DT tests pass;
  the generic ZERO 3W DTB remains byte-identical (`2247ca3`). The selected DT
  has not been booted. GPIO acquisition and radio behavior on mainline remain
  unverified.

On 2026-10-22, all **40** existing focused tests passed again: 13 UART-helper,
17 readiness, four startup-recovery and six compiled-DT tests. The UART helper
also compiled with the documented strict host warning flags. This rerun did
not rebuild the full kernel or add new physical evidence.

The source-selection capability table now separates source/build evidence
from physical verification for microSD, accessory/uevents, AP and Bluetooth.
The remaining external blocker is the selected firmware's redistribution/source
terms. [radxa-pkg/aic8800#109](https://github.com/radxa-pkg/aic8800/issues/109)
was checked on 2026-10-22: still open, with no comments. No firmware permission
is inferred from package metadata or the act of asking.

Keep #5 open, the ADR Proposed for release, and downstream dependencies intact.
The first acceptance criterion still includes unresolved firmware licensing;
the capability evidence criterion needs tracker review against the ADR before
changing its checkbox. A complete Buildroot image, AP/pairing/coexistence,
accessory negotiation and car/reliability acceptance belong to later issues.

A separate boot-only diagnostic image is now prepared locally, using the
checked U-Boot/kernel/DT and a minimal static BusyBox initramfs. It contains no
radio firmware or modules and is intended to save kernel/hardware snapshots
to a FAT log partition without Wi-Fi or SSH. Ten preparation/artifact tests
pass. The recovery snapshot was reverified in full. The owner then selected
that existing backup as the recovery point and moved the card to the reader.
The diagnostic image was written and all 234,881,024 bytes passed SHA-256
readback verification. The expected boot/log partitions were detected and
safely unmounted; the reader was powered off.

The physical follow-up recovered three separate boot snapshots, all reaching
Linux **6.12.114** diagnostic userspace with the correct model/live-DT GPIO
hogs, UART1 and `fcc00000.usb` UDC. All have expected-kernel/capture markers.
One snapshot records both AIC SDIO functions (`c8a1:0082`, `c8a1:0182`); the
other two are captured earlier during host initialization and do not settle
SDIO reliability. No panic/Oops/BUG/call-trace or priority 0–3 messages occur
in the saved logs. The observed LED-off behavior is consistent with the
diagnostic's intentional poweroff, whose final steps are after the saved dmesg.
These are brief boot-only snapshots, not acceptance cold starts or tests of
radio/accessory operation. Raw logs/live DTs are preserved privately; full-card
restoration to the owner-selected reference snapshot follows evidence capture.

`main` remains `e7ef1f1`; the source-selection commits through `619536f` on
`feature/radxa-zero3w-hci-reset` and the subsequent local preparation work have
not been pushed. This draft does not imply a push, merge or hardware result.
