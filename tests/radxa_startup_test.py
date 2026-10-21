# SPDX-License-Identifier: MIT
"""Check rollback behavior without touching the host's services or /etc."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


GENERATOR = Path(__file__).resolve().parents[1] / (
    "aa_wireless_dongle/board/radxa/zero3w/checks/make-startup-test.sh"
)


class StartupTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.bundle = self.root / "bundle"
        subprocess.run(["sh", str(GENERATOR), str(self.bundle)], check=True)
        self.log = self.root / "actions"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for command in ("rm", "systemctl", "timeout", "touch"):
            stub = self.bin / command
            stub.write_text(
                "#!/bin/sh\n"
                f"printf '%s\\n' \"{command} $*\" >> \"$ACTION_LOG\"\n"
                # systemd returns failure for reset-failed on an unloaded unit.
                'if [ "$1" = reset-failed ]; then exit 1; fi\n'
                'if [ "$1" = start ] && [ "$2" = "${FAIL_START-}" ]; then exit 1; fi\n'
                "exit 0\n"
            )
            stub.chmod(0o700)

    def run_rollback(self, script=None, **extra):
        return subprocess.run(
            ["sh", str(script or self.bundle / "rollback.sh")],
            env={**os.environ, "PATH": str(self.bin), "ACTION_LOG": str(self.log), **extra},
            executable="/bin/sh", capture_output=True, text=True, timeout=2,
        )

    def test_recovery_loads_never_started_bluez(self):
        result = self.run_rollback()
        self.assertEqual(result.returncode, 0, result.stderr)
        actions = self.log.read_text().splitlines()
        attach = actions.index("systemctl start rsetup-hciattach@ttyS1.service")
        bluez = actions.index("systemctl start bluetooth.service")
        marker = actions.index("touch /var/lib/radxa-aic-startup-test/rolled-back")
        self.assertLess(attach, bluez)
        self.assertLess(bluez, marker)
        self.assertIn("Reference hciattach and BlueZ restored", result.stdout)

    def test_start_failure_does_not_claim_restoration(self):
        for unit in ("rsetup-hciattach@ttyS1.service", "bluetooth.service"):
            with self.subTest(unit=unit):
                self.log.unlink(missing_ok=True)
                result = self.run_rollback(FAIL_START=unit)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("touch ", self.log.read_text())
                self.assertNotIn("Reference hciattach and BlueZ restored", result.stdout)

    def test_previous_reset_failed_sequence_reproduces_boot_failure(self):
        script = self.root / "old-rollback.sh"
        text = (self.bundle / "rollback.sh").read_text()
        text = text.replace(
            "systemctl start rsetup-hciattach@ttyS1.service",
            "systemctl reset-failed bluetooth.service\n"
            "systemctl start rsetup-hciattach@ttyS1.service",
        )
        script.write_text(text)
        result = self.run_rollback(script)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("touch ", self.log.read_text())

    def test_generator_refuses_to_overwrite_existing_bundle(self):
        before = {p.name: p.read_bytes() for p in self.bundle.iterdir()}
        result = subprocess.run(
            ["sh", str(GENERATOR), str(self.bundle)], capture_output=True, timeout=2,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual({p.name: p.read_bytes() for p in self.bundle.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
