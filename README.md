# Wireless Android Auto Dongle

DIY Wireless Android Auto adapter to use with a car that supports only wired Android Auto using a Raspberry Pi.

This repository consists of the buildroot setup to generate an sd card image to create your own Wireless Android Auto adapter.

## Features
- Native Wireless Android Auto connection to the phone, no extra app needed on the phone.
- Passes through all Android Auto traffic without any modifications to ensure seamless and safe experience.
- Fast bootup, connection under 30 seconds.
- Supports multiple boards (Currently multiple Raspberry Pi boards).

## Supported Hardware
This is currently tested and built for the following Raspberry Pi boards supporting USB OTG.
- **Raspberry Pi Zero W**
- **Raspberry Pi Zero 2 W**
- **Raspberry Pi 3 A+** _(Raspberry Pi 3 B+ is not supported due to lack of USB OTG support.)_
- **Raspberry Pi 4**
- **Raspberry Pi 5**

### In testing
- **Radxa ZERO 3W**: only the tested variant (PCB V1.12M, 1 GB RAM, **no eMMC**, AIC8800D80 radio), booting from microSD. It has passed physical acceptance in a car and stays in testing until its first release is checked, see [Limitations](#limitations). Variants with eMMC or another revision are not supported. The first release containing `radxa-zero3w-sdcard.img.xz` is still to come; until then, [build it yourself](BUILDING.md).

In theory, this can be extended to more hardware in future with these basic requirements.

- The board should support USB OTG or Gadget mode.
- Has Wifi and Bluetooth. External should also work if not in-built.
- Should be able to operate on power provided by the car.

## Install and run
[Download a pre-built sd card image](https://github.com/morre95/MyWirelessAndroidAutoDongle/releases) for your board. You can also [build one yourself](BUILDING.md). Install the image on the SD card using your favorite tool.

Release images are named `<board>-sdcard.img.xz`, for example `radxa-zero3w-sdcard.img.xz`. Newer releases also carry a `.sha256` file next to each image. Download both into the same folder and check the image before flashing:

```shell
sha256sum -c radxa-zero3w-sdcard.img.xz.sha256
```

Most imaging tools, such as Raspberry Pi Imager and balenaEtcher, can flash the `.img.xz` file directly. The image is about 386 MB, so any microSD card will fit it. The Radxa ZERO 3W was tested with a 32 GB SanDisk Ultra card.

You may want to update the country code and other settings that works best for you. See [Configurations](#Configurations)

### First-time connection
- Connect the phone to headunit via USB cable, make sure Android Auto starts. Disconnect phone.
- Connect the board to the car. Make sure to use a data cable, with the USB OTG enabled port on the board.
    - On **Raspberry Pi Zero W** and **Raspberry Pi Zero 2 W**: Use the second micro-usb port marked "USB" and not "PWR".
    - On **Raspberry Pi 3 A+**: Use the only USB-A port with an USB-A to USB-A cable.
    - On **Raspberry Pi 4**, use the USB-C port used for normally powering the board.
    - On **Radxa ZERO 3W**: Use USB-C port 1, the USB 2.0 OTG port that also powers the board, with a USB-C to USB-A data cable to the car. The other USB-C port is a USB 3.0 host port and does not power the board.
- Open Bluetooth settings and pair the new device called `AndroidAuto-Dongle-*` or `WirelessAADongle-*` on your phone.
- After this phone should automatically connect via Wifi and the dongle will connect to the headunit via USB and start Android Auto on the car screen.

### Subsequent connections
From the next time, it should automatically connect to the phone and start Android Auto.

Make sure your Bluetooth and Wifi are enabled on the phone.

## Configurations

Once the image is installed on the SD card, you can see the SD card as `WirelessAA` drive.

Edit the `aawgd.conf` file inside the `WirelessAA` drive using a text editor to update the configurations. The file contains the possible configuration options with their explanations.

The Radxa ZERO 3W runs its Wi-Fi access point on 5 GHz (channel 36); the Raspberry Pi boards use 2.4 GHz. Set `AAWG_COUNTRY_CODE` to the country you drive in.


## Troubleshoot

### Common issues

#### Music or audiobook playback stutters

See [the audio troubleshooting guide](AUDIO-TROUBLESHOOTING.md) for a reversible
TCP buffering comparison and instructions for collecting Wi-Fi/USB diagnostics.

#### Bluetooth and Wifi seems connected, but the phone stuck at "Looking for Android Auto"
The most common issue behind this is either bad USB cable or use of wrong USB port on the device. Make sure:
1. The cable is good quality data cable and not power-only cable
2. You're using the OTG enabled usb port on the board, and not the power-only port.

#### "Device not responding" error on headunit
Make sure that "Wireless Android Auto" is enabled in your phone's Andriod Auto settings. This option is only available and required on some older phones.

### Getting logs
Once you've already tried multiple times and it still does not work, you can ssh into the device and try to get some logs.

- Set a static password by setting the `AAWG_WIFI_PASSWORD` config, and enable SSH by setting the `AAWG_ENABLE_SSH` config. See [the instructions to update the configurations](#Configurations).
- Connect the device to the headunit, let it boot and try to connect once. The logs are not persisted across reboots, so you need to get the logs in the same instance soon after you observe the issue.
- Connect to the device using wifi (SSID: AAWirelessDongle, Password: \<as set in the first step>).
- SSH into the device (username: root, password: password, see relevant defconfigs e.g. [raspberrypi0w_defconfig](aa_wireless_dongle/configs/raspberrypi0w_defconfig)).
- Once you're in, try to have a look at `/var/log/messages` file, it should have most relevant logs to start with. You can also copy the file and attach to issues you create if any.

These steps are the same on the Radxa ZERO 3W, whose access point is on 5 GHz.

## Contribute
[Find or create a new issue](https://github.com/morre95/MyWirelessAndroidAutoDongle/issues) for any bugs or improvements.

Feel free to [Create a PR](https://github.com/morre95/MyWirelessAndroidAutoDongle/pulls) to fix any issues. Refer [BUILDING.md](BUILDING.md) for instructions on how to build locally.

## Support 
Please [consider sponsoring](https://github.com/sponsors/nisargjhaveri) if you find the project useful. Even a small donation helps. This will help continuing fixing issues and getting support for more devices and headunit in future.

In any case, don't forget to star on github and spread the word if you think this project might be useful to someone else as well.

## Limitations
This is currently tested with very limited set of headunits and cars. Let me know if it does not work with your headunit.

### Radxa ZERO 3W
The Radxa ZERO 3W is in testing. So far it has been tested with one board, one phone (Samsung Galaxy S24) and one car head unit. See the [hardware validation record](docs/hardware-validation/radxa-zero3w.md) for the results.
- From a fully switched-off car, Android Auto started in 21–27 seconds over 10 cold starts, including the head unit's own boot. A Raspberry Pi Zero 2 W in the same car took 16–24 seconds. An earlier series had one start at exactly 30 seconds.
- Only the variant listed under [In testing](#in-testing) is tested. Boards with eMMC are not supported.
- A 50-minute session with navigation and music had no disconnects. No logs were reviewed for it.
