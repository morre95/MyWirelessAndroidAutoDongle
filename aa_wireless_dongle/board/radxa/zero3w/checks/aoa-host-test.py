#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Act as an Android Auto headunit on this PC: switch the dongle to accessory mode.

Waits for the dongle's default gadget, sends the Android Open Accessory (AOA)
handshake, waits for the accessory gadget, then resets the accessory from the
host and checks that it is configured again. Uses only usbfs, so run it as root:

    sudo python3 aoa-host-test.py --log LOGFILE

With --version-exchange it skips the reset. It instead sends an Android Auto
version request on the accessory's bulk OUT endpoint and requires the phone's
version response on bulk IN, which shows data flowing both ways through aawgd.
"""
import argparse
import ctypes
import fcntl
import json
import os
from pathlib import Path
import struct
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
ACCESSORY_INTERFACE = 0
BULK_TIMEOUT_MS = 30000
BULK_READ_SIZE = 16384

# Android Auto control-channel frame: channel, flags, big-endian payload length,
# then a big-endian message id. Flags 0x03 marks one unencrypted frame.
AA_CONTROL_CHANNEL = 0
AA_SINGLE_FRAME = 0x03
AA_VERSION_REQUEST = 0x0001
AA_VERSION_RESPONSE = 0x0002
AA_VERSION = (1, 1)


class CtrlTransfer(ctypes.Structure):
    """struct usbdevfs_ctrltransfer from linux/usbdevice_fs.h."""
    _fields_ = [("bRequestType", ctypes.c_uint8), ("bRequest", ctypes.c_uint8),
                ("wValue", ctypes.c_uint16), ("wIndex", ctypes.c_uint16),
                ("wLength", ctypes.c_uint16), ("timeout", ctypes.c_uint32),
                ("data", ctypes.c_void_p)]


def ioc(direction, number, size):
    return (direction << 30) | (size << 16) | (ord("U") << 8) | number


class BulkTransfer(ctypes.Structure):
    """struct usbdevfs_bulktransfer from linux/usbdevice_fs.h."""
    _fields_ = [("ep", ctypes.c_uint), ("len", ctypes.c_uint), ("timeout", ctypes.c_uint),
                ("data", ctypes.c_void_p)]


USBDEVFS_CONTROL = ioc(3, 0, ctypes.sizeof(CtrlTransfer))
USBDEVFS_BULK = ioc(3, 2, ctypes.sizeof(BulkTransfer))
USBDEVFS_CLAIMINTERFACE = ioc(2, 15, ctypes.sizeof(ctypes.c_uint))
USBDEVFS_RESET = ioc(0, 20, 0)


def version_request():
    payload = struct.pack(">HHH", AA_VERSION_REQUEST, *AA_VERSION)
    return struct.pack(">BBH", AA_CONTROL_CHANNEL, AA_SINGLE_FRAME, len(payload)) + payload


def parse_version_response(frame):
    """Return (major, minor, status) from a control-channel version response."""
    if len(frame) < 12:
        raise ValueError(f"Frame too short for a version response: {len(frame)} bytes")
    channel, _flags, length, message = struct.unpack_from(">BBHH", frame)
    if channel != AA_CONTROL_CHANNEL or message != AA_VERSION_RESPONSE or length < 8:
        raise ValueError(f"Not a version response: channel {channel}, message {message:#06x}")
    return struct.unpack_from(">HHH", frame, 6)


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


def bulk_endpoints(device):
    """Return the (in, out) bulk endpoint addresses of the accessory interface."""
    endpoints = {}
    for endpoint in (device / f"{device.name}:1.{ACCESSORY_INTERFACE}").glob("ep_*"):
        if read_attr(endpoint, "type") == "Bulk":
            endpoints[read_attr(endpoint, "direction")] = int(read_attr(endpoint, "bEndpointAddress"), 16)
    return endpoints["in"], endpoints["out"]


def bulk(fd, endpoint, data=b"", length=0):
    buffer = ctypes.create_string_buffer(data, max(len(data), length))
    transfer = BulkTransfer(endpoint, len(data) or length, BULK_TIMEOUT_MS, ctypes.addressof(buffer))
    transferred = fcntl.ioctl(fd, USBDEVFS_BULK, transfer)
    return buffer.raw[:transferred]


def exchange_version(log, device):
    endpoint_in, endpoint_out = bulk_endpoints(device)
    fd = open_node(device)
    try:
        fcntl.ioctl(fd, USBDEVFS_CLAIMINTERFACE, ctypes.c_uint(ACCESSORY_INTERFACE))
        request = version_request()
        bulk(fd, endpoint_out, request)
        log.event("version_request_sent", endpoint=f"{endpoint_out:#04x}", bytes=len(request))
        response = bulk(fd, endpoint_in, length=BULK_READ_SIZE)
        major, minor, status = parse_version_response(response)
        log.event("version_response_received", endpoint=f"{endpoint_in:#04x}", bytes=len(response),
                  major=major, minor=minor, status=status)
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
    parser.add_argument("--version-exchange", action="store_true",
                        help="exchange Android Auto version messages instead of resetting")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("usbfs control transfers need root; run with sudo")

    log = Log(args.log)
    log.event("waiting", gadget="default")
    default = wait_for(log, {DEFAULT_GADGET}, "default", args.boot_timeout)
    switch_to_accessory(log, default)
    accessory = wait_for(log, ACCESSORY_GADGETS, "accessory", 10)
    if args.version_exchange:
        exchange_version(log, accessory)
        log.event("passed")
        return
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
