# SPDX-License-Identifier: MIT
"""Inspect the aic8800 driver package in the radxa-zero3w_defconfig build against ADR-0001."""
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "aa_wireless_dongle/configs"
OUTPUT = Path(os.environ.get("RADXA_OUTPUT", str(ROOT / "buildroot/output/radxa-zero3w")))
KERNEL = OUTPUT / "build/linux-6.12.114"
AIC_COMMIT = "fc7cbdd1791416c2457fa27a59e508bf325c9c3f"
DRIVER = OUTPUT / f"build/aic8800-{AIC_COMMIT}/src/SDIO/driver_fw/driver/aic8800"
MODULES = OUTPUT / "target/lib/modules/6.12.114"
VERMAGIC = "6.12.114 SMP preempt mod_unload aarch64"
MODINFO = OUTPUT / "host/bin/modinfo"


def module_path(name):
    matches = sorted(MODULES.glob(f"updates/**/{name}.ko*"))
    return matches[0] if len(matches) == 1 else None


def modinfo(name, field):
    result = subprocess.run([str(MODINFO), "-F", field, str(module_path(name))],
                            check=True, capture_output=True, text=True)
    return result.stdout.split("\n")[:-1]


class DefconfigTests(unittest.TestCase):
    def test_radxa_selects_the_driver(self):
        self.assertIn("BR2_PACKAGE_AIC8800=y",
                      (CONFIGS / "radxa-zero3w_defconfig").read_text().splitlines())

    def test_raspberry_pi_targets_do_not_select_the_driver(self):
        for defconfig in CONFIGS.glob("rpi*_defconfig"):
            self.assertNotIn("AIC8800", defconfig.read_text(), defconfig.name)


class PatchedSourceTests(unittest.TestCase):
    def test_debian_series_ran_before_the_board_patches(self):
        # Board patch 0001 rewrites the three monitor-callback guards that Debian's
        # fix-linux-6.13-build.patch adds.
        source = (DRIVER / "aic8800_fdrv/rwnx_main.c").read_text(errors="replace")
        self.assertEqual(source.count("KERNEL_VERSION (6, 12, 114)"), 3)

    def test_audited_build_options_are_unchanged(self):
        top = (DRIVER / "Makefile").read_text()
        for line in ("export CONFIG_PLATFORM_UBUNTU = y", "export CONFIG_PLATFORM_ROCKCHIP = n",
                     "export CONFIG_PLATFORM_ROCKCHIP2 = n", "export CONFIG_GPIO_WAKEUP = n"):
            self.assertIn(line, top.splitlines())
        bsp = (DRIVER / "aic8800_bsp/Makefile").read_text().splitlines()
        self.assertIn("CONFIG_MCU_MESSAGE = n", bsp)
        self.assertIn('CONFIG_AIC_FW_PATH = "/lib/firmware/aic8800_fw/SDIO/aic8800D80"', bsp)

    def test_bluetooth_low_power_mode_stays_off(self):
        header = (DRIVER / "aic8800_bsp/aic_bsp_driver.h").read_text(errors="replace")
        self.assertRegex(header, re.compile(r"^#define AICBT_LPM_ENABLE_DEFAULT\s+0$", re.M))


class ModuleTests(unittest.TestCase):
    def test_only_bsp_and_fdrv_are_installed(self):
        installed = sorted(p.name.split(".ko")[0] for p in MODULES.glob("updates/**/aic8800*.ko*"))
        self.assertEqual(installed, ["aic8800_bsp", "aic8800_fdrv"])

    def test_fdrv_depends_on_bsp_and_cfg80211(self):
        self.assertEqual(sorted(modinfo("aic8800_fdrv", "depends")[0].split(",")),
                         ["aic8800_bsp", "cfg80211"])

    def test_modules_match_the_kernel(self):
        for name in ("aic8800_bsp", "aic8800_fdrv"):
            self.assertEqual(modinfo(name, "vermagic"), [VERMAGIC], name)

    def test_fdrv_claims_the_d80_wifi_function(self):
        self.assertIn("sdio:c*vC8A1d0082*", modinfo("aic8800_fdrv", "alias"))

    def test_bsp_claims_sdio_wlan_class_functions(self):
        # The BSP matches by class; on the board it binds the D80's c8a1:0182 function.
        self.assertEqual(modinfo("aic8800_bsp", "alias"), ["sdio:c07v*d*"])

    def test_modules_are_indexed_for_modprobe(self):
        dep = (MODULES / "modules.dep").read_text()
        self.assertRegex(dep, r"updates/\S*aic8800_fdrv\.ko\S*: .*aic8800_bsp\.ko")


class KernelPrerequisiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = set((KERNEL / ".config").read_text().splitlines())

    def test_wifi_ap_prerequisites_are_built(self):
        for line in ("CONFIG_CFG80211=m", "CONFIG_MMC=y"):
            self.assertIn(line, self.config)

    def test_bluetooth_uart_transport_is_built(self):
        for line in ("CONFIG_BT=m", "CONFIG_BT_HCIUART=m", "CONFIG_BT_HCIUART_H4=y"):
            self.assertIn(line, self.config)


if __name__ == "__main__":
    unittest.main()
