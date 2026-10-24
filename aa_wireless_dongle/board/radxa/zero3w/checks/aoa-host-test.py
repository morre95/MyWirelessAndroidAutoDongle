#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Act as an Android Auto headunit on this PC: switch the dongle to accessory mode.

Waits for the dongle's default gadget, sends the Android Open Accessory (AOA)
handshake, waits for the accessory gadget, then resets the accessory from the
host and checks that it is configured again. Uses only usbfs, so run it as root:

    sudo python3 aoa-host-test.py --log LOGFILE
"""
import argparse
import ctypes
import fcntl
import json
import os
from pathlib import Path
import sys
import time

GOOGLE = 0x18D1
DEFAULT_GADGET = (GOOGLE, 0x4EE1)
ACCESSORY_GADGETS = {(GOOGLE, 0x2D00), (GOOGLE, 0x2D01)}
SYSFS = Path("/sys/bus/usb/devices")

# AOA requests, https://source.android.com/docs/core/interaction/accessories/aoa
AOA_GET_PROTOCOL = 51
AOA_SEND_STRING = 52
AOA_START = 53
AOA_STRINGS = ("Android", "Android Auto", "Android Auto", "2.0.1", "", "")
VENDOR_IN = 0xC0
VENDOR_OUT = 0x40
CONTROL_TIMEOUT_MS = 1000
RESET_SETTLE_S = 2


class CtrlTransfer(ctypes.Structure):
    """struct usbdevfs_ctrltransfer from linux/usbdevice_fs.h."""
    _fields_ = [("bRequestType", ctypes.c_uint8), ("bRequest", ctypes.c_uint8),
                ("wValue", ctypes.c_uint16), ("wIndex", ctypes.c_uint16),
                ("wLength", ctypes.c_uint16), ("timeout", ctypes.c_uint32),
                ("data", ctypes.c_void_p)]


def ioc(direction, number, size):
    return (direction << 30) | (size << 16) | (ord("U") << 8) | number


USBDEVFS_CONTROL = ioc(3, 0, ctypes.sizeof(CtrlTransfer))
USBDEVFS_RESET = ioc(0, 20, 0)


class Log:
    def __init__(self, path):
        self.start = time.monotonic()
        self.file = path.open("x")

    def event(self, name, **fields):
        record = {"t": round(time.monotonic() - self.start, 3), "event": name, **fields}
        line = json.dumps(record)
        print(line, flush=True)
        self.file.write(line + "\n")
        self.file.flush()


def read_attr(device, name):
    path = device / name
    return path.read_text().strip() if path.exists() else None


def find_device(ids):
    """Return the sysfs directory of the only connected device matching ids."""
    matches = []
    for device in SYSFS.iterdir():
        vendor, product = read_attr(device, "idVendor"), read_attr(device, "idProduct")
        if vendor and product and (int(vendor, 16), int(product, 16)) in ids:
            matches.append(device)
    if len(matches) > 1:
        raise SystemExit(f"More than one matching device: {[d.name for d in matches]}")
    return matches[0] if matches else None


def describe(device):
    # Deliberately leaves out the serial number.
    return {"port": device.name, "id": f"{read_attr(device, 'idVendor')}:{read_attr(device, 'idProduct')}",
            "manufacturer": read_attr(device, "manufacturer"), "product": read_attr(device, "product"),
            "speed_mbps": read_attr(device, "speed"), "interfaces": read_attr(device, "bNumInterfaces"),
            "devnum": read_attr(device, "devnum"), "configuration": read_attr(device, "bConfigurationValue")}


def wait_for(log, ids, label, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if device := find_device(ids):
            log.event("enumerated", gadget=label, **describe(device))
            return device
        time.sleep(0.2)
    log.event("timeout", gadget=label, seconds=timeout)
    raise SystemExit(f"{label} gadget did not enumerate within {timeout} s")


def open_node(device):
    node = f"/dev/bus/usb/{int(read_attr(device, 'busnum')):03d}/{int(read_attr(device, 'devnum')):03d}"
    return os.open(node, os.O_RDWR)


def control(fd, request_type, request, index=0, data=b"", length=0):
    buffer = ctypes.create_string_buffer(data, max(len(data), length)) if data or length else None
    transfer = CtrlTransfer(request_type, request, 0, index, len(data) or length, CONTROL_TIMEOUT_MS,
                            ctypes.addressof(buffer) if buffer else None)
    transferred = fcntl.ioctl(fd, USBDEVFS_CONTROL, transfer)
    return buffer.raw[:transferred] if buffer else b""


def switch_to_accessory(log, device):
    fd = open_node(device)
    try:
        version = int.from_bytes(control(fd, VENDOR_IN, AOA_GET_PROTOCOL, length=2), "little")
        log.event("aoa_protocol", version=version)
        if version < 1:
            raise SystemExit("Default gadget does not support AOA")
        for index, value in enumerate(AOA_STRINGS):
            control(fd, VENDOR_OUT, AOA_SEND_STRING, index, value.encode() + b"\0")
        log.event("aoa_strings_sent", count=len(AOA_STRINGS))
        control(fd, VENDOR_OUT, AOA_START)
        log.event("aoa_start_sent")
    finally:
        os.close(fd)


def reset(log, device):
    fd = open_node(device)
    try:
        fcntl.ioctl(fd, USBDEVFS_RESET, 0)
        log.event("host_reset_sent", port=device.name)
    except OSError as error:
        # A reset that makes the device re-enumerate can report ENODEV.
        log.event("host_reset_sent", port=device.name, errno=error.errno)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", type=Path, required=True, help="new JSON-lines log file")
    parser.add_argument("--boot-timeout", type=int, default=180,
                        help="seconds to wait for the default gadget after power-up")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("usbfs control transfers need root; run with sudo")

    log = Log(args.log)
    log.event("waiting", gadget="default")
    default = wait_for(log, {DEFAULT_GADGET}, "default", args.boot_timeout)
    switch_to_accessory(log, default)
    accessory = wait_for(log, ACCESSORY_GADGETS, "accessory", 10)
    reset(log, accessory)
    # A port reset re-enumerates the device in place; the board's uevent log
    # records the gadget side of it.
    time.sleep(RESET_SETTLE_S)
    after = wait_for(log, ACCESSORY_GADGETS, "accessory after reset", 10)
    if not read_attr(after, "bConfigurationValue"):
        raise SystemExit("Accessory is not configured after the reset")
    log.event("passed")


if __name__ == "__main__":
    sys.exit(main())
