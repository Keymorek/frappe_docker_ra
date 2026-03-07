from __future__ import annotations

import unittest

from helpers import build_frappe_env


class TestStyleService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_normalize_select_supports_alias_and_default(self):
        module = self.env.load_module("fashion_erp.style.services.style_service")

        self.assertEqual(
            module.normalize_select(
                "SS",
                "季节",
                ("春夏", "秋冬"),
                default="秋冬",
                alias_map={"SS": "春夏"},
            ),
            "春夏",
        )
        self.assertEqual(module.normalize_select("", "季节", ("春夏", "秋冬"), default="秋冬"), "秋冬")

    def test_ensure_enabled_link_rejects_disabled_doc(self):
        module = self.env.load_module("fashion_erp.style.services.style_service")
        self.env.db.exists_map[("Brand", "BR-001")] = True
        self.env.db.value_map[("Brand", "BR-001", "enabled")] = 0

        with self.assertRaisesRegex(self.env.FrappeThrow, "已停用"):
            module.ensure_enabled_link("Brand", "BR-001")


if __name__ == "__main__":
    unittest.main()
