# Testing audio stutter on a Raspberry Pi Zero 2 W

This test compares TCP buffering using the same firmware image. It does not
update the kernel or dependencies. The phone still controls its own TCP socket;
`TCP_NODELAY` here affects responses sent from the Pi to the phone.

## Build and install

If you already have `images/sdcard-raspberrypizero2w-audio-test.img`, use that
prepared image and skip the build commands below. It includes the switchable
TCP setting and diagnostics described here.

From the repository root, build for the Zero 2 W:

```sh
./build.sh rpi02w
```

If this board was built before, force a rebuild of the local daemon first so
Buildroot copies the changed source into its cached build directory:

```sh
docker compose run --rm --no-deps bash make -C output/raspberrypizero2w aawg-rebuild
./build.sh rpi02w
```

The normal build produces `images/sdcard-raspberrypizero2w.img`. Keep a copy of
your previous working image and settings. Flash the test image to a spare SD
card if possible; flashing erases the selected card. Do not overwrite the
phone's or computer's storage.

## Compare buffering settings

On the SD card's `WirelessAA` drive, edit `aawgd.conf`. Start with:

```sh
AAWG_TCP_NODELAY=1
AAWG_PROXY_DIAGNOSTICS=1
```

Keep your existing country code, Wi-Fi channel and connection strategy for both
runs. Play the same downloaded song or audiobook for a few minutes while parked,
with the phone and Pi in the same positions. Record whether stuttering improves.
Then set `AAWG_TCP_NODELAY=0`, reboot, and repeat. Repeat the first setting once
more to check whether an improvement is consistent. A setting of `0` restores
the previous TCP buffering behaviour without reflashing.

The startup log should contain `Proxy settings: TCP_NODELAY=1 diagnostics=1`
(or `TCP_NODELAY=0` for the comparison).

## Save diagnostics before rebooting

For SSH access, also enable `AAWG_ENABLE_SSH=1` and set `AAWG_WIFI_PASSWORD` to
a password you choose (8–63 ASCII characters) in `aawgd.conf`, then reboot.
Connect your computer to `AAWirelessDongle`. The phone should stay connected to
Android Auto. From your computer, capture each run with:

```sh
ssh root@10.0.0.1 aawgd-diagnostics > nodelay-on.txt
```

Use `nodelay-off.txt` for the second run. The image's default SSH login password
is `password`. Keep the computer connected for both comparisons, since adding
a Wi-Fi client changes radio traffic. Capture while playback is active, after
at least 30 seconds, and before restarting the Pi: logs are in RAM and disappear
on reboot. The snapshot does not print your configured Wi-Fi password, but does
include device addresses and logs; review it before sharing publicly.

## What the output means

- `Proxy stats TCP->USB` describes data travelling from phone toward car.
  `write_max_us` and `write_ge20ms` show time spent writing to the USB gadget.
- `Proxy stats USB->TCP` describes responses travelling toward the phone.
  Long writes here indicate pressure on the TCP sending path.
- `read_wait_max_us` includes time waiting for any data and, for TCP, a complete
  protocol frame. Idle periods can be normal. It does not establish packet loss
  or identify an audio channel.
- Timings are in microseconds; `20000` means 20 milliseconds. The 20 ms counter
  is a diagnostic threshold, not an Android Auto playback deadline.
- `Proxy TCP` reports RTT, unacknowledged packets, and cumulative **Pi-side TCP**
  retransmissions for this connection. It does not count all phone-side retries
  or Wi-Fi retries. Compare it with `iw` station counters and kernel logs.
- Each active direction reports at most once every five seconds, plus a final
  summary on disconnect. Reports happen after I/O returns; a permanently blocked
  operation will not produce periodic reports. A successful USB write means
  the driver accepted data, not that the car has played it.
- Some Wi-Fi counters depend on driver support; unavailable survey information
  is not by itself a fault.

If changing TCP buffering makes no difference, compare Wi-Fi channels 1, 6 and
11 separately using `AAWG_WIFI_CHANNEL`. The Zero 2 W's built-in radio supports
2.4 GHz only. Kernel and Wi-Fi firmware updates are a separate comparison after
collecting this baseline.

After testing, disable `AAWG_PROXY_DIAGNOSTICS` and SSH again if no longer needed.
`TCP_NODELAY` defaults to enabled; diagnostics and SSH default to disabled.

## Local regression check

This checks the real TCP socket option and bounded diagnostic logging, without
a Pi or Bluetooth service:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -Iaa_wireless_dongle/package/aawg/src \
    tests/proxy_diagnostics_test.cpp -o /tmp/aawgd-proxy-test
/tmp/aawgd-proxy-test
```
