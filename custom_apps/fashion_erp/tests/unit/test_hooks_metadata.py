from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


class TestHooksMetadata(unittest.TestCase):
    def test_apps_screen_entry_points_to_workspace_route(self):
        from fashion_erp import hooks

        self.assertEqual("/desk/fashion-erp", hooks.app_home)
        self.assertEqual("/assets/fashion_erp/images/fashion-erp-logo.svg", hooks.app_logo_url)

        entries = hooks.add_to_apps_screen
        self.assertTrue(entries)
        fashion_entry = next(entry for entry in entries if entry["name"] == "fashion_erp")
        self.assertEqual("时尚企业管理", fashion_entry["title"])
        self.assertEqual("fashion_erp.utils.has_app_permission", fashion_entry["has_permission"])
        self.assertEqual("/assets/fashion_erp/images/fashion-erp-logo.svg", fashion_entry["logo"])
        self.assertEqual("/desk/fashion-erp", fashion_entry["route"])


if __name__ == "__main__":
    unittest.main()
