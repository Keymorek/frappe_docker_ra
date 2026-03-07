from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from helpers import build_frappe_env


class TestOutsourceService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_build_purchase_qty_scope_maps_groups_by_item_and_warehouse(self):
        module = self.env.load_module("fashion_erp.stock.services.outsource_service")

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
        module = self.env.load_module("fashion_erp.stock.services.outsource_service")
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


if __name__ == "__main__":
    unittest.main()
