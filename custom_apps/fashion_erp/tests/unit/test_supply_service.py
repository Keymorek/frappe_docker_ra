from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from helpers import build_frappe_env


class TestSupplyService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_validate_supply_purchase_receipt_backfills_outsource_context_from_purchase_order(self):
        module = self.env.load_module("fashion_erp.stock.services.supply_service")

        self.env.db.exists_map.update(
            {
                ("Item", "FAB-001"): True,
                ("Purchase Order Item", "POI-001"): True,
                ("Outsource Order", "WB-001"): True,
                ("Sample Ticket", "SMP-001"): True,
                ("Style", "ST-001"): True,
                ("Warehouse", "WH-RAW"): True,
            }
        )
        self.env.db.value_map.update(
            {
                ("Item", "FAB-001", ("item_usage_type", "supply_warehouse"), True): {
                    "item_usage_type": "面料",
                    "supply_warehouse": "WH-RAW",
                },
                ("Purchase Order Item", "POI-001", ("reference_style", "reference_outsource_order", "reference_sample_ticket", "supply_context"), True): {
                    "reference_style": "",
                    "reference_outsource_order": "WB-001",
                    "reference_sample_ticket": "SMP-001",
                    "supply_context": "外包备货",
                },
                ("Sample Ticket", "SMP-001", "style"): "ST-001",
            }
        )
        self.env.get_cached_doc_handler = lambda doctype, name: SimpleNamespace(
            order_status="已下单",
            style="ST-001",
            sample_ticket="SMP-001",
            materials=[SimpleNamespace(item_code="FAB-001")],
        )

        row = SimpleNamespace(
            idx=1,
            item_code="FAB-001",
            warehouse="",
            reference_style="",
            reference_outsource_order="",
            reference_sample_ticket="",
            supply_context="",
            purchase_order_item="POI-001",
        )
        doc = SimpleNamespace(
            supply_receipt_type="",
            supplier="",
            set_warehouse="WH-HEADER",
            items=[row],
        )

        with patch.object(module, "_get_supplier_role", return_value=""):
            module.validate_supply_purchase_receipt(doc)

        self.assertEqual(row.supply_context, "外包备货")
        self.assertEqual(row.reference_outsource_order, "WB-001")
        self.assertEqual(row.reference_style, "ST-001")
        self.assertEqual(row.reference_sample_ticket, "SMP-001")
        self.assertEqual(row.warehouse, "WH-RAW")

    def test_sync_outsource_supply_context_rejects_item_not_in_order_materials(self):
        module = self.env.load_module("fashion_erp.stock.services.supply_service")
        self.env.get_cached_doc_handler = lambda doctype, name: SimpleNamespace(
            order_status="已下单",
            style="ST-001",
            sample_ticket="",
            materials=[SimpleNamespace(item_code="FAB-001")],
        )

        row = SimpleNamespace(
            idx=2,
            reference_outsource_order="WB-001",
            supply_context="外包备货",
            reference_style="",
            reference_sample_ticket="",
            item_code="FAB-999",
        )

        with self.assertRaisesRegex(self.env.FrappeThrow, "供料清单"):
            module._sync_outsource_supply_context(row, "面料", item_label="采购明细")


if __name__ == "__main__":
    unittest.main()
