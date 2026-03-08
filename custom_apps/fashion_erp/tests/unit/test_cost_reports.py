from __future__ import annotations

import unittest

from helpers import build_frappe_env


class TestCostReports(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_outsource_estimated_cost_analysis_returns_progress_and_amounts(self):
        module = self.env.load_module(
            "fashion_erp.fashion_stock.report.outsource_estimated_cost_analysis.outsource_estimated_cost_analysis"
        )

        def get_all(doctype, **kwargs):
            if doctype == "Outsource Order":
                return [
                    {
                        "name": "WB-0001",
                        "order_no": "WB-0001",
                        "order_date": "2026-03-01",
                        "expected_delivery_date": "2026-03-05",
                        "order_status": "生产中",
                        "supplier": "SUP-001",
                        "style": "ST-001",
                        "style_name": "西装外套",
                        "ordered_qty": 100,
                        "received_qty": 40,
                        "unit_estimated_cost": 15,
                        "total_estimated_cost": 1500,
                    }
                ]
            return []

        self.env.get_all_handler = get_all
        columns, data, _, _, summary = module.execute({"include_closed_orders": 1})

        self.assertEqual(columns[0]["fieldname"], "outsource_order")
        self.assertEqual(data[0]["open_qty"], 60.0)
        self.assertEqual(data[0]["estimated_received_amount"], 600.0)
        self.assertEqual(summary[1]["value"], 1500.0)

    def test_material_procurement_cost_analysis_returns_open_amount(self):
        module = self.env.load_module(
            "fashion_erp.fashion_stock.report.material_procurement_cost_analysis.material_procurement_cost_analysis"
        )
        self.env.db.sql_result = [
            {
                "purchase_order": "PO-0001",
                "transaction_date": "2026-03-08",
                "status": "To Receive and Bill",
                "supplier": "SUP-001",
                "supply_order_type": "原辅料采购",
                "item_code": "FAB-001",
                "item_usage_type": "面料",
                "supply_context": "外包备货",
                "reference_style": "ST-001",
                "reference_outsource_order": "WB-0001",
                "qty": 100,
                "received_qty": 40,
                "outstanding_qty": 60,
                "rate": 8,
                "ordered_amount": 800,
                "received_amount": 320,
                "open_amount": 480,
                "warehouse": "MAT-01",
            }
        ]

        columns, data, _, _, summary = module.execute({"supply_context": "外包备货"})

        self.assertEqual(columns[0]["fieldname"], "purchase_order")
        self.assertEqual(data[0]["open_amount"], 480.0)
        self.assertEqual(summary[2]["value"], 800.0)
        self.assertEqual(summary[-1]["value"], 60.0)

    def test_fulfillment_cost_analysis_returns_cost_per_unit(self):
        module = self.env.load_module(
            "fashion_erp.fashion_stock.report.fulfillment_cost_analysis.fulfillment_cost_analysis"
        )
        self.env.db.sql_result = [
            {
                "delivery_note": "DN-0001",
                "posting_date": "2026-03-08",
                "customer": "CUST-001",
                "company": "COMP-01",
                "sales_order": "SO-0001",
                "delivered_qty": 4,
                "fulfillment_consumable_qty": 2,
                "fulfillment_consumable_amount": 10,
                "manual_logistics_fee": 18,
                "fulfillment_total_cost": 28,
                "fulfillment_consumable_stock_entry": "STE-001",
            }
        ]

        columns, data, _, _, summary = module.execute({"company": "COMP-01"})

        self.assertEqual(columns[0]["fieldname"], "delivery_note")
        self.assertEqual(data[0]["cost_per_unit"], 7.0)
        self.assertEqual(summary[4]["value"], 28.0)
        self.assertEqual(summary[5]["value"], 7.0)


if __name__ == "__main__":
    unittest.main()
