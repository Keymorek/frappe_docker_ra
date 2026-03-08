from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from helpers import FakeDoc, build_frappe_env


class TestStyleApi(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()
        self.env.meta_fields["Item"] = {
            "item_code",
            "item_name",
            "item_group",
            "stock_uom",
            "description",
            "brand",
            "style",
            "style_code",
            "size_system",
            "color_code",
            "color_name",
            "size_code",
            "size_name",
            "sellable",
            "sku_status",
            "is_stock_item",
        }

    def tearDown(self):
        self.env.cleanup()

    def test_create_template_item_api_reuses_loaded_style_doc(self):
        api_module = self.env.load_module("fashion_erp.style.api")
        style_doc = FakeDoc(
            doctype="Style",
            name="ST-001",
            style_name="西装外套",
            style_code="SZ001",
            item_group="成衣",
            description="测试款",
            brand="KM",
            size_system="TOP",
            item_template="",
        )
        style_load_count = 0
        inserted_docs: list[FakeDoc] = []

        def db_set(fieldname, value, update_modified=False):
            style_doc.item_template = value

        style_doc.db_set = db_set
        self.env.db.exists_map.update(
            {
                ("Item", "TPL-SZ001"): False,
            }
        )

        def get_doc(arg1, arg2=None):
            nonlocal style_load_count
            if isinstance(arg1, dict):
                doc = FakeDoc(name=arg1.get("item_code"), **arg1)

                def insert(ignore_permissions=False, *, _doc=doc):
                    inserted_docs.append(_doc)
                    _doc.insert_calls.append({"ignore_permissions": ignore_permissions})
                    return _doc

                doc.insert = insert
                return doc

            if (arg1, arg2) == ("Style", "ST-001"):
                style_load_count += 1
                return style_doc
            raise KeyError((arg1, arg2))

        self.env.get_doc_handler = get_doc

        result = api_module.create_template_item("ST-001")

        self.assertTrue(result["ok"])
        self.assertEqual(style_load_count, 1)
        self.assertEqual(result["result"]["item_code"], "TPL-SZ001")
        self.assertEqual(style_doc.item_template, "TPL-SZ001")
        self.assertEqual([doc.item_code for doc in inserted_docs], ["TPL-SZ001"])

    def test_generate_variants_api_reuses_loaded_style_doc(self):
        api_module = self.env.load_module("fashion_erp.style.api")
        style_doc = FakeDoc(
            doctype="Style",
            name="ST-001",
            style_name="西装外套",
            style_code="SZ001",
            item_group="成衣",
            description="测试款",
            brand="KM",
            size_system="TOP",
            style_sizes=[
                SimpleNamespace(size="TOP-S", size_code="S", size_name="S", sort_order=10),
                SimpleNamespace(size="TOP-M", size_code="M", size_name="M", sort_order=20),
            ],
            colors=[SimpleNamespace(enabled=1, color="黑色", color_name="黑色", color_code="BLK")],
        )
        style_load_count = 0
        inserted_docs: list[FakeDoc] = []

        def get_doc(arg1, arg2=None):
            nonlocal style_load_count
            if isinstance(arg1, dict):
                doc = FakeDoc(name=arg1.get("item_code"), **arg1)

                def insert(ignore_permissions=False, *, _doc=doc):
                    inserted_docs.append(_doc)
                    _doc.insert_calls.append({"ignore_permissions": ignore_permissions})
                    return _doc

                doc.insert = insert
                return doc

            if (arg1, arg2) == ("Style", "ST-001"):
                style_load_count += 1
                return style_doc
            raise KeyError((arg1, arg2))

        def get_all(doctype, **kwargs):
            if doctype == "Item":
                return []
            return []

        self.env.get_doc_handler = get_doc
        self.env.get_all_handler = get_all

        with patch("fashion_erp.style.api.get_style_variant_generation_issues", return_value=[]), patch(
            "fashion_erp.style.services.sku_service.get_style_variant_generation_issues",
            return_value=[],
        ), patch("fashion_erp.style.services.sku_service.get_brand_abbreviation", return_value="KM"):
            result = api_module.generate_variants("ST-001")

        self.assertTrue(result["ok"])
        self.assertEqual(style_load_count, 1)
        self.assertEqual(result["result"]["created"], ["KM-SZ001-BLK-S", "KM-SZ001-BLK-M"])
        self.assertEqual([doc.item_code for doc in inserted_docs], ["KM-SZ001-BLK-S", "KM-SZ001-BLK-M"])

    def test_get_style_matrix_api_reuses_loaded_style_doc(self):
        api_module = self.env.load_module("fashion_erp.style.api")
        style_doc = FakeDoc(
            doctype="Style",
            name="ST-001",
            style_name="西装外套",
            style_code="SZ001",
            brand="KM",
            size_system="TOP",
            style_sizes=[
                SimpleNamespace(size="TOP-S", size_code="S", size_name="S", sort_order=10),
                SimpleNamespace(size="TOP-M", size_code="M", size_name="M", sort_order=20),
            ],
            colors=[SimpleNamespace(enabled=1, color="黑色", color_name="黑色", color_code="BLK")],
        )
        style_load_count = 0
        self.env.db.exists_map[("DocType", "Bin")] = False

        def get_doc(doctype, name=None):
            nonlocal style_load_count
            if (doctype, name) == ("Style", "ST-001"):
                style_load_count += 1
                return style_doc
            raise KeyError((doctype, name))

        def get_all(doctype, **kwargs):
            if doctype == "Item":
                return []
            return []

        self.env.get_doc_handler = get_doc
        self.env.get_all_handler = get_all

        with patch("fashion_erp.style.services.sku_service.get_style_variant_generation_issues", return_value=[]), patch(
            "fashion_erp.style.services.sku_service.get_brand_abbreviation",
            return_value="KM",
        ):
            result = api_module.get_style_matrix("ST-001")

        self.assertTrue(result["ok"])
        self.assertEqual(style_load_count, 1)
        self.assertEqual(result["result"]["summary"]["missing_count"], 2)
        self.assertEqual(result["result"]["summary"]["existing_count"], 0)


if __name__ == "__main__":
    unittest.main()
