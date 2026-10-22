#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose a private diagnostic image from checked userspace/radio archives."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
CHECKS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('radio', CHECKS / 'make-radio-test.py')
radio = importlib.util.module_from_spec(spec); spec.loader.exec_module(radio)
boot = radio.boot
PREP = boot.OUTPUT_ROOT / 'radxa-bluetooth-test-prep'
USERSPACE = boot.OUTPUT_ROOT / 'radxa-bluetooth-userspace-container'
MODULES = {
    'ecc': '85ec563d02657401627aeb56a976884fb9300d3f9270822f3d3fa5077ba0d431',
    'ecdh_generic': '3cc141bb726baa51959034bd9585b4a0b1eb13f159c8de223525cb3a6bb56055',
    'cmac': '59831a6718545666f725ccb5fdc27b28de05e66af6040d57d932bffd34810d97',
    'bluetooth': 'c1bd502e01580a004a9f80b8fcda663a6a65e250f221f4e39c857ef7e717c4dd',
    'pwrseq-core': '43d0cb7aac7504c81fe4f774671e48b4f1d2eca423d5dd4788bbcabcc3a66b56',
    'btbcm': '9f7f782ea3c6616c542e070307031a1c15587a9ce6e12652b08cb53a8b43952f',
    'btqca': '642641bbd0994b822b9b972c027f2cb49c6d58da889c32a8aea7947bcf0946c1',
    'hci_uart': 'b9ead25779b941ed1a32d1b020076190d63cc841d054145edb2d65e36cd16223',
}


def sha(data): return hashlib.sha256(data).hexdigest()


def checked_inputs(userspace, prep):
    boot.require_hash(userspace / '.config',
        'a50037fc4bb838291604cafb5fe7c56553f6b2f6029a77e78701fc8df4d8c6bc')
    boot.require_hash(userspace / 'images/rootfs.cpio',
        '58cd5d074175716fcc297284c986963e816245fb31288a32cc9b7f627a26e706')
    boot.require_hash(prep / 'aic-pairing-test',
        'a26e9214a010a0a6c1e291fb40e530a805adcb640395c3e9a54e25c75666ff1a')
    boot.require_hash(CHECKS / 'aic-pairing-test.c',
        'beea11866d637d51187407e10400e6e1ecff9f347dcd7fcf773e67d750bf8c71')
    files = {'init': CHECKS / 'bluetooth-test-init.sh',
             'aic-bluetooth-test.sh': CHECKS / 'aic-bluetooth-test.sh',
             'bin/aic-pairing-test': prep / 'aic-pairing-test'}
    loaded = {'rfkill', 'cfg80211', 'aic8800_bsp', 'aic8800_fdrv'}
    for name, expected in MODULES.items():
        path = prep / f'modules/{name}.ko'
        boot.require_hash(path, expected)
        if boot.run('modinfo', '-F', 'vermagic', str(path), capture_output=True,
                    text=True).stdout.strip() != radio.VERMAGIC:
            raise ValueError(f'Module ABI mismatch: {name}')
        deps = boot.run('modinfo', '-F', 'depends', str(path), capture_output=True,
                        text=True).stdout.strip().split(',')
        if any(d and d.replace('-', '_') not in loaded for d in deps):
            raise ValueError(f'Module dependency order invalid: {name}')
        loaded.add(name.replace('-', '_'))
        files[f'modules/{name}.ko'] = path
    return files


def assemble(output, userspace, prep):
    output = boot.validate_output(output)
    files = checked_inputs(userspace, prep)
    busybox = radio.PREP / 'busybox-1.37.0/busybox'
    for name in ('bluetooth-test-init.sh', 'aic-bluetooth-test.sh'):
        boot.run('qemu-aarch64-static', str(busybox), 'ash', '-n', str(CHECKS / name))
    # Linux accepts concatenated newc archives; later regular files replace earlier ones.
    # Keep the Buildroot base first, checked radio payload second, and new init last.
    with tempfile.TemporaryDirectory(dir=boot.OUTPUT_ROOT) as tmp:
        base = radio.assemble(Path(tmp) / 'radio', busybox, radio.PREP)
        base_manifest = json.loads((base / 'manifest.json').read_text())
        radio_archive = gzip.decompress((base / 'boot/initramfs.cpio.gz').read_bytes())
        output.mkdir(mode=0o700)
        shutil.copytree(base / 'boot', output / 'boot')
    ramfs = output / 'ramfs'; ramfs.mkdir()
    hashes = {name: sha(path.read_bytes()) for name, path in files.items()}
    inputs = {'bluez_version': '5.79', 'dbus_version': '1.14.10',
              'pairing_window_seconds': 180, 'capability': 'NoInputNoOutput',
              'module_order': list(MODULES), 'extra_payload_sha256': hashes,
              'base_radio_ramfs_sha256': base_manifest['ramfs_sha256'],
              'firmware_distribution_approved': False}
    for name, path in files.items():
        target = ramfs / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    metadata = ramfs / 'bluetooth-inputs.json'
    metadata.write_text(json.dumps(inputs, indent=2) + '\n')
    hashes['bluetooth-inputs.json'] = sha(metadata.read_bytes())
    entries = ['dir /bin 0755 0 0', 'dir /modules 0755 0 0']
    for name in hashes:
        mode = '0755' if name == 'init' or name.endswith('.sh') or name.startswith('bin/') else '0644'
        entries.append(f'file /{name} ramfs/{name} {mode} 0 0')
    (output / 'initramfs.list').write_text('\n'.join(entries) + '\n')
    extra = boot.run(str(boot.LINUX / 'usr/gen_init_cpio'), '-t', '0',
                     'initramfs.list', cwd=output, capture_output=True).stdout
    components = [userspace.joinpath('images/rootfs.cpio').read_bytes(), radio_archive, extra]
    (output / 'boot/initramfs.cpio.gz').write_bytes(gzip.compress(b''.join(components), mtime=0))
    image = boot.pack_disk(output).rename(output / 'radxa-bluetooth-test.img')
    manifest = {'purpose': 'Private mainline UART/BlueZ and owner-assisted pairing test',
                'physical_test_performed': False, 'firmware_distribution_approved': False,
                'archive_components': [{'bytes': len(c), 'sha256': sha(c)} for c in components],
                'extra_payload_sha256': hashes,
                'base_radio_ramfs_sha256': base_manifest['ramfs_sha256'],
                'boot_inputs_sha256': base_manifest['boot_inputs_sha256'],
                'generator_sha256': sha(Path(__file__).read_bytes()),
                'image_sha256': sha(image.read_bytes())}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'SHA256SUMS').write_text(f"{manifest['image_sha256']}  {image.name}\n")
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--userspace', type=Path, default=USERSPACE)
    parser.add_argument('--prep', type=Path, default=PREP)
    args = parser.parse_args()
    try: print(assemble(args.output, args.userspace, args.prep))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Bluetooth preparation refused/failed: {error}\n')
