# SPDX-License-Identifier: MIT
"""Run build.sh with a fake docker to check board discovery, labels and selection."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ["bash", "generate_image_donotuse", "rpi5", "radxa-zero3w", "rpi0w", "rpi02w",
            "rpi3a", "rpi4"]
BOARDS = ["radxa-zero3w", "rpi0w", "rpi02w", "rpi3a", "rpi4", "rpi5"]


class BuildScript(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / "bin").mkdir()
        self.calls = root / "calls"
        self.services = root / "services"
        self.services.write_text("\n".join(SERVICES) + "\n")
        docker = root / "bin/docker"
        docker.write_text(f'''#!/bin/sh
case "$*" in
	"compose config --services") cat "{self.services}" ;;
	"compose run --rm --build "*) echo "$5" >>"{self.calls}" ;;
esac
''')
        docker.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{root / 'bin'}:/usr/bin:/bin")

    def run_script(self, *args):
        return subprocess.run([str(ROOT / "build.sh"), *args], env=self.env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=20)

    def built(self):
        return self.calls.read_text().split() if self.calls.exists() else []

    def test_help_lists_radxa_and_pi_boards_with_labels(self):
        result = self.run_script("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = [line.split()[0] for line in result.stdout.splitlines()
                  if line.startswith("  ") and line.split()[0] in SERVICES]
        self.assertEqual(listed, BOARDS)
        self.assertIn("radxa-zero3w  Radxa ZERO 3W", result.stdout)
        self.assertIn("rpi4          Raspberry Pi 4", result.stdout)

    def test_all_builds_every_board_but_no_helper_service(self):
        result = self.run_script("all")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.built(), BOARDS)

    def test_radxa_builds_on_its_own(self):
        result = self.run_script("radxa-zero3w")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.built(), ["radxa-zero3w"])

    def test_helper_services_are_not_boards(self):
        for name in ("bash", "generate_image_donotuse"):
            with self.subTest(name=name):
                result = self.run_script(name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"unknown board '{name}'", result.stderr)
        self.assertEqual(self.built(), [])

    def test_compose_without_board_services_is_an_error(self):
        self.services.write_text("bash\ngenerate_image_donotuse\nother\n")
        result = self.run_script("--help")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("defines no rpi* or radxa* board services", result.stderr)


if __name__ == "__main__":
    unittest.main()
