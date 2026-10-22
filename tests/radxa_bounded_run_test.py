# SPDX-License-Identifier: MIT
"""Run the real deadline supervisor without touching a radio."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'aa_wireless_dongle/board/radxa/zero3w/checks/aic-bounded-run.c'


class BoundedRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('RADXA_BOUNDED_RUN_BIN'):
            cls.tmp = None
            cls.binary = Path(os.environ['RADXA_BOUNDED_RUN_BIN'])
            return
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tmp.name) / 'bounded-run'
        subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-Wconversion', '-Wshadow', str(SOURCE), '-o', str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        if cls.tmp: cls.tmp.cleanup()

    def run_command(self, *args):
        return subprocess.run([str(self.binary), *args], capture_output=True,
                              text=True, timeout=4)

    def test_preserves_command_result(self):
        for status in (0, 7):
            r = self.run_command('1', 'sh', '-c', f'echo captured; exit {status}')
            self.assertEqual(r.returncode, status)
            self.assertEqual(r.stdout, 'captured\n')

    def test_timeout_kills_worker_and_descendant(self):
        with tempfile.TemporaryDirectory() as tmp:
            pidfile = Path(tmp) / 'pids'
            started = time.monotonic()
            r = self.run_command('1', 'sh', '-c',
                'echo $$ > "$1"; sleep 30 & echo $! >> "$1"; wait', 'worker', str(pidfile))
            self.assertEqual(r.returncode, 124, r.stderr)
            self.assertLess(time.monotonic() - started, 3)
            for pid in pidfile.read_text().splitlines():
                state = Path('/proc', pid, 'stat')
                self.assertTrue(not state.exists() or ') Z ' in state.read_text())

    def test_stopped_worker_cannot_block_supervisor(self):
        r = self.run_command('1', 'sh', '-c', 'kill -STOP $$')
        self.assertEqual(r.returncode, 124, r.stderr)

    def test_nested_supervisors_are_rejected_before_worker_exec(self):
        r = self.run_command('1', str(self.binary), '10', 'sh', '-c', 'echo leaked-worker')
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, '')

    def test_signal_is_failure(self):
        r = self.run_command('1', 'sh', '-c', 'kill -TERM $$')
        self.assertEqual(r.returncode, 128 + signal.SIGTERM)

    def test_invalid_deadlines_are_rejected_before_exec(self):
        for deadline in ('0', '-1', '601', '1junk', ''):
            with self.subTest(deadline=deadline):
                r = self.run_command(deadline, 'sh', '-c', 'echo should-not-run')
                self.assertEqual(r.returncode, 2)
                self.assertEqual(r.stdout, '')


if __name__ == '__main__': unittest.main()
