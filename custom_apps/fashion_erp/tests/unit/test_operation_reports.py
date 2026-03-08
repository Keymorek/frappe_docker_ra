from __future__ import annotations

import unittest
from unittest.mock import patch

from helpers import build_frappe_env


class TestOperationReports(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_style_inventory_overview_returns_rows_and_summary(self):
        module = self.env.load_module(
            "fashion_erp.fashion_stock.report.style_inventory_overview.style_inventory_overview"
        )
        self.env.db.sql_result = [
            {
                "style": "ST-001",
                "style_name": "西装外套",
                "item_code": "SKU-001",
                "item_name": "西装外套-黑-M",
                "color_code": "BLK",
                "size_code": "M",
                "warehouse": "FG-01",
                "actual_qty": 8,
                "reserved_qty": 2,
                "projected_qty": 6,
                "safe_stock": 10,
                "sellable": 1,
                "sku_status": "在售",
            }
        ]

        columns, data, _, _, summary = module.execute(
            {"style": "ST-001", "warehouse": "FG-01"}
        )

        self.assertEqual(columns[0]["fieldname"], "style")
        self.assertEqual(data[0]["item_code"], "SKU-001")
        self.assertEqual(summary[0]["value"], 1)
        self.assertEqual(summary[-1]["value"], 1)
        self.assertTrue(self.env.db.sql_calls)

    def test_material_supply_overview_flattens_order_supply_rows(self):
        module = self.env.load_module(
            "fashion_erp.fashion_stock.report.material_supply_overview.material_supply_overview"
        )

        def get_all(doctype, **kwargs):
            if doctype == "Outsource Order":
                return [
                    {
                        "name": "WB-0001",
                        "order_no": "WB-0001",
                        "order_status": "已下单",
                        "order_date": "2026-03-08",
                        "expected_delivery_date": "2026-03-12",
                        "supplier": "SUP-001",
                        "style": "ST-001",
                        "style_name": "西装外套",
                    }
                ]
            return []

        self.env.get_all_handler = get_all

        with patch(
            "fashion_erp.fashion_stock.report.material_supply_overview.material_supply_overview.get_outsource_supply_summary"
        ) as mocked_summary:
            mocked_summary.return_value = {
                "rows": [
                    {
                        "item_code": "FAB-001",
                        "item_name": "面料A",
                        "required_qty": 10,
                        "prepared_qty": 2,
                        "issued_qty": 1,
                        "on_hand_qty": 3,
                        "on_order_qty": 1,
                        "to_prepare_qty": 8,
                        "to_issue_qty": 1,
                        "to_purchase_qty": 4,
                        "status": "需采购",
                        "warehouse_scope": "MAT-01",
                        "locations": "A-01",
                    }
                ]
            }
            columns, data, _, _, summary = module.execute({"style": "ST-001"})

        self.assertEqual(columns[0]["fieldname"], "outsource_order")
        self.assertEqual(data[0]["supplier"], "SUP-001")
        self.assertEqual(data[0]["to_purchase_qty"], 4.0)
        self.assertEqual(summary[-1]["value"], 1)

    def test_outsource_receipt_overview_aggregates_header_rows(self):
        module = self.env.load_module(
            "fashion_erp.fashion_stock.report.outsource_receipt_overview.outsource_receipt_overview"
        )

        def get_all(doctype, **kwargs):
            if doctype == "Outsource Receipt":
                return [
                    {
                        "name": "DH-0001",
                        "receipt_no": "DH-0001",
                        "receipt_date": "2026-03-08",
                        "receipt_status": "已入库",
                        "outsource_order": "WB-0001",
                        "supplier": "SUP-001",
                        "company": "COMP-01",
                        "style": "ST-001",
                        "style_name": "西装外套",
                        "warehouse": "FG-01",
                        "total_received_qty": 20,
                        "exception_row_count": 1,
                        "total_shortage_qty": 2,
                        "total_wrong_color_qty": 1,
                        "total_wrong_size_qty": 0,
                        "total_defective_qty": 1,
                        "qc_stock_entry": "STE-001",
                        "final_stock_entry": "STE-002",
                        "qc_completed_at": "2026-03-09 10:00:00",
                        "exception_summary": "1 行异常",
                    }
                ]
            return []

        self.env.get_all_handler = get_all
        columns, data, _, _, summary = module.execute({"supplier": "SUP-001"})

        self.assertEqual(columns[0]["fieldname"], "name")
        self.assertEqual(data[0]["total_received_qty"], 20.0)
        self.assertEqual(summary[0]["value"], 1)
        self.assertEqual(summary[2]["value"], 20.0)

    def test_sales_fulfillment_overview_returns_sql_rows(self):
        module = self.env.load_module(
            "fashion_erp.fashion_stock.report.sales_fulfillment_overview.sales_fulfillment_overview"
        )
        self.env.db.sql_result = [
            {
                "sales_order": "SO-0001",
                "transaction_date": "2026-03-08",
                "delivery_date": "2026-03-10",
                "customer": "CUST-001",
                "channel": "抖音",
                "channel_store": "STORE-01",
                "external_order_id": "EXT-001",
                "fulfillment_status": "待发货",
                "after_sales_ticket": "",
                "grand_total": 299,
                "line_count": 2,
                "total_qty": 3,
                "delivered_qty": 1,
                "pending_qty": 2,
                "ready_to_ship_lines": 1,
            }
        ]

        columns, data, _, _, summary = module.execute(
            {"channel_store": "STORE-01", "fulfillment_status": "待发货"}
        )

        self.assertEqual(columns[0]["fieldname"], "sales_order")
        self.assertEqual(data[0]["pending_qty"], 2.0)
        self.assertEqual(summary[0]["value"], 1)
        self.assertEqual(summary[-1]["value"], 1)
        self.assertTrue(self.env.db.sql_calls)

    def test_after_sales_overview_returns_sql_rows(self):
        module = self.env.load_module(
            "fashion_erp.fashion_stock.report.after_sales_overview.after_sales_overview"
        )
        self.env.db.sql_result = [
            {
                "after_sales_ticket": "TK-0001",
                "ticket_no": "TK-0001",
                "apply_time": "2026-03-08 09:00:00",
                "ticket_type": "退货退款",
                "ticket_status": "待退款",
                "priority": "普通",
                "channel": "抖音",
                "channel_store": "STORE-01",
                "external_order_id": "EXT-001",
                "sales_order": "SO-0001",
                "customer": "CUST-001",
                "return_reason": "R01",
                "return_disposition": "A1",
                "refund_status": "待退款",
                "refund_amount": 199,
                "replacement_sales_order": "",
                "handler_user": "ops@example.com",
                "line_count": 1,
                "requested_qty": 1,
                "received_qty": 1,
                "restock_qty": 1,
                "defective_qty": 0,
            }
        ]

        columns, data, _, _, summary = module.execute({"ticket_status": "待退款"})

        self.assertEqual(columns[0]["fieldname"], "after_sales_ticket")
        self.assertEqual(data[0]["refund_amount"], 199.0)
        self.assertEqual(summary[0]["value"], 1)
        self.assertEqual(summary[-1]["value"], 1)


if __name__ == "__main__":
    unittest.main()

