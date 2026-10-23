#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Assemble a local boot-only experiment. Never open a physical block device."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUTPUT_ROOT = ROOT / "buildroot/output"
LINUX = OUTPUT_ROOT / "radxa-platform-check/linux"
BOOTCHAIN = OUTPUT_ROOT / "radxa-bootchain-check"
DTB = "rk3566-radxa-zero-3w-aic8800d80.dtb"
INPUTS = {
    "Image": (LINUX / "arch/arm64/boot/Image",
              "44b9811dbec7199c008ca0cb4317c5b9522a514087aa003a48c36becaa42f597"),
    DTB: (LINUX / f"arch/arm64/boot/dts/rockchip/{DTB}",
          "3bd46eb308d09a4fb62ca7ebe8a522a81de5d9953db094bbf99c106772ae956e"),
    "u-boot-rockchip.bin": (BOOTCHAIN / "images/u-boot-rockchip.bin",
                           "9f98a8e8187f1c5666813684c4f471325c74e87104773e8b84bdaad5eb531fc6"),
}


def require_hash(path, expected):
    if not path.is_file():
        raise ValueError(f"Missing regular input file: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"Input differs from selected experiment: {path}")
    return actual


def validate_output(path):
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Output path must not traverse symlinks")
    path = path.resolve()
    if not path.is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("Output must be under ignored buildroot/output")
    if path.exists():
        raise ValueError("Output already exists; choose a new directory")
    return path


def require_static_arm64(path):
    if not path.is_file():
        raise ValueError("BusyBox input must be a regular file")
    data = path.read_bytes()
    if (len(data) < 64 or data[:6] != b"\x7fELF\x02\x01" or
            struct.unpack_from("<H", data, 18)[0] != 183):
        raise ValueError("BusyBox must be a little-endian ARM64 ELF")
    offset = struct.unpack_from("<Q", data, 32)[0]
    size, count = struct.unpack_from("<HH", data, 54)
    if size != 56 or not count or offset + size * count > len(data):
        raise ValueError("Invalid ELF program headers")
    kinds = [struct.unpack_from("<I", data, offset + size * i)[0]
             for i in range(count)]
    if 1 not in kinds or 2 in kinds or 3 in kinds:
        raise ValueError("BusyBox must be static, without interpreter/dynamic segments")


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def pack_disk(output):
    image = output / "radxa-boot-test.img"
    with image.open("xb") as stream:
        stream.truncate(224 * 1024 * 1024)
    run("sfdisk", str(image), input=(
        "label: dos\nlabel-id: 0xa1c00005\nunit: sectors\n"
        "start=32768,size=262144,type=83,bootable\n"
        "start=294912,size=131072,type=c\n"), text=True,
        stdout=subprocess.DEVNULL)
    bootfs, logfs = output / "boot.ext4", output / "logs.fat"
    for path, megs in ((bootfs, 128), (logfs, 64)):
        with path.open("xb") as stream:
            stream.truncate(megs * 1024 * 1024)
    run("mkfs.ext4", "-q", "-F", "-L", "AICBOOT",
        "-O", "^64bit,^metadata_csum,^orphan_file",
        "-d", str(output / "boot"), str(bootfs))
    run("mkfs.fat", "-F", "32", "-n", "AICBOOTLOGS", str(logfs))
    with image.open("r+b") as stream:
        for path, offset in ((INPUTS["u-boot-rockchip.bin"][0], 64 * 512),
                             (bootfs, 32768 * 512), (logfs, 294912 * 512)):
            stream.seek(offset)
            with path.open("rb") as source:
                shutil.copyfileobj(source, stream)
    return image


def assemble(output, busybox):
    output = validate_output(output)
    busybox = busybox.resolve(strict=True)
    require_static_arm64(busybox)
    for path, expected in INPUTS.values():
        require_hash(path, expected)
    config = (LINUX / ".config").read_text().splitlines()
    for option in ("BLK_DEV_INITRD", "RD_GZIP", "DEVTMPFS", "PROC_FS", "SYSFS",
                   "MMC_DW_ROCKCHIP", "EXT4_FS", "VFAT_FS", "MSDOS_PARTITION",
                   "NLS_CODEPAGE_437", "NLS_ISO8859_1"):
        if f"CONFIG_{option}=y" not in config:
            raise ValueError(f"Kernel needs built-in CONFIG_{option}")
    for tool in ("mkfs.ext4", "mkfs.fat", "sfdisk", "qemu-aarch64-static"):
        if not shutil.which(tool):
            raise ValueError(f"Missing host tool: {tool}")
    applets = run("qemu-aarch64-static", str(busybox), "--list",
                  capture_output=True, text=True).stdout.splitlines()
    required = "sh cat cp dmesg ls mkdir mount umount sleep sync uname poweroff blkid"
    if not set(required.split()).issubset(applets):
        raise ValueError("BusyBox lacks required diagnostic applets")
    init = Path(__file__).with_name("boot-test-init.sh")
    run("qemu-aarch64-static", str(busybox), "ash", "-n", str(init))
    output.mkdir(mode=0o700)
    boot = output / "boot"
    (boot / "extlinux").mkdir(parents=True)
    for name in ("Image", DTB):
        shutil.copyfile(INPUTS[name][0], boot / name)
    shutil.copyfile(busybox, output / "busybox")
    shutil.copyfile(init, output / "init")
    entries = [f"dir /{name} 0755 0 0" for name in
               ("bin", "dev", "proc", "sys", "logs")]
    entries += ["nod /dev/console 0600 0 0 c 5 1",
                "nod /dev/null 0666 0 0 c 1 3",
                "file /bin/busybox busybox 0755 0 0",
                "slink /bin/sh busybox 0777 0 0",
                "file /init init 0755 0 0"]
    (output / "initramfs.list").write_text("\n".join(entries) + "\n")
    cpio = run(str(LINUX / "usr/gen_init_cpio"), "-t", "0", "initramfs.list",
               cwd=output, capture_output=True).stdout
    (boot / "initramfs.cpio.gz").write_bytes(gzip.compress(cpio, mtime=0))
    (boot / "extlinux/extlinux.conf").write_text(
        "default diagnostic\ntimeout 10\nlabel diagnostic\n"
        "    linux /Image\n"
        f"    fdt /{DTB}\n"
        "    initrd /initramfs.cpio.gz\n"
        "    append console=ttyS2,1500000n8 earlycon rdinit=/init panic=0\n")
    image = pack_disk(output)
    manifest = {
        "purpose": "Private boot-only experiment; hardware validation pending",
        "git_head": run("git", "rev-parse", "HEAD", cwd=ROOT,
                        capture_output=True, text=True).stdout.strip(),
        "inputs_sha256": {name: expected for name, (_, expected) in INPUTS.items()},
        "busybox_sha256": hashlib.sha256(busybox.read_bytes()).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "kernel_config_sha256": hashlib.sha256((LINUX / ".config").read_bytes()).hexdigest(),
        "init_sha256": hashlib.sha256(init.read_bytes()).hexdigest(),
        "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "radio_firmware_included": False,
        "physical_test_performed": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "SHA256SUMS").write_text(f"{manifest['image_sha256']}  {image.name}\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--busybox", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(assemble(args.output, args.busybox))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Boot-test preparation refused/failed: {error}\n")
