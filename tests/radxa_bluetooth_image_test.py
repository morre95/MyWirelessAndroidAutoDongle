# SPDX-License-Identifier: MIT
"""Inspect actual boot filesystem and all three composed initramfs archives."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import shutil

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ROOT / 'aa_wireless_dongle/board/radxa/zero3w/checks'


def extract(archive, name):
    return subprocess.run(['cpio', '-i', '--to-stdout', name], input=archive,
                          capture_output=True, check=True).stdout


def names(archive):
    return set(subprocess.run(['cpio', '-it'], input=archive, capture_output=True,
                              check=True).stdout.decode().splitlines())


class BluetoothImage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(os.environ.get('RADXA_BLUETOOTH_TEST_DIR', str(
            ROOT / 'buildroot/output/radxa-bluetooth-test-20261022-v4')))
        cls.manifest = json.loads((cls.directory / 'manifest.json').read_text())
        archive = gzip.decompress((cls.directory / 'boot/initramfs.cpio.gz').read_bytes())
        cls.components = []; offset = 0
        for part in cls.manifest['archive_components']:
            data = archive[offset:offset + part['bytes']]
            if hashlib.sha256(data).hexdigest() != part['sha256']:
                raise AssertionError('Packed component differs from manifest')
            cls.components.append(data); offset += part['bytes']
        if offset != len(archive) or len(cls.components) != 3:
            raise AssertionError('Unexpected archive composition')

    def test_complete_image_matches_checksum(self):
        with (self.directory / 'radxa-bluetooth-test.img').open('rb') as f:
            self.assertEqual(hashlib.file_digest(f, 'sha256').hexdigest(), self.manifest['image_sha256'])
        self.assertFalse(self.manifest['physical_test_performed'])
        self.assertFalse(self.manifest['firmware_distribution_approved'])

    def test_real_disk_partition_contains_composed_archive(self):
        partition = self.directory / 'boot.ext4'
        with (self.directory / 'radxa-bluetooth-test.img').open('rb') as f:
            f.seek(32768 * 512)
            self.assertEqual(hashlib.sha256(f.read(partition.stat().st_size)).digest(),
                             hashlib.sha256(partition.read_bytes()).digest())
        packed = subprocess.run(['debugfs', '-R', 'cat /initramfs.cpio.gz', str(partition)],
                                capture_output=True, check=True).stdout
        self.assertEqual(packed, (self.directory / 'boot/initramfs.cpio.gz').read_bytes())

    def test_checked_base_radio_payload_is_preserved(self):
        for name, expected in self.manifest['base_radio_ramfs_sha256'].items():
            self.assertEqual(hashlib.sha256(extract(self.components[1], name)).hexdigest(), expected, name)
        modules = {Path(n).name for n in names(self.components[1]) if n.endswith('.ko')}
        self.assertEqual(modules, {'rfkill.ko', 'cfg80211.ko', 'aic8800_bsp.ko', 'aic8800_fdrv.ko'})

    def test_extra_payload_matches_manifest_and_current_sources(self):
        for name, expected in self.manifest['extra_payload_sha256'].items():
            self.assertEqual(hashlib.sha256(extract(self.components[2], name)).hexdigest(), expected, name)
        for name, source in [('init', 'bluetooth-test-init.sh'),
                             ('aic-bluetooth-test.sh', 'aic-bluetooth-test.sh'),
                             ('aic-bluetooth-snapshot.sh', 'aic-bluetooth-snapshot.sh')]:
            self.assertEqual(extract(self.components[2], name), (CHECKS / source).read_bytes())
        self.assertEqual(self.manifest['generator_sha256'],
                         hashlib.sha256((CHECKS / 'make-bluetooth-test.py').read_bytes()).hexdigest())

    def test_userspace_has_arm64_daemons_and_bus_policy(self):
        base = self.components[0]; entries = names(base)
        for program in ['usr/libexec/bluetooth/bluetoothd', 'usr/bin/hciattach',
                        'usr/bin/dbus-daemon', 'usr/bin/dbus-send', 'usr/bin/dbus-uuidgen']:
            self.assertIn(program, entries)
            self.assertEqual(extract(base, program)[18:20], b'\xb7\x00')
        self.assertIn('usr/share/dbus-1/system.d/bluetooth.conf', entries)
        self.assertFalse(any(Path(n).name in ('sshd', 'dropbear', 'hostapd', 'wpa_supplicant') for n in entries))
        self.assertFalse(any(n.startswith('var/lib/bluetooth/') for n in entries))

    def test_bluetooth_dependency_closure_is_in_final_layer(self):
        modules = {Path(n).name for n in names(self.components[2]) if n.endswith('.ko')}
        self.assertEqual(modules, {n + '.ko' for n in
            ['ecc', 'ecdh_generic', 'cmac', 'bluetooth', 'pwrseq-core', 'btbcm', 'btqca', 'hci_uart']})
        inputs = json.loads(extract(self.components[2], 'bluetooth-inputs.json'))
        self.assertEqual(inputs['pairing_window_seconds'], 180)
        self.assertEqual(inputs['capability'], 'NoInputNoOutput')
        self.assertEqual(extract(self.components[2], 'bin/aic-pairing-test')[18:20], b'\xb7\x00')

    def test_bounded_failure_capture_is_in_actual_image(self):
        final = self.components[2]
        self.assertEqual(extract(final, 'bin/aic-bounded-run')[18:20], b'\xb7\x00')
        self.assertEqual(extract(final, 'aic-bluetooth-snapshot.sh'),
                         (CHECKS / 'aic-bluetooth-snapshot.sh').read_bytes())
        inputs = json.loads(extract(final, 'bluetooth-inputs.json'))
        self.assertEqual(inputs['diagnostic_version'], 4)
        init = extract(final, 'init')
        self.assertIn(b'if /bin/sh /aic-bluetooth-test.sh', init)
        self.assertIn(b'aic-bounded-run 10 /bin/sh /aic-bluetooth-snapshot.sh', init)
        self.assertIn(b'capture_finished=0', init)
        self.assertIn(b'aic-bounded-run 210 aic-pairing-test',
                      extract(final, 'aic-bluetooth-test.sh'))

    def test_packed_native_signal_probe_with_no_shell_kill(self):
        qemu = shutil.which('qemu-aarch64-static')
        self.assertIsNotNone(qemu)
        with tempfile.TemporaryDirectory() as tmp:
            busybox = Path(tmp) / 'busybox'
            control = Path(tmp) / 'control'
            busybox.write_bytes(extract(self.components[1], 'bin/busybox')); busybox.chmod(0o700)
            control.write_bytes(extract(self.components[2], 'bin/aic-bounded-run')); control.chmod(0o700)
            no_tools = dict(os.environ, PATH=tmp)
            r = subprocess.run([qemu, str(busybox), 'sh', '-c', 'kill -0 $$'],
                               env=no_tools, capture_output=True, timeout=3)
            self.assertEqual(r.returncode, 127)
            sysroot = ROOT / 'buildroot/output/radxa-bluetooth-userspace-container/target'
            r = subprocess.run([qemu, '-L', str(sysroot), str(control), '--signal', '0', str(os.getpid())],
                               env=no_tools, capture_output=True, timeout=3)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_init_refuses_host_execution(self):
        r = subprocess.run(['sh', str(CHECKS / 'bluetooth-test-init.sh')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn('PID 1', r.stderr)

    def test_changed_userspace_is_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'buildroot/output') as tmp:
            source = Path(tmp) / 'userspace'; (source / 'images').mkdir(parents=True)
            original = ROOT / 'buildroot/output/radxa-bluetooth-userspace-container'
            (source / '.config').write_bytes((original / '.config').read_bytes())
            (source / 'images/rootfs.cpio').write_bytes(b'changed')
            out = Path(tmp) / 'image'
            r = subprocess.run([sys.executable, str(CHECKS / 'make-bluetooth-test.py'),
                                '--userspace', str(source), '--output', str(out)], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('Input differs', r.stderr)
            self.assertFalse(out.exists())


if __name__ == '__main__': unittest.main()
