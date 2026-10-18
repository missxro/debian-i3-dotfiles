"""Repository checks: portable defaults and an explicit public-file boundary."""
import configparser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def test_core_configuration_is_present_and_portable(self):
        required = [
            "config/i3/config", "config/polybar/config.ini",
            "config/kitty/kitty.conf", "config/kitty/color.ini",
            "config/kitty/current-theme.conf", "config/picom/picom.conf",
        ]
        for name in required:
            with self.subTest(file=name):
                path = ROOT / name
                self.assertTrue(path.is_file(), f"Missing {name}")
                text = path.read_text()
                self.assertNotRegex(text, r"/home/[^\s\"']+|/Users/|/opt/(?:data)/")
                self.assertNotRegex(text, r"DisplayPort-\d|HDMI-A-\d|--rate\s+\d")

    def test_polybar_references_only_defined_modules(self):
        parser = configparser.ConfigParser(interpolation=None)
        self.assertTrue(parser.read(ROOT / "config/polybar/config.ini"))
        bars = [s for s in parser.sections() if s.startswith("bar/")]
        self.assertEqual(bars, ["bar/main"])
        self.assertEqual(parser["bar/main"]["monitor"], "${env:MONITOR:}")
        for key in ("modules-left", "modules-center", "modules-right"):
            for module in parser["bar/main"].get(key, "").split():
                self.assertIn("module/" + module, parser)

    def test_i3_does_not_force_hardware_or_restart_supervisors_on_reload(self):
        text = (ROOT / "config/i3/config").read_text()
        active = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        self.assertNotIn("xrandr --output", active)
        self.assertNotIn("experimental-backends", active)
        self.assertNotRegex(active, r"client\.\w+_floating")
        self.assertNotRegex(active, r"exec_always.*(?:picom|wallpaper|polybar)")
        self.assertIn("wallpaper-wrap", active)


class PublicBoundaryTests(unittest.TestCase):
    def test_no_private_paths_or_network_addresses_in_public_files(self):
        for folder in (ROOT / "config", ROOT / "bin", ROOT / "docs"):
            if not folder.exists():
                continue
            for path in folder.rglob("*"):
                if not path.is_file() or "__pycache__" in path.parts:
                    continue
                if path == ROOT / "config/fastfetch/roxy-mushoku-tensei-2.png":
                    self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                    continue
                text = path.read_text()
                with self.subTest(file=str(path.relative_to(ROOT))):
                    self.assertNotRegex(text, r"/home/[^\s\"']+|/Users/|/opt/(?:data)/|[A-Za-z]:\\Users\\")
                    self.assertNotRegex(text, r"\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b|-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----")
                    self.assertNotRegex(text, r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})\b")


if __name__ == "__main__":
    unittest.main()
