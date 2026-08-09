import pathlib
import unittest

class SecurityTests(unittest.TestCase):
    def test_manifest_declares_no_live_execution(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        text = (root / "manifest.toml").read_text(encoding="utf-8")
        self.assertIn('"live_order_submit"', text)
        self.assertIn('"fund_transfer"', text)

    def test_plugin_has_no_secret_files(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        bad_names = {".env", "secrets.json", "credentials.json", "api_keys.txt"}
        self.assertFalse(any(path.name.lower() in bad_names for path in root.rglob("*") if path.is_file()))
