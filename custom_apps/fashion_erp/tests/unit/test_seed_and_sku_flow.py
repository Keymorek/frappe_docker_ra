from __future__ import annotations

import unittest
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch

from helpers import FakeDoc, build_frappe_env


class TestSeedAndSkuFlow(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_seed_stock_master_data_is_idempotent(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.stock_service")
        store: dict[tuple[str, str], FakeDoc] = {}

        def exists(doctype: str, name: str) -> bool:
            return (doctype, name) in store

        def get_doc(arg1, arg2=None):
            if isinstance(arg1, dict):
                payload = dict(arg1)
                doctype = payload.pop("doctype")
                name_field = {
                    "Warehouse Zone": "zone_code",
                    "Inventory Status": "status_code",
                    "Return Reason": "reason_code",
                    "Return Disposition": "disposition_code",
                }[doctype]
                name = payload[name_field]
                doc = FakeDoc(doctype=doctype, name=name, **payload)

                def insert(ignore_permissions=False, *, _doc=doc):
                    store[(doctype, name)] = _doc
                    _doc.insert_calls.append({"ignore_permissions": ignore_permissions})
                    return _doc

                doc.insert = insert
                return doc

            return store[(arg1, arg2)]

        self.env.db.exists = exists
        self.env.get_doc_handler = get_doc

        module.seed_stock_master_data()
        first_counts = {key: len(doc.insert_calls) for key, doc in store.items()}
        total_seed_docs = (
            len(module.WAREHOUSE_ZONE_SEEDS)
            + len(module.INVENTORY_STATUS_SEEDS)
            + len(module.RETURN_REASON_SEEDS)
            + len(module.RETURN_DISPOSITION_SEEDS)
        )

        module.seed_stock_master_data()

        self.assertEqual(len(store), total_seed_docs)
        self.assertEqual(first_counts, {key: len(doc.insert_calls) for key, doc in store.items()})
        self.assertTrue(all(len(doc.save_calls) == 0 for doc in store.values()))

    def test_generate_variants_for_style_creates_updates_and_skips(self):
        module = self.env.load_module("fashion_erp.style.services.sku_service")
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
        }

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
                SimpleNamespace(size="TOP-L", size_code="L", size_name="L", sort_order=30),
            ],
            colors=[
                SimpleNamespace(enabled=1, color="黑色", color_name="黑色", color_code="BLK"),
            ],
        )
        existing_item = FakeDoc(
            doctype="Item",
            name="KM-SZ001-BLK-S",
            item_name="旧名称",
            item_group="成衣",
            description="旧描述",
            brand="KM",
            style="ST-001",
            style_code="SZ001",
            size_system="TOP",
            color_code="BLK",
            color_name="黑色",
            size_code="S",
            size_name="S",
            sellable=1,
            sku_status="正常",
        )
        skipped_item = FakeDoc(
            doctype="Item",
            name="KM-SZ001-BLK-M",
            item_name="西装外套 / 黑色 / M",
            item_group="成衣",
            description="测试款",
            brand="KM",
            style="ST-001",
            style_code="SZ001",
            size_system="TOP",
            color_code="BLK",
            color_name="黑色",
            size_code="M",
            size_name="M",
            sellable=1,
            sku_status="正常",
        )
        inserted_docs: list[FakeDoc] = []

        def get_doc(arg1, arg2=None):
            if isinstance(arg1, dict):
                doc = FakeDoc(**arg1)

                def insert(ignore_permissions=False, *, _doc=doc):
                    inserted_docs.append(_doc)
                    _doc.insert_calls.append({"ignore_permissions": ignore_permissions})
                    return _doc

                doc.insert = insert
                return doc

            if arg1 == "Style":
                return style_doc
            if arg1 == "Item" and arg2 == "KM-SZ001-BLK-S":
                return existing_item
            if arg1 == "Item" and arg2 == "KM-SZ001-BLK-M":
                return skipped_item
            raise KeyError((arg1, arg2))

        self.env.get_doc_handler = get_doc
        self.env.get_all_handler = lambda doctype, **kwargs: (
            [
                {"item_code": "KM-SZ001-BLK-S"},
                {"item_code": "KM-SZ001-BLK-M"},
            ]
            if doctype == "Item"
            else []
        )
        self.env.db.exists_map.update(
            {
                ("Item", "KM-SZ001-BLK-S"): True,
                ("Item", "KM-SZ001-BLK-M"): True,
                ("Item", "KM-SZ001-BLK-L"): False,
            }
        )

        with patch.object(module, "get_style_variant_generation_issues", return_value=[]), patch.object(
            module,
            "get_brand_abbreviation",
            return_value="KM",
        ):
            result = module.generate_variants_for_style("ST-001")

        self.assertEqual(result["created"], ["KM-SZ001-BLK-L"])
        self.assertEqual(result["updated"], ["KM-SZ001-BLK-S"])
        self.assertEqual(result["skipped"], ["KM-SZ001-BLK-M"])
        self.assertEqual(result["size_codes"], ["S", "M", "L"])
        self.assertEqual(existing_item.item_name, "西装外套 / 黑色 / S")
        self.assertEqual(len(existing_item.save_calls), 1)
        self.assertEqual([doc.item_code for doc in inserted_docs], ["KM-SZ001-BLK-L"])

    def test_generate_variants_for_style_preloads_existing_items_in_batch(self):
        module = self.env.load_module("fashion_erp.style.services.sku_service")
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
        }
        get_all_counter = Counter()
        exists_counter = Counter()
        original_exists = self.env.db.exists

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
            colors=[
                SimpleNamespace(enabled=1, color="黑色", color_name="黑色", color_code="BLK"),
            ],
        )
        existing_item = FakeDoc(
            doctype="Item",
            name="KM-SZ001-BLK-S",
            item_name="旧名称",
            item_group="成衣",
            description="旧描述",
            brand="KM",
            style="ST-001",
            style_code="SZ001",
            size_system="TOP",
            color_code="BLK",
            color_name="黑色",
            size_code="S",
            size_name="S",
            sellable=1,
            sku_status="正常",
        )
        inserted_docs: list[FakeDoc] = []

        def counting_exists(doctype: str, name: str) -> bool:
            exists_counter[(doctype, name)] += 1
            return original_exists(doctype, name)

        def get_doc(arg1, arg2=None):
            if isinstance(arg1, dict):
                doc = FakeDoc(**arg1)

                def insert(ignore_permissions=False, *, _doc=doc):
                    inserted_docs.append(_doc)
                    _doc.insert_calls.append({"ignore_permissions": ignore_permissions})
                    return _doc

                doc.insert = insert
                return doc

            if arg1 == "Style":
                return style_doc
            if arg1 == "Item" and arg2 == "KM-SZ001-BLK-S":
                return existing_item
            raise KeyError((arg1, arg2))

        def get_all(doctype, **kwargs):
            get_all_counter[doctype] += 1
            if doctype == "Item":
                self.assertEqual(
                    kwargs.get("filters"),
                    [["Item", "item_code", "in", ["KM-SZ001-BLK-S", "KM-SZ001-BLK-M"]]],
                )
                return [{"item_code": "KM-SZ001-BLK-S"}]
            return []

        self.env.db.exists = counting_exists
        self.env.get_doc_handler = get_doc
        self.env.get_all_handler = get_all

        with patch.object(module, "get_style_variant_generation_issues", return_value=[]), patch.object(
            module,
            "get_brand_abbreviation",
            return_value="KM",
        ):
            result = module.generate_variants_for_style("ST-001")

        self.assertEqual(get_all_counter["Size Code"], 0)
        self.assertEqual(get_all_counter["Item"], 1)
        self.assertEqual(exists_counter[("Item", "KM-SZ001-BLK-S")], 0)
        self.assertEqual(exists_counter[("Item", "KM-SZ001-BLK-M")], 0)
        self.assertEqual(result["updated"], ["KM-SZ001-BLK-S"])
        self.assertEqual(result["created"], ["KM-SZ001-BLK-M"])
        self.assertEqual(result["size_codes"], ["S", "M"])
        self.assertEqual([doc.item_code for doc in inserted_docs], ["KM-SZ001-BLK-M"])

    def test_build_style_matrix_preloads_items_and_bins_in_batch(self):
        module = self.env.load_module("fashion_erp.style.services.sku_service")
        self.env.meta_fields["Item"] = {"name", "item_code", "item_name", "sellable"}
        self.env.db.exists_map[("DocType", "Bin")] = True
        get_all_counter = Counter()

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
            colors=[
                SimpleNamespace(enabled=1, color="黑色", color_name="黑色", color_code="BLK"),
                SimpleNamespace(enabled=1, color="白色", color_name="白色", color_code="WHT"),
            ],
        )

        def get_all(doctype, **kwargs):
            get_all_counter[doctype] += 1
            if doctype == "Item":
                self.assertEqual(
                    kwargs.get("filters"),
                    [["Item", "item_code", "in", ["KM-SZ001-BLK-S", "KM-SZ001-BLK-M", "KM-SZ001-WHT-S", "KM-SZ001-WHT-M"]]],
                )
                return [
                    {
                        "name": "KM-SZ001-BLK-S",
                        "item_code": "KM-SZ001-BLK-S",
                        "item_name": "西装外套 / 黑色 / S",
                        "sellable": 1,
                    },
                    {
                        "name": "KM-SZ001-WHT-M",
                        "item_code": "KM-SZ001-WHT-M",
                        "item_name": "西装外套 / 白色 / M",
                        "sellable": 1,
                    },
                ]
            if doctype == "Bin":
                self.assertEqual(
                    kwargs.get("filters"),
                    [["Bin", "item_code", "in", ["KM-SZ001-BLK-S", "KM-SZ001-BLK-M", "KM-SZ001-WHT-S", "KM-SZ001-WHT-M"]]],
                )
                return [
                    {"item_code": "KM-SZ001-BLK-S", "actual_qty": 5},
                    {"item_code": "KM-SZ001-WHT-M", "actual_qty": 2},
                    {"item_code": "KM-SZ001-WHT-M", "actual_qty": 3},
                ]
            return []

        self.env.get_doc_handler = lambda doctype, name=None: style_doc if (doctype, name) == ("Style", "ST-001") else None
        self.env.get_all_handler = get_all

        with patch.object(module, "get_style_variant_generation_issues", return_value=[]), patch.object(
            module,
            "get_brand_abbreviation",
            return_value="KM",
        ):
            result = module.build_style_matrix("ST-001")

        self.assertEqual(get_all_counter["Size Code"], 0)
        self.assertEqual(get_all_counter["Item"], 1)
        self.assertEqual(get_all_counter["Bin"], 1)
        self.assertEqual(result["summary"]["existing_count"], 2)
        self.assertEqual(result["summary"]["missing_count"], 2)
        self.assertEqual(result["matrix_rows"][0]["cells"][0]["stock_qty"], 5)
        self.assertEqual(result["matrix_rows"][1]["cells"][1]["stock_qty"], 5)
        self.assertEqual(result["matrix_rows"][0]["cells"][1]["exists"], False)


if __name__ == "__main__":
    unittest.main()
