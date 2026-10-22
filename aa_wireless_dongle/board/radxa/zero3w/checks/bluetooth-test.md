# Mainline Bluetooth attachment diagnostic — 2026-10-22

## Selected next diagnostic: native process control (v4)

V3 registered hci0, then falsely failed its attachment gate because the minimal
BusyBox has neither a kill applet nor an ash kill builtin. Failed signal probes
also led cleanup into a wait on a live process. The
[v3 result](../../../../../docs/handoffs/2026-10-22-radxa-bluetooth-uart-capture.md)
records the physical evidence and recovery. Host PATH had hidden this dependency
in the previous stage fixtures, including the QEMU-shell cases.

The selected unflashed private candidate is
`buildroot/output/radxa-bluetooth-test-20261022-v4/radxa-bluetooth-test.img`,
234,881,024 bytes, SHA-256
`4a0186870d04bbca2bf73ded9b20f7ab0926723123c9e2820e4d4ea9603776ce`.
Do not use the earlier v2/v3 candidates for another physical test. Complete the
current reference restoration/readback/runtime recovery before card movement.

V4 adds `aic-bounded-run --signal 0|TERM|KILL PID`. It accepts only decimal
PIDs above 1 through INT_MAX; group, init and malformed targets are rejected.
Zero means a successful operation/live probe, 1 means ESRCH (absent), 2 means
invalid arguments, and 3 means another signal error. An EPERM zero-signal probe
still means the process exists. The stage requires a working native probe at
startup and only waits for an absent or zombie child; unexpected probe errors
stay bounded and fail cleanup. No optional shell signal command is required.
Snapshot/deadline/cleanup budgets, kernel/DT/firmware/modules, baudrate/flow,
BlueZ and actual pairing acceptance remain unchanged from v3.

All **41 host checks pass**: eight native-helper, fourteen stage, nine agent
and ten packed-image checks. The stage PATH contains only explicit fixture
commands and the real native helper, with no host kill fallback. The new
regression using the actual ARM64 ash first timed out on the old stage and now
reaches the pairing fixture and completes cleanup. Eight helper and fourteen
stage checks also pass with the actual ARM64 helper under QEMU and target ash.
The packed-image suite extracts both actual executables, reproduces missing
shell kill and successfully probes through the native helper. Independent review
has no remaining required findings; an ESRCH-result mutation fails the native
test. These results validate the dependency fix, not physical BlueZ/pairing.

The same compile command below builds the updated helper. Current pinned source
SHA-256 is `35755804d17e4e0222dc73f4bcb3c4caa7f1bce6935c9aab9c74ffafa7932107`;
ARM64 executable SHA-256 is
`a956293998341b27230272a645282c3c0db339a76be54bb81ea77b91ca6ddd20`.
The previous helper binary is retained privately as
`radxa-bluetooth-test-prep/aic-bounded-run-v3`; source and packed v3 artifact
remain preserved. V4 has not been written or physically tested.

## Historical follow-up: UART failure capture (v3)

The v2 physical test passed firmware readiness/HCI Reset but failed the
`hci_attach` gate (11), before D-Bus/BlueZ/pairing. Final capture was absent.
Full reference restoration and its runtime checks passed. See the
[v2 hardware record](../../../../../docs/handoffs/2026-10-22-radxa-bluetooth-test.md).

The next selected private image is
`buildroot/output/radxa-bluetooth-test-20261022-v3/radxa-bluetooth-test.img`,
234,881,024 bytes, SHA-256
`9d30fc90d6c2ef38dd6ab2bba332677727a68f422bd6d4e0155ae690f731a32a`.
The `v3-pre-review` and `v3-pre-pairing-bound` bundles are superseded local
candidates. The detailed current checkpoint is the
[UART capture handoff](../../../../../docs/handoffs/2026-10-22-radxa-bluetooth-uart-capture.md).

V3 keeps the same kernel/DT/boot chain, radio payload, eight Bluetooth modules,
BlueZ 5.79, 1.5 Mbaud/RTS-CTS attachment and 180-second pairing agent. It adds
snapshots before attachment, at failure **before cleanup**, and after cleanup.
They record kernel logs, the attachment PID's status/wchan/syscall/stack,
module/interrupt/controller state and the live DT. No packet, process-memory or
bond-storage capture is added. The meaning of process state and wait/stack
files follows the [kernel proc documentation](https://www.kernel.org/doc/html/v6.12/filesystems/proc.html).

`aic-bounded-run.c` supervises each snapshot (5 seconds), Bluetooth module load
(10 seconds), pairing agent (210 seconds, including its existing internal
180-second window) and final snapshot (10 seconds) independently. It kills the
worker's process group at the deadline and uses only nonblocking child reaping,
with a 200 ms reap grace. Nested supervisors fail before starting a worker;
there is no enclosing supervisor around the entire Bluetooth shell stage.
Cleanup allows one second after TERM and three bounded one-second polls after
KILL. It waits only for exited/zombie children and records any unreaped PID as
failure 16, preserving the original stage failure in `failure-result.txt`.
These budgets do not guarantee recovery from a system/kernel/storage hang.

`CAPTURE_FINISHED=1` now requires final snapshot exit zero; individual artifact
read/redirection failures produce a failed snapshot status. Capture completion
still does not establish pairing success. Inspect `failure-process.txt`,
`failure-kernel.txt`, `failure-snapshot-exit.txt`, `failure-result.txt` and
`cleanup-result.txt`, alongside the existing success gates. A zero-byte
`hciattach.log` is not enough to locate the blocked operation.

All **35 local checks pass**: six native supervisor, eleven stage, nine agent
and nine actual-image checks. Six supervisor tests also pass with the actual
ARM64 executable under QEMU, and eleven stage tests pass with the target
ARM64 BusyBox ash. This includes simulated non-terminating cleanup, child exit
status, failed snapshot artifacts and rejected nesting; it does not reproduce
an actual uninterruptible task. Independent review reproduced and resolved
false snapshot success and nested-worker escape, and a process-presence
mutation was caught by the stage test. The image has not yet been physically
tested. Use the same identity-checked writer/recovery and one-start/twelve-minute
physical procedure below.

Build the helper with the same pinned Buildroot external toolchain and strict
warnings used for the pairing agent, without changing userspace inputs:

```sh
docker run --rm --network none \
  --mount "type=bind,source=$PWD,target=/app,readonly" \
  --mount "type=bind,source=$PWD/buildroot/output,target=/app/buildroot/output" \
  --workdir /app aawg-buildroot:latest \
  /app/buildroot/output/radxa-bluetooth-userspace-container/host/bin/aarch64-linux-gcc \
  -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wshadow \
  aa_wireless_dongle/board/radxa/zero3w/checks/aic-bounded-run.c \
  -o /app/buildroot/output/radxa-bluetooth-test-prep/aic-bounded-run
```

The generator pins source SHA-256
`6dcc09c264112d83e5f0590246936d0f76817a30b4530a21b2eaa482323b5e4f`
and executable SHA-256
`bf4019e9511459d91b8cdde4f1e1b84d4e2a0bc9a9b907d53a4a86e73b3c3c6a`.
Assemble into a fresh directory with `make-bluetooth-test.py --output ...` and
set `RADXA_BLUETOOTH_TEST_DIR` for the actual-image suite when using a different
path. Run `tests/radxa_bounded_run_test.py`, `tests/radxa_bluetooth_stage_test.py`,
`tests/radxa_pairing_agent_test.py` and `tests/radxa_bluetooth_image_test.py`.

## Historical v2 preparation

Preparation follows the owner's authorization after the successful
[radio reset test](../../../../../docs/handoffs/2026-10-22-radxa-radio-test.md).
The reference Radxa OS is left unchanged during local build preparation.
The existing owner-selected full-card backup remains the recovery point. The
owner has an Android phone available for the manual pairing step.

## First checkpoint: userspace

Build a separate, non-shipping userspace with Buildroot 2026.02.3's pinned
Bootlin AArch64 glibc profile, BlueZ **5.79** and D-Bus **1.14.10**. Normal source
hash checking remains mandatory. The diagnostic defconfig does not build or
change Linux/U-Boot and does not change any Pi target. It reuses the earlier
minimal BusyBox configuration and selects hciattach/btmon tools. The private
download directory avoids the old container build's unavailable download path.

```sh
docker run --rm --name aawg-radxa-bt-userspace \
  --mount "type=bind,source=$PWD,target=/app,readonly" \
  --mount "type=bind,source=$PWD/buildroot/output,target=/app/buildroot/output" \
  --workdir /app/buildroot aawg-buildroot:latest bash -ec '
    make O=output/radxa-bluetooth-userspace-container \
      BR2_DEFCONFIG=/app/aa_wireless_dongle/board/radxa/zero3w/checks/bluetooth-test_defconfig defconfig
    make O=output/radxa-bluetooth-userspace-container -j8
  '
```

This userspace archive alone is **not** the card image. The subsequent diagnostic
must reuse the checked Linux 6.12.114/DT/U-Boot and radio inputs, add the matching
Bluetooth kernel-module dependency closure, preserve the successful radio gate,
then require UART attachment and a powered BlueZ adapter before reporting success.
No firmware distribution, radio acceptance or actual phone pairing is implied.

## Startup contract and evidence

Use `hciattach -n -s 1500000 /dev/ttyS1 any 1500000 flow` after successful firmware
readiness/reset, keep that foreground process alive, wait for `hci0`, and only
then start bluetoothd with a local system D-Bus. Require `org.bluez.Adapter1`
and a successful `Powered=true` property write/readback. Record daemon output,
monotonic stages, module/kernel state and adapter properties on the existing
diagnostic log partition. Preserve failure evidence and clean up child processes
before the capture/poweroff path. Timeouts do not guarantee recovery from an
uninterruptible kernel task.

The pairing agent uses a 180-second, headless `NoInputNoOutput` window named
`Radxa Mainline Test`; the owner confirms pairing on the phone. Only an actual
BlueZ `Device1.Paired=true` event plus property readback may pass. Close
discoverability/pairability after the first paired device or timeout. Do not
mark devices trusted or authorize application profiles. Pairing keys live only
in this diagnostic's RAM filesystem and are not a persistent dongle setup.
Classical Bluetooth is enabled, but LE/RFCOMM are disabled in the existing
kernel; a passing pairing test does not establish the Android Auto transport.
AP/channel operation follows review of the earlier regulatory warnings. Until the final
image and checks pass, leave the owner's card/reference untouched.

Source guidance: [Buildroot external toolchain/out-of-tree manual](https://buildroot.org/downloads/manual/manual.html),
[BlueZ UART attachment](https://github.com/bluez/bluez/blob/master/doc/hciattach.rst),
and [BlueZ adapter API](https://github.com/bluez/bluez/blob/master/doc/org.bluez.Adapter.rst).

## Prepared image and verification

The selected private artifact is
`buildroot/output/radxa-bluetooth-test-20261022-v2/radxa-bluetooth-test.img`,
**234,881,024 bytes**, SHA-256:

```text
a4f10f4159a11a7a47dac12b94599717eb2aa192f3285b5971c9440a7280e423
```

The local build completed with mandatory source hashes. Initial host-only
attempts stopped on inherited `LD_LIBRARY_PATH` and missing `bc`; their logs
are preserved privately. The project container completed the build without
changing the host environment or bypassing dependency/hash checks.

Compile `aic-pairing-test.c` inside the same mounted container with its
`host/bin/aarch64-linux-gcc`, `-std=c11 -O2 -Wall -Wextra -Werror -Wconversion
-Wshadow` and the target `gio-2.0` pkg-config flags. Set
`PKG_CONFIG_SYSROOT_DIR` to the userspace output's `staging` directory and
`PKG_CONFIG_LIBDIR` to its `staging/usr/lib/pkgconfig:staging/usr/share/pkgconfig`.
The local compile command/log are preserved in
`radxa-bluetooth-test-prep/build-agent.py` and `agent-build.log`.
The checked source hash is
`beea11866d637d51187407e10400e6e1ecff9f347dcd7fcf773e67d750bf8c71`;
the ARM64 binary hash is
`a26e9214a010a0a6c1e291fb40e530a805adcb640395c3e9a54e25c75666ff1a`.

`make-bluetooth-test.py` refuses existing/unsafe output directories and changed
userspace/config/agent/module inputs. It validates vermagic and the eight-module
dependency order, then composes Buildroot's checked newc archive, the unchanged
radio payload and the final init/agent/module layer. Linux's
[initramfs format](https://www.kernel.org/doc/html/v6.12/driver-api/early-userspace/buffer-format.html)
allows concatenated newc archives; the final regular `/init` replaces the earlier
radio init. `/lib` remains a directory in this selected userspace. Each component,
extra payload and complete image is hashed in `manifest.json`; per-boot
`inputs.json` records the selected payloads. Build-time physical-test flags stay
false until separate hardware evidence exists. Output hashes identify this
experiment, not a reproducible release; rebuilt inputs require explicit review.

```sh
python3 aa_wireless_dongle/board/radxa/zero3w/checks/make-bluetooth-test.py \
  --output buildroot/output/radxa-bluetooth-test-rebuilt
RADXA_BLUETOOTH_TEST_DIR=buildroot/output/radxa-bluetooth-test-rebuilt \
  python3 tests/radxa_bluetooth_image_test.py
```

All **24 checks pass**: nine native private-D-Bus agent cases, seven stage
fixtures and eight actual-image checks. The latter inspect all three archives,
the packed boot partition, module sets, current scripts, ARM64 programs and
D-Bus policy, and reject changed userspace before creating output. Stage tests
also check that child processes are gone after every run. Mutation testing
detected acceptance of a false `Paired` property. The same nine private-D-Bus
cases also pass with the actual ARM64 agent under QEMU against its target GIO
libraries. QEMU additionally runs BlueZ/D-Bus version checks and hciattach's
type list; it does not prove HCI/UART or phone operation. This image has not
been flashed or booted.

## Operator-assisted card test

Use the earlier identity checks, exact image readback, private read-only capture
and complete-card restoration procedure. The owner-selected prior backup is
still the recovery source. Preserve evidence before restoration and recheck
the running reference afterwards. Reidentify reader/device paths each time.

Before powering the test card, open Bluetooth settings on the Android phone and
prepare to search. Use the same computer USB-A–USB-C power setup and **one start**.
When `Radxa Mainline Test` appears, request pairing and confirm on the phone
within its **three-minute window**. Record the phone's displayed result. A saved
old bond for this same test/controller may need removal before a fresh attempt.

Allow **twelve minutes** before disconnecting power and returning the card to
the reader, even if the LED goes dark earlier. This covers the existing radio
and new dependency/daemon/agent budgets; a kernel task stuck in uninterruptible
sleep still requires manual recovery. The program captures and powers off after
the result; LED state alone is not evidence of success. Do not retry blindly.

Require `RADIO_RESET_RESULT=success`, `BT_PAIRING_RESULT=success`, agent exit zero,
the successful paired-property readback, and completed capture. Files include
`radio.log`, Bluetooth progress/result, `hciattach.log`, `dbus.log`,
`bluetoothd.log`, `pairing.log`, `pairing-exit.txt`, `bluez-objects.txt`, kernel
logs and `live.dtb`. Hardware state is captured after child cleanup; hci0 can
therefore already be absent there. Adapter/device evidence is captured while
BlueZ is still alive. A completed capture is not by itself a successful pairing.

Captured diagnostics contain radio/phone identifiers and remain private.
Raw btmon pairing traces are excluded because they can contain link keys; the
agent never prints passkeys, and pairing storage stays in RAM. Remove the test
bond from the phone after evidence collection, since restoring Radxa OS restores
the earlier controller-side state. Profile connection, persistent pairing,
RFCOMM, AP/coexistence and Android Auto require later tests.
