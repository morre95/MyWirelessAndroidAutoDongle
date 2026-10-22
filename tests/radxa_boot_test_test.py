# SPDX-License-Identifier: MIT
"""Guard offline image preparation and inspect the actual prepared artifact."""
import hashlib
import gzip
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "aa_wireless_dongle/board/radxa/zero3w/checks/make-boot-test.py"
spec = importlib.util.spec_from_file_location("boot_test", SCRIPT)
boot = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(boot)


class PreparationGuards(unittest.TestCase):
    def test_init_refuses_execution_outside_pid_one(self):
        result = subprocess.run(["sh", str(SCRIPT.with_name("boot-test-init.sh"))],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("PID 1", result.stderr)

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=boot.OUTPUT_ROOT) as tmp:
            marker = Path(tmp) / "keep"
            marker.write_text("reference data")
            with self.assertRaises(ValueError):
                boot.validate_output(Path(tmp))
            self.assertEqual(marker.read_text(), "reference data")

    def test_output_outside_ignored_build_tree_is_rejected(self):
        with self.assertRaises(ValueError):
            boot.validate_output(Path("/dev/radxa-must-never-be-written"))

    def test_symlink_to_another_directory_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=boot.OUTPUT_ROOT) as tmp:
            link = Path(tmp) / "link"
            link.symlink_to(boot.OUTPUT_ROOT, target_is_directory=True)
            with self.assertRaises(ValueError):
                boot.validate_output(link / "radxa-test-output")

    def test_changed_input_cannot_silently_replace_selected_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "Image"
            artifact.write_bytes(b"selected kernel")
            expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
            boot.require_hash(artifact, expected)
            artifact.write_bytes(b"different kernel")
            with self.assertRaises(ValueError):
                boot.require_hash(artifact, expected)

    def test_dynamic_or_wrong_architecture_init_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "busybox"
            header = bytearray(64)
            header[:6] = b"\x7fELF\x02\x01"
            struct.pack_into("<H", header, 18, 183)
            struct.pack_into("<Q", header, 32, 64)
            struct.pack_into("<HH", header, 54, 56, 1)
            program = bytearray(56)
            struct.pack_into("<I", program, 0, 3)  # PT_INTERP
            binary.write_bytes(header + program)
            with self.assertRaises(ValueError):
                boot.require_static_arm64(binary)
            struct.pack_into("<I", program, 0, 1)  # PT_LOAD
            binary.write_bytes(header + program)
            boot.require_static_arm64(binary)
            struct.pack_into("<H", header, 18, 62)  # x86-64
            binary.write_bytes(header + program)
            with self.assertRaises(ValueError):
                boot.require_static_arm64(binary)


class PreparedImage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(os.environ.get("RADXA_BOOT_TEST_DIR", str(
            boot.OUTPUT_ROOT / "radxa-boot-test-20261022-v3")))
        cls.image = cls.directory / "radxa-boot-test.img"

    def test_manifest_identifies_image_and_generator(self):
        manifest = json.loads((self.directory / "manifest.json").read_text())
        with self.image.open("rb") as stream:
            self.assertEqual(hashlib.file_digest(stream, "sha256").hexdigest(),
                             manifest["image_sha256"])
        self.assertEqual(manifest["generator_sha256"],
                         hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
        self.assertFalse(manifest["radio_firmware_included"])
        self.assertFalse(manifest["physical_test_performed"])

    def test_bootloader_and_partitions_are_in_the_image_without_overlap(self):
        with self.image.open("rb") as stream:
            mbr = stream.read(512)
            self.assertEqual(mbr[510:], b"\x55\xaa")
            for index, expected in enumerate(((0x80, 0x83, 32768, 262144),
                                               (0, 0x0c, 294912, 131072))):
                entry = mbr[446 + index * 16:462 + index * 16]
                self.assertEqual((entry[0], entry[4], *struct.unpack_from("<II", entry, 8)),
                                 expected)
            loader = boot.INPUTS["u-boot-rockchip.bin"][0].read_bytes()
            self.assertLess(64 * 512 + len(loader), 32768 * 512)
            stream.seek(64 * 512)
            self.assertEqual(stream.read(len(loader)), loader)
            for name, sector in (("boot.ext4", 32768), ("logs.fat", 294912)):
                content = (self.directory / name).read_bytes()
                stream.seek(sector * 512)
                self.assertEqual(hashlib.sha256(stream.read(len(content))).digest(),
                                 hashlib.sha256(content).digest())

    def test_boot_files_match_selected_kernel_dtb_and_initramfs(self):
        for name in ("Image", boot.DTB, "initramfs.cpio.gz"):
            result = subprocess.run(["debugfs", "-R", f"cat /{name}",
                                     str(self.directory / "boot.ext4")],
                                    check=True, capture_output=True)
            self.assertEqual(result.stdout, (self.directory / "boot" / name).read_bytes())
            if name in boot.INPUTS:
                self.assertEqual(hashlib.sha256(result.stdout).hexdigest(),
                                 boot.INPUTS[name][1])
        config = subprocess.run(["debugfs", "-R", "cat /extlinux/extlinux.conf",
                                 str(self.directory / "boot.ext4")],
                                check=True, capture_output=True, text=True).stdout
        self.assertIn(f"fdt /{boot.DTB}\n", config)
        self.assertIn("initrd /initramfs.cpio.gz\n", config)
        self.assertIn("rdinit=/init", config)

    def test_initramfs_has_console_and_no_radio_firmware_or_modules(self):
        archive = gzip.decompress((self.directory / "boot/initramfs.cpio.gz").read_bytes())
        result = subprocess.run(["cpio", "-it"], input=archive,
                                capture_output=True, check=True)
        names = set(result.stdout.decode().splitlines())
        self.assertEqual(names, {"bin", "dev", "proc", "sys", "logs", "dev/console",
                                 "dev/null", "bin/busybox", "bin/sh", "init"})
        embedded_init = subprocess.run(["cpio", "-i", "--to-stdout", "init"],
                                       input=archive, capture_output=True, check=True).stdout
        self.assertEqual(embedded_init, SCRIPT.with_name("boot-test-init.sh").read_bytes())
        self.assertEqual((self.directory / "init").read_bytes(),
                         SCRIPT.with_name("boot-test-init.sh").read_bytes())
        boot.require_static_arm64(self.directory / "busybox")


if __name__ == "__main__":
    unittest.main()
