from __future__ import annotations

import json
import unittest
from pathlib import Path


STYLE_DOCTYPES = (
    "color",
    "color_group",
    "craft_sheet",
    "fabric_master",
    "sample_ticket",
    "size_code",
    "size_system",
    "style",
    "style_category",
    "style_category_template",
    "style_season",
    "style_sub_category",
    "style_year",
)


class TestStyleMetadata(unittest.TestCase):
    def test_style_doctypes_grant_stock_manager_maintenance_access(self):
        root = Path("custom_apps/fashion_erp/fashion_erp/style/doctype")

        for doctype_name in STYLE_DOCTYPES:
            with self.subTest(doctype=doctype_name):
                json_path = root / doctype_name / f"{doctype_name}.json"
                payload = json.loads(json_path.read_text(encoding="utf-8"))
                roles = {row.get("role") for row in payload.get("permissions") or []}
                self.assertIn("System Manager", roles)
                self.assertIn("Stock Manager", roles)
                self.assertIn("Item Manager", roles)

    def test_style_category_template_disables_quick_entry_and_labels_full_path_usage(self):
        json_path = Path(
            "custom_apps/fashion_erp/fashion_erp/style/doctype/style_category_template/style_category_template.json"
        )
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        fields = {field["fieldname"]: field for field in payload["fields"]}

        self.assertEqual(0, payload.get("quick_entry"))
        self.assertIn("完整路径", fields["category_level_1"].get("description", ""))
        self.assertIn("完整路径", fields["full_path"].get("description", ""))


if __name__ == "__main__":
    unittest.main()
