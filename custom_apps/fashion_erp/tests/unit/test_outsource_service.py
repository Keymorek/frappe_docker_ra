from __future__ import annotations

import unittest
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch

from helpers import build_frappe_env


class TestOutsourceService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_build_purchase_qty_scope_maps_groups_by_item_and_warehouse(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_service")

        scope_maps = module._build_purchase_qty_scope_maps(
            [
                {"item_code": "FAB-001", "warehouse": "WH-A", "outstanding_qty": 5},
                {"item_code": "FAB-001", "warehouse": "", "outstanding_qty": 3},
                {"item_code": "TRIM-001", "warehouse": "WH-B", "outstanding_qty": 2},
            ]
        )

        self.assertEqual(scope_maps["by_item"], {"FAB-001": 8.0, "TRIM-001": 2.0})
        self.assertEqual(
            scope_maps["by_item_warehouse"],
            {
                ("FAB-001", "WH-A"): 5.0,
                ("FAB-001", ""): 3.0,
                ("TRIM-001", "WH-B"): 2.0,
            },
        )
        self.assertEqual(scope_maps["generic_by_item"], {"FAB-001": 3.0})

    def test_get_outsource_supply_summary_uses_legacy_purchase_scope_as_fallback(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_service")
        doc = SimpleNamespace(
            name="WB-001",
            order_no="WB-001",
            style="ST-001",
            style_name="测试款",
            materials=[object()],
        )

        with patch.object(module, "_get_outsource_order_doc", return_value=doc), patch.object(
            module,
            "_group_outsource_materials",
            return_value={
                "FAB-001": {
                    "item_name": "面料A",
                    "uom": "M",
                    "required_qty": 10,
                    "prepared_qty": 2,
                    "issued_qty": 1,
                    "warehouses": ["WH-A"],
                    "default_locations": ["A-01"],
                    "row_indexes": [1],
                }
            },
        ), patch.object(
            module,
            "_get_on_hand_qty_maps",
            return_value=({"FAB-001": 3}, {("FAB-001", "WH-A"): 3}),
        ), patch.object(
            module,
            "_get_open_purchase_qty_maps",
            return_value={
                "linked": module._build_purchase_qty_scope_maps(),
                "legacy": module._build_purchase_qty_scope_maps(
                    [{"item_code": "FAB-001", "warehouse": "WH-A", "outstanding_qty": 4}]
                ),
            },
        ):
            result = module.get_outsource_supply_summary("WB-001")

        row = result["rows"][0]
        self.assertEqual(row["on_order_qty"], 4.0)
        self.assertEqual(row["to_purchase_qty"], 1.0)
        self.assertIn("旧采购数据", row["warning"])

    def test_normalize_materials_reuses_cached_item_and_location_queries_for_duplicate_rows(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_service")
        self.env.db.value_map[
            (
                "Item",
                "FAB-001",
                ("item_name", "item_usage_type", "stock_uom", "supply_warehouse", "default_location"),
                True,
            )
        ] = {
            "item_name": "面料A",
            "item_usage_type": "面料",
            "stock_uom": "M",
            "supply_warehouse": "WH-RAW",
            "default_location": "A-01",
        }
        self.env.db.value_map[("Warehouse Location", "A-01", "warehouse", False)] = "WH-RAW"
        lookup_counter = Counter()
        original_get_value = self.env.db.get_value

        def counting_get_value(doctype, name, fieldname, as_dict=False):
            frozen_field = tuple(fieldname) if isinstance(fieldname, list) else fieldname
            lookup_counter[(doctype, name, frozen_field, as_dict)] += 1
            return original_get_value(doctype, name, fieldname, as_dict=as_dict)

        self.env.db.get_value = counting_get_value
        doc = SimpleNamespace(
            flags=SimpleNamespace(),
            materials=[
                SimpleNamespace(
                    idx=1,
                    item_code="FAB-001",
                    item_name="",
                    item_usage_type="",
                    uom="",
                    planned_qty=10,
                    prepared_qty=2,
                    issued_qty_manual=1,
                    warehouse="",
                    default_location="",
                    remark="",
                ),
                SimpleNamespace(
                    idx=2,
                    item_code="FAB-001",
                    item_name="",
                    item_usage_type="",
                    uom="",
                    planned_qty=8,
                    prepared_qty=0,
                    issued_qty_manual=0,
                    warehouse="",
                    default_location="",
                    remark="",
                ),
            ],
        )

        with patch.object(module, "ensure_link_exists", return_value=None) as link_mock, patch.object(
            module,
            "ensure_enabled_link",
            return_value=None,
        ) as enabled_mock:
            module._normalize_materials(doc)

        self.assertEqual(doc.materials[0].item_name, "面料A")
        self.assertEqual(doc.materials[1].item_name, "面料A")
        self.assertEqual(doc.materials[0].warehouse, "WH-RAW")
        self.assertEqual(doc.materials[1].warehouse, "WH-RAW")
        self.assertEqual(doc.materials[0].default_location, "A-01")
        self.assertEqual(doc.materials[1].default_location, "A-01")
        self.assertEqual(link_mock.call_count, 2)
        self.assertEqual(enabled_mock.call_count, 1)
        self.assertEqual(
            lookup_counter[
                (
                    "Item",
                    "FAB-001",
                    ("item_name", "item_usage_type", "stock_uom", "supply_warehouse", "default_location"),
                    True,
                )
            ],
            1,
        )
        self.assertEqual(
            lookup_counter[("Warehouse Location", "A-01", "warehouse", False)],
            1,
        )


if __name__ == "__main__":
    unittest.main()
