from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from helpers import build_frappe_env


class TestOutsourceReceiptService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_validate_qc_result_completion_requires_full_allocation(self):
        module = self.env.load_module("fashion_erp.stock.services.outsource_receipt_service")
        doc = SimpleNamespace(
            items=[
                SimpleNamespace(
                    idx=1,
                    qty=10,
                    sellable_qty=7,
                    repair_qty=1,
                    defective_qty=0,
                    frozen_qty=0,
                )
            ]
        )

        with self.assertRaisesRegex(self.env.FrappeThrow, "质检分配数量必须等于到货数量"):
            module._validate_qc_result_completion(doc)

    def test_build_final_stock_entry_items_splits_qc_results_by_target_status(self):
        module = self.env.load_module("fashion_erp.stock.services.outsource_receipt_service")
        transition_calls = []

        def build_row_payload(doc, row, **kwargs):
            return {
                "item_code": row.item_code,
                "qty": kwargs["qty"],
                "inventory_status_to": kwargs["inventory_status_to"],
            }

        with patch.object(module, "_build_stock_entry_row_payload", side_effect=build_row_payload), patch.object(
            module,
            "validate_inventory_status_transition",
            side_effect=lambda from_status, to_status, row_label="": transition_calls.append(
                (from_status, to_status, row_label)
            ),
        ):
            doc = SimpleNamespace(
                name="DH-001",
                outsource_order="WB-001",
                warehouse="WH-QC",
                items=[
                    SimpleNamespace(
                        idx=1,
                        item_code="FG-001",
                        qty=10,
                        sellable_qty=8,
                        repair_qty=1,
                        defective_qty=0,
                        frozen_qty=1,
                        style="ST-001",
                        color_code="BLK",
                        size_code="M",
                    )
                ],
            )

            items = module._build_final_stock_entry_items(doc)

        self.assertEqual(
            items,
            [
                {"item_code": "FG-001", "qty": 8, "inventory_status_to": "SELLABLE"},
                {"item_code": "FG-001", "qty": 1, "inventory_status_to": "REPAIR"},
                {"item_code": "FG-001", "qty": 1, "inventory_status_to": "FROZEN"},
            ],
        )
        self.assertEqual(
            transition_calls,
            [
                ("QC_PENDING", "SELLABLE", "到货明细第 1 行"),
                ("QC_PENDING", "REPAIR", "到货明细第 1 行"),
                ("QC_PENDING", "FROZEN", "到货明细第 1 行"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
