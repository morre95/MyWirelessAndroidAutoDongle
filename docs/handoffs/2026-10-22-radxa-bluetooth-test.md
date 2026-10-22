# Next mainline Bluetooth test — 2026-10-22

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

The next physical step is clean reference shutdown and moving the card to the
reader for identity-checked writing and full image readback. The operator must
be ready on the phone before test power-on, perform one start, confirm pairing
within the three-minute window and allow twelve minutes before card return.
Preserve logs before restoring the selected full-card backup. Remove the phone's
temporary test bond after capture; its controller-side keys are intentionally
not persistent across recovery. Never print/copy link keys into public evidence.
