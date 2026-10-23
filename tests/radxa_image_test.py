# SPDX-License-Identifier: MIT
"""Inspect the radxa-zero3w microSD image: layout, boot files and mounts."""
import os
import re
from pathlib import Path
import struct
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(os.environ.get("RADXA_OUTPUT", str(ROOT / "buildroot/output/radxa-zero3w")))
IMAGES = OUTPUT / "images"
HOST = OUTPUT / "host"
DTB = "rk3566-radxa-zero-3w-aic8800d80.dtb"
SECTOR = 512
MIB = 1024 * 1024
UBOOT_OFFSET = 32 * 1024


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def partitions(image):
    with image.open("rb") as stream:
        mbr = stream.read(SECTOR)
    entries = []
    for index in range(4):
        boot, kind, start, size = struct.unpack_from("<B3xB3xII", mbr, 446 + 16 * index)
        if kind:
            entries.append((boot, kind, start * SECTOR, size * SECTOR))
    return mbr[510:512], entries


class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image = IMAGES / "sdcard.img"
        cls.signature, cls.parts = partitions(cls.image)

    def test_dos_table_has_boot_rootfs_and_persist(self):
        self.assertEqual(self.signature, b"\x55\xaa")
        self.assertEqual([(boot, kind) for boot, kind, _, _ in self.parts],
                         [(0x80, 0x0C), (0, 0x83), (0, 0x83)])

    def test_boot_partition_starts_at_16_mib(self):
        self.assertEqual(self.parts[0][2], 16 * MIB)

    def test_bootloader_is_raw_at_sector_64_before_the_first_partition(self):
        bootloader = (IMAGES / "u-boot-rockchip.bin").read_bytes()
        with self.image.open("rb") as stream:
            stream.seek(UBOOT_OFFSET)
            self.assertEqual(stream.read(len(bootloader)), bootloader)
        self.assertLessEqual(UBOOT_OFFSET + len(bootloader), self.parts[0][2])

    def test_partitions_hold_the_built_filesystems(self):
        with self.image.open("rb") as stream:
            for (_, _, start, size), name in zip(self.parts, ("boot.vfat", "rootfs.ext4",
                                                              "persist.ext4")):
                expected = (IMAGES / name).read_bytes()
                stream.seek(start)
                self.assertEqual(size, len(expected), name)
                self.assertEqual(stream.read(size), expected, name)


class BootPartitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vfat = IMAGES / "boot.vfat"

    def mtools(self, tool, *args):
        return run(str(HOST / f"bin/{tool}"), "-i", str(self.vfat), *args)

    def test_label_is_the_computer_visible_name(self):
        self.assertIn("WirelessAA", self.mtools("mlabel", "-s", "::"))

    def test_boot_files_are_present(self):
        listing = self.mtools("mdir", "-b", "-/", "::")
        for name in ("::/aawgd.conf", "::/Image", f"::/{DTB}", "::/extlinux/extlinux.conf"):
            self.assertIn(name, listing.split())

    def test_extlinux_boots_the_aic_tree_from_mmcblk1(self):
        conf = self.mtools("mtype", "::/extlinux/extlinux.conf")
        self.assertIn("linux /Image", conf)
        self.assertIn(f"fdt /{DTB}", conf)
        self.assertIn("root=/dev/mmcblk1p2", conf)
        self.assertIn("console=ttyS2,1500000n8", conf)


class RootfsTests(unittest.TestCase):
    def debugfs(self, request):
        result = subprocess.run([str(HOST / "sbin/debugfs"), "-R", request,
                                 str(IMAGES / "rootfs.ext4")],
                                check=True, capture_output=True, text=True)
        return result.stdout + result.stderr

    def test_fstab_mounts_only_microsd_partitions(self):
        mounts = {fields[1]: fields[0] for fields in
                  (line.split() for line in self.debugfs("cat /etc/fstab").splitlines())
                  if fields and not fields[0].startswith("#")}
        self.assertEqual(mounts["/boot"], "/dev/mmcblk1p1")
        self.assertEqual(mounts["/persist"], "/dev/mmcblk1p3")

    def test_configuration_points_at_the_boot_partition(self):
        self.assertIn('Fast link dest: "/boot/aawgd.conf"', self.debugfs("stat /etc/aawgd.conf"))

    def test_no_raspberry_pi_modules_script(self):
        self.assertIn("File not found", self.debugfs("stat /etc/init.d/S00modules"))


class DeviceTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = run(str(HOST / "bin/dtc"), "-q", "-I", "dtb", "-O", "dts", str(IMAGES / DTB))

    def alias(self, name):
        return re.search(rf'^\t\t{name} = "([^"]+)";', self.source, re.M).group(1)

    def node(self, path):
        name = path.rsplit("/", 1)[1]
        return re.search(rf"^\t{re.escape(name)} {{\n(.*?)^\t}};", self.source, re.M | re.S).group(1)

    def test_microsd_controller_is_mmc1(self):
        self.assertEqual(self.alias("mmc1"), "/mmc@fe2b0000")
        self.assertIn('status = "okay";', self.node(self.alias("mmc1")))

    def test_emmc_controller_is_disabled(self):
        self.assertIn('status = "disabled";', self.node(self.alias("mmc0")))


if __name__ == "__main__":
    unittest.main()
