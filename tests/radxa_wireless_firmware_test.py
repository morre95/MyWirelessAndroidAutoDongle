# SPDX-License-Identifier: MIT
"""Inspect the AIC8800D80 firmware in the radxa-zero3w_defconfig build against ADR-0001."""
import csv
import hashlib
import os
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "aa_wireless_dongle/configs"
OUTPUT = Path(os.environ.get("RADXA_OUTPUT", str(ROOT / "buildroot/output/radxa-zero3w")))
FIRMWARE_DIR = OUTPUT / "target/lib/firmware/aic8800_fw/SDIO/aic8800D80"
# linux-firmware 20261019, AIC8800D80 U02 v6.9.1.1, and the driver's userconfig
# from radxa-pkg/aic8800 fc7cbdd.
INSTALLED = {
    "fw_adid_8800d80_u02.bin": "a526cbd02fcdc495f049f3ad6b5933cb08cd984b16790c716a060d582fee1a56",
    "fw_patch_8800d80_u02.bin": "be3d13e5cf1adb18a57dc829da34f6bf9450ace5c92b8d9baa39f55ba310318f",
    "fw_patch_table_8800d80_u02.bin": "6fb9284b3d1d6ba88e1495adce7c2da02c0cc8cd0df83a6ca23c2f8a5f0d8a45",
    "fmacfw_8800d80_u02.bin": "ea91583a4b0004d8e8e7fb304b49a85df9468ddca42fb52841e37c7bb825de42",
    "LICENSE.aic": "32abfdc0476b2ddb9942d01b0fbe798a581d4618c88931d50d8e0e8ab142f513",
    "aic_userconfig_8800d80.txt": "56c039d10af63c888b18890f508968a143f034de279fd2c4ec7ee65133e3dbdb",
}
PATCH_TABLE_TAG = b"AICBT_PT_TAG"
PATCH_INFO_TYPE = 0
PATCH_INFO_BASE_PAIRS = 4  # aicbt_patch_info_t fields before ext_patch_nb_addr
VENDOR_TYPE_LIMIT = 1000  # entries the BSP reads without a payload


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch_info_pairs(path):
    """Return the address/value pair count of the table's patch-info entry."""
    raw = path.read_bytes()
    position = 16
    while position < len(raw):
        position += 16  # entry name
        entry_type, pairs = struct.unpack_from("<II", raw, position)
        position += 8
        if entry_type >= VENDOR_TYPE_LIMIT:
            pairs = 0
        if entry_type == PATCH_INFO_TYPE:
            return pairs
        position += pairs * 8
    raise AssertionError("No patch-info entry")


class DefconfigTests(unittest.TestCase):
    def test_radxa_selects_the_firmware(self):
        self.assertIn("BR2_PACKAGE_AIC8800_FIRMWARE=y",
                      (CONFIGS / "radxa-zero3w_defconfig").read_text().splitlines())

    def test_raspberry_pi_targets_do_not_select_the_firmware(self):
        for defconfig in CONFIGS.glob("rpi*_defconfig"):
            self.assertNotIn("AIC8800", defconfig.read_text(), defconfig.name)


class InstalledFirmwareTests(unittest.TestCase):
    def test_only_the_selected_files_are_installed(self):
        self.assertEqual(sorted(p.name for p in FIRMWARE_DIR.iterdir()), sorted(INSTALLED))

    def test_installed_files_match_their_pinned_hashes(self):
        for name, expected in INSTALLED.items():
            self.assertEqual(sha256(FIRMWARE_DIR / name), expected, name)

    def test_patch_table_declares_no_ext_patch(self):
        # The BSP loads fw_patch_8800d80_u02_ext<N>.bin only for a longer info entry.
        table = FIRMWARE_DIR / "fw_patch_table_8800d80_u02.bin"
        self.assertEqual(table.read_bytes()[:len(PATCH_TABLE_TAG)], PATCH_TABLE_TAG)
        self.assertEqual(patch_info_pairs(table), PATCH_INFO_BASE_PAIRS)

    def test_no_other_aic_firmware_location_exists(self):
        others = [p for p in (OUTPUT / "target/lib/firmware").rglob("*8800*")
                  if p.is_file() and p.parent != FIRMWARE_DIR]
        self.assertEqual(others, [])


class LegalInfoTests(unittest.TestCase):
    def test_manifest_declares_the_aic_firmware_license(self):
        with (OUTPUT / "legal-info/manifest.csv").open() as manifest:
            rows = {row["PACKAGE"]: row for row in csv.DictReader(manifest)}
        row = rows["aic8800-firmware"]
        self.assertEqual(row["VERSION"], "20261019")
        self.assertEqual(row["LICENSE"], "LicenseRef-LICENSE.aic")
        self.assertEqual(row["LICENSE FILES"], "LICENSE.aic")


if __name__ == "__main__":
    unittest.main()
