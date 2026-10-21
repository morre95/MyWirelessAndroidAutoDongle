# SPDX-License-Identifier: MIT
"""Check the compiled, pinned AIC candidate and retained generic ZERO 3W DT."""
import hashlib
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "buildroot/output/radxa-bootchain-check/host/lib" /
                    f"python{sys.version_info.major}.{sys.version_info.minor}/site-packages"))
import libfdt


DTB_DIR = Path(os.environ.get("RADXA_DTB_DIR", str(
    ROOT / "buildroot/output/radxa-platform-check/linux/arch/arm64/boot/dts/rockchip"
)))
GENERIC_SHA256 = "eefcec9be8350d21e2f578bf9734279e4583779a87177411f4253feecc4b7d86"


class AicDtbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fdt = libfdt.Fdt((DTB_DIR / "rk3566-radxa-zero-3w-aic8800d80.dtb").read_bytes())

    def node(self, path):
        return self.fdt.path_offset(path)

    def alias(self, name):
        return self.node(self.fdt.getprop(self.node("/aliases"), name).as_str())

    def cells(self, node, name):
        return self.fdt.getprop(node, name).as_uint32_list()

    def children(self, node):
        child = self.fdt.first_subnode(node, libfdt.QUIET_NOTFOUND)
        while child >= 0:
            yield child
            child = self.fdt.next_subnode(child, libfdt.QUIET_NOTFOUND)

    def test_bluetooth_defaults_match_measured_directions(self):
        gpio = self.alias("gpio0")
        for name, pin, direction in (
            ("aic-bt-pc1-hog", 17, "output-low"),
            ("aic-bt-pb3-hog", 11, "input"),
            ("aic-bt-pb4-hog", 12, "input"),
        ):
            with self.subTest(name=name):
                hog = self.fdt.subnode_offset(gpio, name)
                self.assertTrue(self.fdt.hasprop(hog, "gpio-hog"))
                self.assertEqual(self.cells(hog, "gpios"), [pin, 0])
                selected = [p for p in ("input", "output-low", "output-high")
                            if self.fdt.hasprop(hog, p)]
                self.assertEqual(selected, [direction])

    def test_gpio_mux_and_pulls_select_only_the_reference_pins(self):
        gpio = self.alias("gpio0")
        self.assertEqual(self.fdt.getprop(gpio, "pinctrl-names").as_str(), "default")
        pins = []
        for phandle in self.cells(gpio, "pinctrl-0"):
            group = self.fdt.node_offset_by_phandle(phandle)
            bank, pin, mux, config = self.cells(group, "rockchip,pins")
            pins.append((bank, pin, mux))
            config = self.fdt.node_offset_by_phandle(config)
            bias = "bias-pull-down" if pin == 17 else "bias-pull-up"
            self.assertTrue(self.fdt.hasprop(config, bias))
            self.assertFalse(self.fdt.hasprop(config, "bias-disable"))
            self.assertEqual(self.cells(config, "drive-strength"), [0])
            self.assertTrue(self.fdt.hasprop(config, "input-schmitt-enable"))
        self.assertEqual(set(pins), {(0, 17, 0), (0, 11, 0), (0, 12, 0)})

    def test_wifi_power_sequence_keeps_its_gpio(self):
        power = self.node("/sdio-pwrseq")
        gpio = self.alias("gpio0")
        self.assertEqual(self.cells(power, "reset-gpios"),
                         [self.fdt.getprop(gpio, "phandle").as_uint32(), 16, 1])
        self.assertEqual(self.cells(power, "post-power-on-delay-ms"), [100])
        self.assertEqual(self.cells(power, "power-off-delay-us"), [5000000])
        self.assertFalse(self.fdt.hasprop(power, "clocks"))
        self.assertFalse(self.fdt.hasprop(power, "clock-names"))
        hogged = [self.cells(n, "gpios")[0] for n in self.children(gpio)
                  if self.fdt.hasprop(n, "gpio-hog")]
        self.assertEqual(sorted(hogged), [11, 12, 17])
        self.assertEqual(self.cells(self.alias("mmc2"), "mmc-pwrseq"),
                         self.cells(power, "phandle"))

    def test_uart_keeps_all_four_hardware_flow_control_pins(self):
        uart = self.alias("serial1")
        self.assertEqual(self.fdt.getprop(uart, "status").as_str(), "okay")
        self.assertTrue(self.fdt.hasprop(uart, "uart-has-rtscts"))
        pins = []
        for phandle in self.cells(uart, "pinctrl-0"):
            group = self.fdt.node_offset_by_phandle(phandle)
            cells = self.cells(group, "rockchip,pins")
            pins.extend(tuple(cells[i:i + 3]) for i in range(0, len(cells), 4))
            for i in range(0, len(cells), 4):
                config = self.fdt.node_offset_by_phandle(cells[i + 3])
                bias = "bias-pull-up" if cells[i + 1] in (11, 12) else "bias-disable"
                self.assertTrue(self.fdt.hasprop(config, bias))
                level = 1 if cells[i + 1] == 14 else 3
                self.assertEqual(self.cells(config, "drive-strength"), [level])
                self.assertTrue(self.fdt.hasprop(config, "input-schmitt-enable"))
        self.assertEqual(set(pins), {(2, 11, 2), (2, 12, 2), (2, 13, 2), (2, 14, 2)})
        self.assertEqual(list(self.children(uart)), [])

    def test_antenna_and_sdio_settings_remain_aic_specific(self):
        antenna = self.node("/regulator-board-antenna")
        gpio = self.alias("gpio3")
        self.assertEqual(self.cells(antenna, "gpio"),
                         [self.fdt.getprop(gpio, "phandle").as_uint32(), 27, 1])
        self.assertTrue(self.fdt.hasprop(antenna, "regulator-always-on"))
        self.assertEqual(self.cells(self.alias("mmc2"), "rockchip,default-sample-phase"), [180])
        self.assertEqual(self.fdt.getprop(self.alias("mmc0"), "status").as_str(), "disabled")

    def test_generic_tree_is_byte_identical(self):
        data = (DTB_DIR / "rk3566-radxa-zero-3w.dtb").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), GENERIC_SHA256)


if __name__ == "__main__":
    unittest.main()
