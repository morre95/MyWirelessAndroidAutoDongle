# SPDX-License-Identifier: MIT
"""Verify fail-closed radio startup using isolated sysfs and command fixtures."""
import os
import gzip
import hashlib
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ROOT / "aa_wireless_dongle/board/radxa/zero3w/checks"


class RadioStages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "logs"
        self.log.mkdir()
        self.trace = self.root / "trace"
        self.timeouts = self.root / "timeouts"
        self.env = dict(os.environ, PATH=f"{self.bin}:/usr/bin:/bin",
                        RADXA_SYSFS_ROOT=str(self.root / "sys"),
                        RADXA_MODULE_DIR=str(self.root / "modules"),
                        TRACE=str(self.trace), TIMEOUT_TRACE=str(self.timeouts), FAIL="")
        for function, device in ((1, "0x0082"), (2, "0x0182")):
            path = self.root / f"sys/bus/sdio/devices/mmc2:390b:{function}"
            path.mkdir(parents=True)
            (path / "vendor").write_text("0xc8a1\n")
            (path / "device").write_text(device + "\n")
        self.command("uname", "echo 6.12.114")
        self.command("sleep", ":")
        self.command("sync", ":")
        self.command("timeout", 'echo "$*" >>"$TIMEOUT_TRACE"; shift 3; exec "$@"')
        self.command("insmod", 'name=${1##*/}; echo "$name" >>"$TRACE"; [ "$FAIL" != "$name" ]')
        for name in ("aic-firmware-ready.sh", "aic-hci-reset"):
            self.command(name, f'echo {name} >>"$TRACE"; [ "$FAIL" != "{name}" ]')

    def command(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)

    def run_stage(self, fail=""):
        self.env["FAIL"] = fail
        result = subprocess.run(["sh", str(CHECKS / "aic-radio-test.sh"), str(self.log)],
                                env=self.env, capture_output=True, text=True, timeout=10)
        trace = self.trace.read_text().splitlines() if self.trace.exists() else []
        return result, trace

    def test_success_requires_ordered_loads_readiness_and_reset(self):
        result, trace = self.run_stage()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(trace, ["rfkill.ko", "cfg80211.ko", "aic8800_bsp.ko",
                                 "aic8800_fdrv.ko", "aic-firmware-ready.sh", "aic-hci-reset"])
        self.assertIn("RADIO_RESET_RESULT=success", (self.log / "radio-result.txt").read_text())
        commands = self.timeouts.read_text().splitlines()
        self.assertEqual(len(commands), 5)
        self.assertTrue(all(c.startswith('-s KILL 30 insmod ') for c in commands[:4]))
        self.assertEqual(commands[-1], '-s KILL 5 aic-hci-reset /dev/ttyS1')

    def test_missing_sdio_prevents_all_module_loads(self):
        (self.root / "sys/bus/sdio/devices/mmc2:390b:2/device").unlink()
        result, trace = self.run_stage()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace, [])
        self.assertIn("STAGE=sdio_wait", (self.log / "radio-result.txt").read_text())

    def test_load_failure_blocks_every_later_stage(self):
        for name in ("rfkill.ko", "cfg80211.ko", "aic8800_bsp.ko", "aic8800_fdrv.ko"):
            with self.subTest(name=name):
                self.trace.unlink(missing_ok=True)
                result, trace = self.run_stage(name)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(trace[-1], name)
                self.assertNotIn("aic-hci-reset", trace)

    def test_readiness_failure_prevents_uart_reset(self):
        result, trace = self.run_stage("aic-firmware-ready.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("aic-hci-reset", trace)

    def test_readiness_is_rechecked_before_reset(self):
        counter = self.root / "readiness-count"
        self.command("aic-firmware-ready.sh", f'''count=0
[ ! -f "{counter}" ] || count=$(cat "{counter}")
count=$((count + 1)); echo "$count" >"{counter}"
echo aic-firmware-ready.sh >>"$TRACE"
[ "$count" -ge 3 ]''')
        result, trace = self.run_stage()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(trace.count('aic-firmware-ready.sh'), 3)
        self.assertEqual(trace[-1], 'aic-hci-reset')

    def test_reset_failure_is_not_reported_as_success(self):
        result, trace = self.run_stage("aic-hci-reset")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace[-1], "aic-hci-reset")
        self.assertIn("RADIO_RESET_RESULT=failed", (self.log / "radio-result.txt").read_text())

    def test_wrong_kernel_prevents_module_loads(self):
        self.command("uname", "echo 6.1.84-reference")
        result, trace = self.run_stage()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace, [])
        self.assertIn("STAGE=kernel", (self.log / "radio-result.txt").read_text())

    def test_log_write_failure_prevents_all_module_loads(self):
        for name in ('radio-result.txt', 'progress.txt'):
            with self.subTest(name=name):
                target = self.log / name
                target.unlink(missing_ok=True)
                target.mkdir()
                result, trace = self.run_stage()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(trace, [])
                target.rmdir()

    def test_log_sync_failure_prevents_all_module_loads(self):
        self.command('sync', 'exit 1')
        result, trace = self.run_stage()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trace, [])


class RadioImage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(os.environ.get("RADXA_RADIO_TEST_DIR", str(
            ROOT / "buildroot/output/radxa-radio-test-20261022-v2")))

    def test_real_image_and_embedded_inputs_match_manifest(self):
        manifest = json.loads((self.directory / "manifest.json").read_text())
        image = self.directory / "radxa-radio-test.img"
        with image.open("rb") as stream:
            self.assertEqual(hashlib.file_digest(stream, "sha256").hexdigest(),
                             manifest["image_sha256"])
        self.assertTrue(manifest["radio_firmware_included"])
        self.assertFalse(manifest["physical_test_performed"])
        self.assertFalse(manifest["firmware_distribution_approved"])
        archive = gzip.decompress((self.directory / "boot/initramfs.cpio.gz").read_bytes())
        for name, expected in manifest["ramfs_sha256"].items():
            result = subprocess.run(["cpio", "-i", "--to-stdout", name], input=archive,
                                    capture_output=True, check=True)
            self.assertEqual(hashlib.sha256(result.stdout).hexdigest(), expected, name)

    def test_disk_boot_partition_contains_the_radio_archive(self):
        partition = self.directory / 'boot.ext4'
        with (self.directory / 'radxa-radio-test.img').open('rb') as stream:
            stream.seek(32768 * 512)
            packed = hashlib.sha256(stream.read(partition.stat().st_size)).hexdigest()
        self.assertEqual(packed, hashlib.sha256(partition.read_bytes()).hexdigest())
        archive = subprocess.run(['debugfs', '-R', 'cat /initramfs.cpio.gz', str(partition)],
                                 capture_output=True, check=True).stdout
        self.assertEqual(archive, (self.directory / 'boot/initramfs.cpio.gz').read_bytes())

    def test_packaged_scripts_match_current_sources(self):
        manifest = json.loads((self.directory / 'manifest.json').read_text())
        for name, source in [('init', 'radio-test-init.sh'),
                             ('aic-radio-test.sh', 'aic-radio-test.sh'),
                             ('bin/aic-firmware-ready.sh', 'aic-firmware-ready.sh')]:
            self.assertEqual(manifest['ramfs_sha256'][name],
                             hashlib.sha256((CHECKS / source).read_bytes()).hexdigest())

    def test_payload_is_limited_to_selected_modules_and_six_firmware_files(self):
        archive = gzip.decompress((self.directory / "boot/initramfs.cpio.gz").read_bytes())
        names = subprocess.run(["cpio", "-it"], input=archive,
                               capture_output=True, check=True).stdout.decode().splitlines()
        self.assertEqual({Path(n).name for n in names if n.endswith('.ko')},
                         {"rfkill.ko", "cfg80211.ko", "aic8800_bsp.ko", "aic8800_fdrv.ko"})
        self.assertEqual(len([n for n in names if '/aic8800D80/' in n]), 6)
        self.assertFalse(any('hciattach' in n or 'btlpm' in n or 'bluetoothd' in n for n in names))

    def test_init_refuses_execution_on_host(self):
        result = subprocess.run(["sh", str(CHECKS / "radio-test-init.sh")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("PID 1", result.stderr)

    def test_changed_firmware_is_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'buildroot/output') as tmp:
            prep = Path(tmp) / 'prep'
            prep.mkdir()
            original = ROOT / 'buildroot/output/radxa-radio-test-prep'
            for name in ('modules', 'firmware'):
                shutil.copytree(original / name, prep / name)
            shutil.copyfile(original / 'aic-hci-reset', prep / 'aic-hci-reset')
            (prep / 'firmware/aic_userconfig_8800d80.txt').write_bytes(b'changed')
            output = Path(tmp) / 'image'
            result = subprocess.run([sys.executable, str(CHECKS / 'make-radio-test.py'),
                                     '--prep', str(prep), '--output', str(output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Input differs', result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
