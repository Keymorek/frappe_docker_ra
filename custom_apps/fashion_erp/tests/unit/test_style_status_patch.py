from __future__ import annotations

import unittest

from helpers import build_frappe_env


class TestStyleStatusPatch(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()
        self.env.db.exists_map[("DocType", "Style")] = True
        self.env.meta_fields["Style"] = {"season", "gender", "launch_status", "sales_status"}

    def tearDown(self):
        self.env.cleanup()

    def test_patch_translates_style_select_values_to_zh(self):
        module = self.env.load_module("fashion_erp.patches.v1_3.normalize_style_select_values")

        def get_all_handler(doctype, filters=None, **kwargs):
            if doctype != "Style":
                return []
            if filters == {"launch_status": "Draft"}:
                return ["STYLE-001"]
            if filters == {"launch_status": "LAUNCHED"}:
                return ["STYLE-002"]
            if filters == {"sales_status": "On Sale"}:
                return ["STYLE-003"]
            if filters == {"gender": "Women"}:
                return ["STYLE-004"]
            return []

        self.env.get_all_handler = get_all_handler

        module.execute()

        self.assertIn(
            ("Style", "STYLE-001", "launch_status", "草稿", {"update_modified": False}),
            self.env.db.set_value_calls,
        )
        self.assertIn(
            ("Style", "STYLE-002", "launch_status", "已上市", {"update_modified": False}),
            self.env.db.set_value_calls,
        )
        self.assertIn(
            ("Style", "STYLE-003", "sales_status", "在售", {"update_modified": False}),
            self.env.db.set_value_calls,
        )
        self.assertIn(
            ("Style", "STYLE-004", "gender", "女装", {"update_modified": False}),
            self.env.db.set_value_calls,
        )


if __name__ == "__main__":
    unittest.main()
