#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a private AIC radio diagnostic image; never write a physical card."""
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

CHECKS = Path(__file__).resolve().parent
STARTUP = CHECKS.parents[3] / "package/aic8800-startup/src"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("boot_test", CHECKS / "make-boot-test.py")
boot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boot)
PREP = boot.OUTPUT_ROOT / "radxa-radio-test-prep"
VERMAGIC = "6.12.114 SMP preempt mod_unload aarch64"
MODULES = {
    "rfkill": "4687d68e350816da3c287e6bf3966fffdb9c51eadabefe326c187ef39d53b6f9",
    "cfg80211": "640a322588093c9edd3eae85e0bcf2b85c92634dd56ddcddcc29fd0afac76dc3",
    "aic8800_bsp": "7d42e347b366a7f464f063bbfc19c63cf478a0860962fc842dcb597efa0846ed",
    "aic8800_fdrv": "64b6bd765fe293e2b332de7acee1031d6d8160671d3a985ee6dde88a5dbcd217",
}
FIRMWARE = {
    "fw_patch_table_8800d80_u02.bin": "ad83e162ac9f6aa033f3b18315d8830bcb13d8cc945bec2c8ec810a2b6eaed47",
    "fw_adid_8800d80_u02.bin": "a526cbd02fcdc495f049f3ad6b5933cb08cd984b16790c716a060d582fee1a56",
    "fw_patch_8800d80_u02.bin": "96514eb2790783deea3390811473519fd19640c26c532d4263eb8923d2fbb497",
    "fw_patch_8800d80_u02_ext0.bin": "f1f5048c094c74103b1a0e11cb6898fc18de9ee532cef90967d80745ee8573a1",
    "fmacfw_8800d80_u02.bin": "2ce84b41de107c43656f98899e86bc65c13afda15ca780c629aead20f3bc56ad",
    "aic_userconfig_8800d80.txt": "56c039d10af63c888b18890f508968a143f034de279fd2c4ec7ee65133e3dbdb",
}


def radio_inputs(prep):
    files = {}
    for name, expected in MODULES.items():
        path = prep / f"modules/{name}.ko"
        boot.require_hash(path, expected)
        if boot.run("modinfo", "-F", "vermagic", str(path),
                    capture_output=True, text=True).stdout.strip() != VERMAGIC:
            raise ValueError(f"Module/kernel ABI mismatch: {name}")
        files[f"modules/{name}.ko"] = path
    for name, expected in FIRMWARE.items():
        path = prep / f"firmware/{name}"
        boot.require_hash(path, expected)
        files[f"lib/firmware/aic8800_fw/SDIO/aic8800D80/{name}"] = path
    helper = prep / "aic-hci-reset"
    boot.require_hash(helper, "95d4d948230f00bc418eff219ca48c56da1e1bda8ffae9fee91c31f232023026")
    boot.require_hash(STARTUP / "aic-hci-reset.c",
                      "119ed8bfda09aa75b872fdcddf919a4f6e5c2cee0780e58b16c00c3bdc3180f0")
    boot.require_static_arm64(helper)
    files.update({"bin/aic-hci-reset": helper,
                  "bin/aic-firmware-ready.sh": STARTUP / "aic-firmware-ready.sh",
                  "aic-radio-test.sh": CHECKS / "aic-radio-test.sh",
                  "init": CHECKS / "radio-test-init.sh"})
    return files


def assemble(output, busybox, prep):
    output = boot.validate_output(output)
    files = radio_inputs(prep)
    boot.require_hash(boot.LINUX / ".config",
                      "9fed7f3914a9a2af6a44e9dae3e1ed9c879c531ba436f78da0a8f66ad1908535")
    busybox = busybox.resolve(strict=True)
    boot.require_static_arm64(busybox)
    applets = boot.run("qemu-aarch64-static", str(busybox), "--list",
                       capture_output=True, text=True).stdout.splitlines()
    if not {"timeout", "insmod", "grep", "readlink"}.issubset(applets):
        raise ValueError("BusyBox lacks radio-stage applets")
    for script in (CHECKS / "radio-test-init.sh", CHECKS / "aic-radio-test.sh",
                   STARTUP / "aic-firmware-ready.sh"):
        boot.run("qemu-aarch64-static", str(busybox), "ash", "-n", str(script))
    with tempfile.TemporaryDirectory(dir=boot.OUTPUT_ROOT) as temporary:
        template = boot.assemble(Path(temporary) / "base", busybox)
        output.mkdir(mode=0o700)
        shutil.copytree(template / "boot", output / "boot")
    files["bin/busybox"] = busybox
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest()
              for name, path in files.items()}
    inputs = {"module_vermagic": VERMAGIC, "modules_sha256": MODULES,
              "firmware_sha256": FIRMWARE,
              "aic_commit": "fc7cbdd1791416c2457fa27a59e508bf325c9c3f",
              "source_archive_sha256": "cae09dc427fc6c4a7a1887b44612c8a30b39596fe04aeaaec66b8de6581eaa06",
              "disabled_bsp_flags": ["CONFIG_MCU_MESSAGE", "CONFIG_PLATFORM_ROCKCHIP",
                                     "CONFIG_PLATFORM_ROCKCHIP2", "CONFIG_GPIO_WAKEUP"],
              "btlpm_loaded": False, "hciattach_started": False,
              "payload_sha256": hashes}
    ramfs = output / "ramfs"
    for name, path in files.items():
        target = ramfs / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    (ramfs / "radio-inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    hashes["radio-inputs.json"] = hashlib.sha256((ramfs / "radio-inputs.json").read_bytes()).hexdigest()
    directories = {"dev", "proc", "sys", "logs", "bin"}
    for name in hashes:
        directories.update(str(p) for p in Path(name).parents if str(p) != ".")
    entries = [f"dir /{name} 0755 0 0" for name in
               sorted(directories, key=lambda n: (n.count('/'), n))]
    entries += ["nod /dev/console 0600 0 0 c 5 1", "nod /dev/null 0666 0 0 c 1 3"]
    for name in hashes:
        mode = "0755" if name == "init" or name.endswith('.sh') or name.startswith('bin/') else "0644"
        entries.append(f"file /{name} ramfs/{name} {mode} 0 0")
    entries += [f"slink /bin/{name} busybox 0777 0 0" for name in applets]
    (output / "initramfs.list").write_text("\n".join(entries) + "\n")
    archive = boot.run(str(boot.LINUX / "usr/gen_init_cpio"), "-t", "0",
                       "initramfs.list", cwd=output, capture_output=True).stdout
    (output / "boot/initramfs.cpio.gz").write_bytes(gzip.compress(archive, mtime=0))
    image = boot.pack_disk(output)
    image = image.rename(output / "radxa-radio-test.img")
    manifest = {"purpose": "Private module/firmware/HCI-reset experiment",
                "physical_test_performed": False, "radio_firmware_included": True,
                "firmware_distribution_approved": False, "ramfs_sha256": hashes,
                "boot_inputs_sha256": {name: expected for name, (_, expected) in boot.INPUTS.items()},
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "base_generator_sha256": hashlib.sha256((CHECKS / "make-boot-test.py").read_bytes()).hexdigest(),
                "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "SHA256SUMS").write_text(f"{manifest['image_sha256']}  {image.name}\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--busybox", type=Path, default=PREP / "busybox-1.37.0/busybox")
    parser.add_argument("--prep", type=Path, default=PREP)
    args = parser.parse_args()
    try:
        print(assemble(args.output, args.busybox, args.prep))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Radio-test preparation refused/failed: {error}\n")
