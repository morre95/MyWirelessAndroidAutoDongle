# SPDX-License-Identifier: MIT
"""Check the Android Auto frames that aoa-host-test.py exchanges with the phone."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "aoa_host_test", ROOT / "aa_wireless_dongle/board/radxa/zero3w/checks/aoa-host-test.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class VersionFrames(unittest.TestCase):
    def test_request_is_one_unencrypted_control_frame_for_version_1_1(self):
        self.assertEqual(tool.version_request(), bytes.fromhex("0003 0006 0001 0001 0001"))

    def test_response_yields_version_and_status(self):
        frame = bytes.fromhex("0003 0008 0002 0001 0007 0000")
        self.assertEqual(tool.parse_version_response(frame), (1, 7, 0))

    def test_other_messages_are_rejected(self):
        for frame in (bytes.fromhex("0003 0008 0001 0001 0007 0000"),  # a request
                      bytes.fromhex("0103 0008 0002 0001 0007 0000"),  # another channel
                      bytes.fromhex("0003 0002 0002")):  # truncated
            with self.subTest(frame=frame.hex()):
                with self.assertRaises(ValueError):
                    tool.parse_version_response(frame)

    def test_usbfs_ioctl_numbers_match_the_kernel(self):
        self.assertEqual(tool.USBDEVFS_BULK, 0xC0185502)
        self.assertEqual(tool.USBDEVFS_CLAIMINTERFACE, 0x8004550F)


if __name__ == "__main__":
    unittest.main()
