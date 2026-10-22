# SPDX-License-Identifier: MIT
"""Exercise gating and child cleanup without physical radios or system buses."""
import os
from pathlib import Path
import subprocess
import signal
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'aa_wireless_dongle/board/radxa/zero3w/checks/aic-bluetooth-test.sh'


class BluetoothStages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.shell = os.environ.get('RADXA_BT_STAGE_SHELL', 'sh')
        self.root = Path(self.tmp.name)
        self.bin = self.root / 'bin'; self.bin.mkdir()
        self.log = self.root / 'logs'; self.log.mkdir()
        self.trace = self.root / 'trace'; self.pids = self.root / 'pids'
        (self.root / 'sys/class/bluetooth').mkdir(parents=True)
        (self.root / 'sys/class/tty/ttyS1').mkdir(parents=True)
        (self.root / 'sys/bus/sdio/devices').mkdir(parents=True)
        (self.root / 'sys/firmware').mkdir()
        (self.root / 'sys/firmware/fdt').write_bytes(b'fixture-dt')
        (self.log / 'radio-result.txt').write_text('RADIO_RESET_RESULT=success\n')
        self.env = dict(os.environ, PATH=f'{self.bin}:/usr/bin:/bin', TRACE=str(self.trace),
                        PIDFILE=str(self.pids), RADXA_SYSFS_ROOT=str(self.root / 'sys'),
                        FAIL='', RADXA_MODULE_DIR=str(self.root / 'modules'),
                        RADXA_DBUS_SOCKET=str(self.root / 'bus'),
                        RADXA_BT_SNAPSHOT=str(STAGE.with_name('aic-bluetooth-snapshot.sh')))
        self.command('uname', 'echo 6.12.114')
        self.command('sleep', 'exec /bin/sleep 0.01')
        self.command('sync', ':')
        self.command('dmesg', 'echo snapshot >> "$TRACE"; echo fixture-kernel')
        self.command('aic-bounded-run', 'shift; exec "$@"')
        self.command('timeout', '''case "$*" in *aic-pairing-test*) shift 5;; *) shift 3;; esac
exec "$@"''')
        self.command('insmod', '''name=${1##*/}; echo "$name" >>"$TRACE"
[ "$FAIL" != "$name" ]''')
        for name in ('hciattach', 'dbus-daemon', 'bluetoothd'):
            body = f'echo {name} >>"$TRACE"; echo "$$" >>"$PIDFILE"\n'
            if name == 'hciattach':
                body += '[ "$FAIL" = missing_hci ] || mkdir -p "$RADXA_SYSFS_ROOT/class/bluetooth/hci0"\n'
            self.command(name, body + 'exec /bin/sleep 30')
        self.command('dbus-send', '''case "$*" in
 *--dest=org.bluez*) [ "$FAIL" != adapter ] && grep -q '^bluetoothd$' "$TRACE" || exit 1;;
 *) grep -q '^dbus-daemon$' "$TRACE" || exit 1;;
esac
echo dbus-send >>"$TRACE"''')
        self.command('aic-pairing-test', '''echo aic-pairing-test >>"$TRACE"
[ "$FAIL" != pairing ]''')

    def command(self, name, body):
        f = self.bin / name; f.write_text('#!/bin/sh\n' + body + '\n'); f.chmod(0o755)

    def run_stage(self, fail=''):
        self.env['FAIL'] = fail
        result = subprocess.run([self.shell, str(STAGE), str(self.log)], env=self.env,
                                capture_output=True, text=True, timeout=8)
        trace = self.trace.read_text().splitlines() if self.trace.exists() else []
        if self.pids.exists():
            for pid in self.pids.read_text().splitlines():
                with self.assertRaises(ProcessLookupError): os.kill(int(pid), 0)
        return result, trace

    def test_success_loads_dependencies_before_attachment_and_bluez(self):
        result, trace = self.run_stage()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(trace[:8], [n + '.ko' for n in
            ['ecc', 'ecdh_generic', 'cmac', 'bluetooth', 'pwrseq-core', 'btbcm', 'btqca', 'hci_uart']])
        self.assertLess(trace.index('hciattach'), trace.index('bluetoothd'))
        self.assertLess(trace.index('bluetoothd'), trace.index('aic-pairing-test'))
        self.assertIn('BT_PAIRING_RESULT=success', (self.log / 'bluetooth-result.txt').read_text())

    def test_radio_failure_blocks_bluetooth_modules(self):
        (self.log / 'radio-result.txt').write_text('RADIO_RESET_RESULT=failed\n')
        result, trace = self.run_stage()
        self.assertNotEqual(result.returncode, 0); self.assertEqual(trace, ['snapshot'])

    def test_each_module_failure_blocks_all_daemons(self):
        for name in ['ecc', 'ecdh_generic', 'cmac', 'bluetooth', 'pwrseq-core', 'btbcm', 'btqca', 'hci_uart']:
            with self.subTest(module=name):
                self.trace.unlink(missing_ok=True)
                result, trace = self.run_stage(name + '.ko')
                self.assertNotEqual(result.returncode, 0); self.assertNotIn('hciattach', trace)

    def test_missing_hci_prevents_dbus_and_bluez(self):
        result, trace = self.run_stage('missing_hci')
        self.assertNotEqual(result.returncode, 0); self.assertNotIn('dbus-daemon', trace)

    def test_attachment_failure_preserves_state_before_cleanup(self):
        result, trace = self.run_stage('missing_hci')
        self.assertEqual(result.returncode, 11)
        self.assertIn('snapshot', trace)
        self.assertIn('fixture-kernel', (self.log / 'failure-kernel.txt').read_text())
        self.assertIn('State:', (self.log / 'failure-process.txt').read_text())
        self.assertIn('SNAPSHOT_FINISHED=1', (self.log / 'failure-snapshot.txt').read_text())
        self.assertIn('CLEANUP_FINISHED=1', (self.log / 'cleanup-result.txt').read_text())

    def test_early_attachment_exit_is_recorded(self):
        self.command('hciattach', 'echo hciattach >> "$TRACE"; exit 7')
        result, trace = self.run_stage()
        self.assertEqual(result.returncode, 11, result.stderr)
        self.assertNotIn('dbus-daemon', trace)
        self.assertIn('EXIT=7', (self.log / 'cleanup-result.txt').read_text())

    def test_snapshot_artifact_failure_is_not_complete_success(self):
        for name in ('final-process.txt', 'hardware-after-cleanup.txt'):
            (self.log / name).mkdir()
        r = subprocess.run([self.shell, str(STAGE.with_name('aic-bluetooth-snapshot.sh')),
                            str(self.log), 'final', '-'], env=self.env, capture_output=True)
        self.assertEqual(r.returncode, 20)
        self.assertIn('SNAPSHOT_STATUS=20', (self.log / 'final-snapshot.txt').read_text())

    def test_unfinished_child_does_not_block_capture_return(self):
        self.env['FAIL'] = 'missing_hci'
        wrapper = '''kill() {
case "$1" in -0) /bin/kill "$@";; *) return 0;; esac
}
stage=$1; shift
. "$stage"'''
        try:
            result = subprocess.run([self.shell, '-c', wrapper, 'stage', str(STAGE), str(self.log)],
                                    env=self.env, capture_output=True, text=True, timeout=4)
            self.assertEqual(result.returncode, 16, result.stderr)
            self.assertIn('UNREAPED_PID=', (self.log / 'cleanup-result.txt').read_text())
            self.assertIn('BT_PAIRING_RESULT=failed', (self.log / 'bluetooth-result.txt').read_text())
            self.assertIn('STAGE=hci_attach', (self.log / 'failure-result.txt').read_text())
            self.assertIn('SNAPSHOT_FINISHED=1', (self.log / 'failure-snapshot.txt').read_text())
        finally:
            if self.pids.exists():
                for pid in self.pids.read_text().splitlines():
                    try: os.kill(int(pid), signal.SIGKILL)
                    except ProcessLookupError: pass

    def test_absent_bluez_adapter_prevents_pairing(self):
        result, trace = self.run_stage('adapter')
        self.assertNotEqual(result.returncode, 0); self.assertNotIn('aic-pairing-test', trace)

    def test_pairing_failure_is_not_success(self):
        result, _ = self.run_stage('pairing')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('BT_PAIRING_RESULT=failed', (self.log / 'bluetooth-result.txt').read_text())

    def test_log_failure_blocks_module_load(self):
        (self.log / 'bluetooth-progress.txt').mkdir()
        result, trace = self.run_stage()
        self.assertNotEqual(result.returncode, 0); self.assertEqual(trace, [])


if __name__ == '__main__': unittest.main()
