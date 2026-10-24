# SPDX-License-Identifier: MIT
"""Exercise the Radxa radio init script with isolated sysfs and command fixtures."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "aa_wireless_dongle/package/aic8800-startup/src"
SCRIPT = SOURCE / "S38radio"
CONFIGS = ROOT / "aa_wireless_dongle/configs"
OUTPUT = Path(os.environ.get("RADXA_OUTPUT", str(ROOT / "buildroot/output/radxa-zero3w")))
TARGET = OUTPUT / "target"
EM_AARCH64 = 183
# Set to e.g. "qemu-aarch64-static -L TARGET TARGET/bin/busybox ash" for the board's shell.
SHELL = os.environ.get("RADXA_SHELL", "sh").split()
FIXTURES = ("modprobe", "aic-firmware-ready.sh", "aic-hci-reset", "start-stop-daemon")


class RadioStartup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.sys = self.root / "sys"
        self.trace = self.root / "trace"
        self.env = dict(os.environ, PATH=f"{self.bin}:/usr/bin:/bin",
                        RADXA_SYSFS_ROOT=str(self.sys), TRACE=str(self.trace), FAIL="")
        self.sdio_function("0x0082")
        self.command("sleep", 'echo sleep >>"$TRACE"')
        for name in FIXTURES:
            self.command(name, f'echo "{name} $*" >>"$TRACE"; [ "$FAIL" != "{name}" ]')
        # btattach registers hci0 once it attaches the UART.
        self.command("start-stop-daemon", f'''echo "start-stop-daemon $*" >>"$TRACE"
[ "$FAIL" != start-stop-daemon ] || exit 1
case " $* " in *" -S "*) [ -n "$NO_HCI" ] || mkdir -p "{self.sys}/class/bluetooth/hci0" ;; esac''')

    def sdio_function(self, device):
        path = self.sys / "bus/sdio/devices/mmc2:390b:1"
        path.mkdir(parents=True)
        (path / "vendor").write_text("0xc8a1\n")
        (path / "device").write_text(device + "\n")

    def command(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def start(self, fail="", **env):
        result = subprocess.run([*SHELL, str(SCRIPT), "start"], env=dict(self.env, FAIL=fail, **env),
                                capture_output=True, text=True, timeout=10)
        trace = self.trace.read_text().splitlines() if self.trace.exists() else []
        return result, [line for line in trace if line != "sleep"]

    def test_runs_the_adr_startup_contract_in_order(self):
        result, trace = self.start()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(trace, [
            "modprobe aic8800_fdrv custregd=0",
            "aic-firmware-ready.sh wlan0",
            "modprobe hci_uart",
            "aic-hci-reset /dev/ttyS1",
            "start-stop-daemon -S -b -q -m -p /var/run/btattach.pid -x /usr/bin/btattach"
            " -- -B /dev/ttyS1 -P h4 -S 1500000",
        ])

    def test_waits_for_the_sdio_radio_before_loading(self):
        self.command("sleep", f'''echo sleep >>"$TRACE"
mkdir -p "{self.sys}/bus/sdio/devices/mmc2:390b:1"
echo 0xc8a1 >"{self.sys}/bus/sdio/devices/mmc2:390b:1/vendor"
echo 0x0082 >"{self.sys}/bus/sdio/devices/mmc2:390b:1/device"''')
        for child in (self.sys / "bus/sdio/devices/mmc2:390b:1").iterdir():
            child.unlink()
        result, trace = self.start()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(trace[0], "modprobe aic8800_fdrv custregd=0")

    def test_missing_sdio_radio_loads_nothing(self):
        (self.sys / "bus/sdio/devices/mmc2:390b:1/device").write_text("0x0182\n")
        result, trace = self.start()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace, [])
        self.assertIn("AIC8800D80 Wi-Fi SDIO device c8a1:0082 not found", result.stderr)

    def test_driver_load_failure_stops_wifi_and_bluetooth(self):
        result, trace = self.start("modprobe")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace, ["modprobe aic8800_fdrv custregd=0"])
        self.assertIn("cannot load aic8800_fdrv", result.stderr)
        self.assertIn("/lib/firmware/aic8800_fw/SDIO/aic8800D80", result.stderr)

    def test_readiness_is_polled_with_a_bound(self):
        result, trace = self.start("aic-firmware-ready.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace.count("aic-firmware-ready.sh wlan0"), 11)
        self.assertNotIn("aic-hci-reset /dev/ttyS1", trace)
        self.assertIn("Wi-Fi firmware not ready on wlan0", result.stderr)

    def test_reset_failure_never_attaches(self):
        result, trace = self.start("aic-hci-reset")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace[-1], "aic-hci-reset /dev/ttyS1")
        self.assertIn("Bluetooth HCI reset failed on /dev/ttyS1", result.stderr)

    def test_bluetooth_failure_leaves_wifi_loaded(self):
        result, trace = self.start("aic-hci-reset")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("aic-firmware-ready.sh wlan0", trace)
        self.assertNotIn("rmmod", " ".join(trace))

    def test_attach_timeout_stops_btattach(self):
        result, trace = self.start(NO_HCI="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace[-1], "start-stop-daemon -K -q -p /var/run/btattach.pid")
        self.assertIn("hci0 did not appear within 10 s", result.stderr)

    def test_stop_ends_btattach(self):
        result = subprocess.run([*SHELL, str(SCRIPT), "stop"], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.trace.read_text().splitlines(),
                         ["start-stop-daemon -K -q -p /var/run/btattach.pid"])


class InstalledStartup(unittest.TestCase):
    """Inspect the radxa-zero3w_defconfig build output."""

    def test_only_radxa_selects_the_startup_package(self):
        self.assertIn("BR2_PACKAGE_AIC8800_STARTUP=y",
                      (CONFIGS / "radxa-zero3w_defconfig").read_text().splitlines())
        for defconfig in CONFIGS.glob("raspberrypi*_defconfig"):
            self.assertNotIn("AIC8800", defconfig.read_text(), defconfig.name)

    def test_scripts_are_installed_unchanged(self):
        for installed, source in (("etc/init.d/S38radio", "S38radio"),
                                  ("usr/sbin/aic-firmware-ready.sh", "aic-firmware-ready.sh")):
            path = TARGET / installed
            self.assertEqual(path.read_bytes(), (SOURCE / source).read_bytes(), installed)
            self.assertTrue(os.access(path, os.X_OK), installed)

    def test_reset_helper_is_an_arm64_executable(self):
        header = (TARGET / "usr/sbin/aic-hci-reset").read_bytes()[:20]
        self.assertEqual(header[:4], b"\x7fELF")
        self.assertEqual(int.from_bytes(header[18:20], "little"), EM_AARCH64)

    def test_btattach_is_installed(self):
        self.assertTrue(os.access(TARGET / "usr/bin/btattach", os.X_OK))

    def test_radio_starts_before_hostapd_bluez_and_network(self):
        scripts = sorted(p.name for p in (TARGET / "etc/init.d").glob("S??*"))
        for later in ("S39hostapd_conf", "S40bluetoothd", "S40network"):
            self.assertLess(scripts.index("S38radio"), scripts.index(later), later)

    def test_access_point_uses_5ghz_channel_36(self):
        lines = (TARGET / "etc/hostapd.conf.in").read_text().splitlines()
        for line in ("hw_mode=a", "ieee80211ac=1", "channel=36"):
            self.assertIn(line, lines)


if __name__ == "__main__":
    unittest.main()
