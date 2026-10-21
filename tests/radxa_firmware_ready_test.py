# SPDX-License-Identifier: MIT
"""Exercise the readiness predicate against an isolated sysfs-shaped tree."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / (
    "aa_wireless_dongle/board/radxa/zero3w/checks/aic-firmware-ready.sh"
)


class FirmwareReadyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.write("module/aic8800_bsp/initstate", "live\n")
        self.write("module/aic8800_fdrv/initstate", "live\n")
        self.write("module/aic8800_bsp/parameters/testmode", "0\n")
        self.write("devices/platform/aic-bsp/cpmode",
                   "Support mode value:\n  0: work\nCurrent: 0, firmware info:\n")
        self.device = self.root / "devices/mmc_host/mmc1/mmc1:0001/mmc1:0001:1"
        self.device.mkdir(parents=True)
        self.write(self.device / "vendor", "0xc8a1\n")
        self.write(self.device / "device", "0x0082\n")
        driver = self.root / "bus/sdio/drivers/aicwf_sdio"
        driver.mkdir(parents=True)
        (driver / "module").symlink_to(self.root / "module/aic8800_fdrv")
        (self.device / "driver").symlink_to(driver)
        netdev = self.device / "net/wlan0"
        netdev.mkdir(parents=True)
        (netdev / "device").symlink_to(self.device)
        (self.root / "class/net").mkdir(parents=True)
        (self.root / "class/net/wlan0").symlink_to(netdev)

    def write(self, path, contents):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)

    def run_gate(self, *args):
        return subprocess.run(
            ["sh", str(SCRIPT), *args],
            env={**os.environ, "RADXA_SYSFS_ROOT": str(self.root)},
            capture_output=True, text=True, timeout=2,
        )

    def assert_not_ready(self):
        result = self.run_gate()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("not ready:", result.stderr)

    def test_complete_initialization_is_ready(self):
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AIC firmware load ordering ready", result.stdout)

    def test_module_directory_alone_is_not_ready(self):
        (self.root / "module/aic8800_fdrv/initstate").unlink()
        self.assert_not_ready()

    def test_interface_visible_before_module_completion_is_not_ready(self):
        for module in ("aic8800_bsp", "aic8800_fdrv"):
            for state in ("coming", "going", "", "unknown"):
                with self.subTest(module=module, state=state):
                    self.write(f"module/{module}/initstate", state + "\n")
                    self.assert_not_ready()
            self.write(f"module/{module}/initstate", "live\n")

    def test_live_modules_without_interface_are_not_ready(self):
        (self.root / "class/net/wlan0").unlink()
        self.assert_not_ready()

    def test_wrong_radio_is_not_ready(self):
        for attribute, value in (("vendor", "0x5449"), ("device", "0xc08d")):
            with self.subTest(attribute=attribute):
                path = self.device / attribute
                original = path.read_text()
                path.write_text(value + "\n")
                self.assert_not_ready()
                path.write_text(original)

    def test_missing_radio_identity_is_not_ready(self):
        (self.device / "device").unlink()
        self.assert_not_ready()

    def test_unbound_device_is_not_ready(self):
        (self.device / "driver").unlink()
        self.assert_not_ready()

    def test_wrong_driver_is_not_ready(self):
        (self.device / "driver").unlink()
        wrong = self.root / "bus/sdio/drivers/other"
        wrong.mkdir()
        (self.device / "driver").symlink_to(wrong)
        self.assert_not_ready()

    def test_driver_from_wrong_module_is_not_ready(self):
        module = self.root / "bus/sdio/drivers/aicwf_sdio/module"
        module.unlink()
        module.symlink_to(self.root / "module/aic8800_bsp")
        self.assert_not_ready()

    def test_non_work_firmware_modes_are_not_ready(self):
        self.write("module/aic8800_bsp/parameters/testmode", "4\n")
        self.assert_not_ready()
        self.write("module/aic8800_bsp/parameters/testmode", "0\n")
        self.write("devices/platform/aic-bsp/cpmode", "Current: 4, firmware info:\n")
        self.assert_not_ready()

    def test_missing_mode_evidence_is_not_ready(self):
        (self.root / "devices/platform/aic-bsp/cpmode").unlink()
        self.assert_not_ready()

    def test_explicit_interface_name(self):
        (self.root / "class/net/wlan0").rename(self.root / "class/net/wlx-test")
        self.assertEqual(self.run_gate("wlx-test").returncode, 0)
        self.assert_not_ready()

    def test_invalid_arguments_are_usage_errors(self):
        for args in (("../wlan0",), ("",), ("..",), ("a" * 16,), ("wlan0", "extra")):
            with self.subTest(args=args):
                self.assertEqual(self.run_gate(*args).returncode, 2)

    def test_check_preserves_files(self):
        files = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(self.run_gate().returncode, 0)
        self.assertEqual({p: p.read_bytes() for p in files}, files)


if __name__ == "__main__":
    unittest.main()
