# Mainline Bluetooth attachment diagnostic — 2026-10-22

Preparation follows the owner's authorization after the successful
[radio reset test](../../../../../docs/handoffs/2026-10-22-radxa-radio-test.md).
The reference Radxa OS remains running while local build preparation proceeds.
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
