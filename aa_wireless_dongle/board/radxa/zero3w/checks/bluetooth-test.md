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
