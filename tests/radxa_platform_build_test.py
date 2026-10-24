# SPDX-License-Identifier: MIT
"""Inspect the radxa-zero3w_defconfig kernel and boot outputs against ADR-0001."""
import hashlib
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEFCONFIG = ROOT / "aa_wireless_dongle/configs/radxa-zero3w_defconfig"
OUTPUT = Path(os.environ.get("RADXA_OUTPUT", str(ROOT / "buildroot/output/radxa-zero3w")))
KERNEL = OUTPUT / "build/linux-6.12.114"
IMAGES = OUTPUT / "images"
RKBIN_COMMIT = "f43a462e7a1429a9d407ae52b4745033034a6cf9"
DDR_SHA256 = "20e4bb076847bd019fcdeb7bdc15bd249890f07ecc76e9937101f22e50950982"
BL31_SHA256 = "65110f822fdbdd0163ce2dabc60591e7a8a0ffbc9471780e29eef0062f9ed7b6"
DDR_OFFSET = 0x800


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DefconfigTests(unittest.TestCase):
    def test_download_hashes_are_enforced(self):
        self.assertIn("BR2_DOWNLOAD_FORCE_CHECK_HASHES=y", DEFCONFIG.read_text().splitlines())

    def test_no_raspberry_pi_boot_inputs_are_imported(self):
        text = DEFCONFIG.read_text().lower()
        for marker in ("raspberrypi", "rpi_firmware"):
            self.assertNotIn(marker, text)


class KernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = set((KERNEL / ".config").read_text().splitlines())

    def assertOption(self, line):
        self.assertIn(line, self.config)

    def test_release_is_the_pinned_kernel(self):
        self.assertEqual((KERNEL / "include/config/kernel.release").read_text().strip(), "6.12.114")

    def test_rockchip_arm64_support_is_built(self):
        self.assertOption("CONFIG_ARM64=y")
        self.assertOption("CONFIG_ARCH_ROCKCHIP=y")

    def test_bluetooth_supports_le_rfcomm_and_h4_uart(self):
        for line in ("CONFIG_BT=m", "CONFIG_BT_BREDR=y", "CONFIG_BT_LE=y", "CONFIG_BT_RFCOMM=m",
                     "CONFIG_BT_HCIUART=m", "CONFIG_BT_HCIUART_H4=y"):
            self.assertOption(line)

    def test_l2cap_getsockopt_reaches_its_iter_callback(self):
        # 6.12.114 gives L2CAP only getsockopt_iter; without board patch 0006 the
        # socket core never calls it and BlueZ cannot register the adapter.
        self.assertIn(".getsockopt_iter = l2cap_sock_getsockopt",
                      (KERNEL / "net/bluetooth/l2cap_sock.c").read_text())
        self.assertIn("err = ops->getsockopt_iter(sock, level, optname, &opt);",
                      (KERNEL / "net/socket.c").read_text())

    def test_bnep_stays_disabled(self):
        self.assertOption("# CONFIG_BT_BNEP is not set")

    def test_accessory_gadget_and_uevents_are_built(self):
        self.assertOption("CONFIG_USB_CONFIGFS_F_ACC=y")
        self.assertOption("CONFIG_USB_CONFIGFS_UEVENT=y")

    def test_gadget_stack_is_built_in_without_a_module_loader(self):
        # The image has no hotplug module loading, so S92usb_gadget needs
        # configfs gadgets, the accessory and FunctionFS present at boot.
        for line in ("CONFIG_USB_DWC3=y", "CONFIG_USB_DWC3_DUAL_ROLE=y", "CONFIG_USB_GADGET=y",
                     "CONFIG_USB_LIBCOMPOSITE=y", "CONFIG_USB_CONFIGFS=y", "CONFIG_USB_F_ACC=y",
                     "CONFIG_USB_F_FS=y", "CONFIG_PHY_ROCKCHIP_INNO_USB2=y"):
            self.assertOption(line)

    def test_image_is_an_arm64_kernel(self):
        self.assertEqual((IMAGES / "Image").read_bytes()[0x38:0x3c], b"ARM\x64")

    def test_aic_device_tree_is_installed(self):
        self.assertGreater((IMAGES / "rk3566-radxa-zero-3w-aic8800d80.dtb").stat().st_size, 0)


class BootloaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rkbin = OUTPUT / f"build/rockchip-rkbin-{RKBIN_COMMIT}/bin/rk35"
        cls.bootloader = (IMAGES / "u-boot-rockchip.bin").read_bytes()

    def test_rkbin_blobs_match_the_selected_files(self):
        self.assertEqual(sha256(self.rkbin / "rk3566_ddr_1056MHz_v1.23.bin"), DDR_SHA256)
        self.assertEqual(sha256(self.rkbin / "rk3568_bl31_v1.44.elf"), BL31_SHA256)

    def test_ddr_blob_is_packed_at_its_rockchip_offset(self):
        ddr = (self.rkbin / "rk3566_ddr_1056MHz_v1.23.bin").read_bytes()
        self.assertEqual(self.bootloader[DDR_OFFSET:DDR_OFFSET + len(ddr)], ddr)


if __name__ == "__main__":
    unittest.main()
