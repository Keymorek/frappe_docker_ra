from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from helpers import FakeDoc, build_frappe_env


class TestSeedAndSkuFlow(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_seed_stock_master_data_is_idempotent(self):
        module = self.env.load_module("fashion_erp.stock.services.stock_service")
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
        self.env.get_all_handler = lambda doctype, **kwargs: [
            {"name": "S", "size_code": "S", "size_name": "S", "sort_order": 10},
            {"name": "M", "size_code": "M", "size_name": "M", "sort_order": 20},
            {"name": "L", "size_code": "L", "size_name": "L", "sort_order": 30},
        ]
        self.env.db.exists_map.update(
            {
                ("Item", "KM-SZ001-BLK-S"): True,
                ("Item", "KM-SZ001-BLK-M"): True,
                ("Item", "KM-SZ001-BLK-L"): False,
            }
        )

        with patch.object(module, "get_style_variant_generation_issues", return_value=[]), patch.object(
            module,
            "get_enabled_size_codes",
            return_value=["S", "M", "L"],
        ), patch.object(module, "get_brand_sku_prefix", return_value="KM"):
            result = module.generate_variants_for_style("ST-001")

        self.assertEqual(result["created"], ["KM-SZ001-BLK-L"])
        self.assertEqual(result["updated"], ["KM-SZ001-BLK-S"])
        self.assertEqual(result["skipped"], ["KM-SZ001-BLK-M"])
        self.assertEqual(result["size_codes"], ["S", "M", "L"])
        self.assertEqual(existing_item.item_name, "西装外套 / 黑色 / S")
        self.assertEqual(len(existing_item.save_calls), 1)
        self.assertEqual([doc.item_code for doc in inserted_docs], ["KM-SZ001-BLK-L"])


if __name__ == "__main__":
    unittest.main()
