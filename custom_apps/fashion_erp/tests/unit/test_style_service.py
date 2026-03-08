from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_build_style_category_template_details_supports_up_to_four_levels(self):
        module = self.env.load_module("fashion_erp.style.services.style_service")

        details = module.build_style_category_template_details("女装", "裤子", "休闲裤", "无")

        self.assertEqual(details["category_level_1"], "女装")
        self.assertEqual(details["category_level_2"], "裤子")
        self.assertEqual(details["category_level_3"], "休闲裤")
        self.assertEqual(details["category_level_4"], "")
        self.assertEqual(details["leaf_category_name"], "休闲裤")
        self.assertEqual(details["full_path"], "女装 / 裤子 / 休闲裤")
        self.assertEqual(details["level_depth"], 3)

    def test_build_style_category_template_details_rejects_skipped_levels(self):
        module = self.env.load_module("fashion_erp.style.services.style_service")

        with self.assertRaisesRegex(self.env.FrappeThrow, "不能跳级"):
            module.build_style_category_template_details("女装", "", "休闲裤", "")

    def test_build_style_category_template_details_requires_second_level_for_douyin(self):
        module = self.env.load_module("fashion_erp.style.services.style_service")

        with self.assertRaisesRegex(self.env.FrappeThrow, "至少需要维护到二级类目"):
            module.build_style_category_template_details("女装", "", "", "", source_platform="抖音")

    def test_load_style_category_template_seeds_reads_csv_template(self):
        module = self.env.load_module("fashion_erp.style.services.style_service")

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "抖音抖店女装服饰内衣类目.csv"
            csv_path.write_text(
                "平台,原始模版文本,一级类目,二级类目,三级类目,四级类目\n"
                "抖音,女装-裤子-休闲裤-无,女装,裤子,休闲裤,无\n",
                encoding="utf-8-sig",
            )

            with patch.object(module, "_find_style_category_csv_path", return_value=csv_path):
                rows = module.load_style_category_template_seeds()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_platform"], "抖音")
        self.assertEqual(rows[0]["external_text"], "女装-裤子-休闲裤-无")
        self.assertEqual(rows[0]["full_path"], "女装 / 裤子 / 休闲裤")
        self.assertEqual(rows[0]["leaf_category_name"], "休闲裤")
        self.assertEqual(rows[0]["default_size_system"], "BOTTOM")
        self.assertEqual(rows[0]["allowed_size_systems"], "BOTTOM")

    def test_load_style_category_template_seeds_supports_legacy_text_column(self):
        module = self.env.load_module("fashion_erp.style.services.style_service")

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "抖音抖店女装服饰内衣类目.csv"
            csv_path.write_text(
                "平台,文本,一级类目,二级类目,三级类目,四级类目\n"
                "抖音,女装-T 恤-无-无,女装,T 恤,无,无\n",
                encoding="utf-8-sig",
            )

            with patch.object(module, "_find_style_category_csv_path", return_value=csv_path):
                rows = module.load_style_category_template_seeds()

        self.assertEqual(1, len(rows))
        self.assertEqual("女装-T 恤-无-无", rows[0]["external_text"])

    def test_get_product_category_size_rule_parses_allowed_systems(self):
        module = self.env.load_module("fashion_erp.style.services.style_service")
        self.env.db.value_map[
            (
                "Style Category Template",
                "女装 / 套装",
                ("default_size_system", "allowed_size_systems", "full_path"),
                True,
            )
        ] = {
            "default_size_system": "TOP",
            "allowed_size_systems": "TOP\nFREE",
            "full_path": "女装 / 套装",
        }

        rule = module.get_product_category_size_rule("女装 / 套装")

        self.assertEqual(rule["default_size_system"], "TOP")
        self.assertEqual(rule["allowed_size_systems"], ["TOP", "FREE"])

    def test_normalize_select_matches_alias_case_insensitively(self):
        module = self.env.load_module("fashion_erp.style.services.style_service")

        self.assertEqual(
            module.normalize_select(
                "launched",
                "上市状态",
                ("草稿", "已上市"),
                alias_map={"Launched": "已上市"},
            ),
            "已上市",
        )


if __name__ == "__main__":
    unittest.main()
