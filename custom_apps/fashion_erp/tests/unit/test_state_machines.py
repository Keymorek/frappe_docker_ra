from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from helpers import FakeDoc, build_frappe_env


class TestStateMachines(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_outsource_order_happy_path(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_service")
        doc = FakeDoc(
            name="WB-001",
            order_no="WB-001",
            order_status="草稿",
            ordered_qty=100,
            received_qty=0,
            total_estimated_cost=5000,
        )

        with patch.object(module, "_get_outsource_order_doc", return_value=doc), patch.object(
            module,
            "_ensure_submission_prerequisites",
            return_value=None,
        ):
            submit_result = module.submit_outsource_order("WB-001")
            start_result = module.start_outsource_order("WB-001")
            complete_result = module.complete_outsource_order("WB-001")
            with self.assertRaisesRegex(self.env.FrappeThrow, "已完成的外包单不允许取消"):
                module.cancel_outsource_order("WB-001")

        self.assertEqual(submit_result["order_status"], "已下单")
        self.assertEqual(start_result["order_status"], "生产中")
        self.assertEqual(complete_result["order_status"], "已完成")
        self.assertEqual([row.action_type for row in doc.logs], ["下单", "开工", "完成"])
        self.assertEqual(len(doc.save_calls), 3)

    def test_outsource_receipt_happy_path(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_receipt_service")
        doc = FakeDoc(
            name="DH-001",
            receipt_no="DH-001",
            receipt_status="草稿",
            outsource_order="WB-001",
            total_received_qty=10,
            warehouse="WH-QC",
            qc_stock_entry="",
            final_stock_entry="",
            qc_completed_at=None,
            items=[
                SimpleNamespace(
                    idx=1,
                    qty=10,
                    sellable_qty=10,
                    repair_qty=0,
                    defective_qty=0,
                    frozen_qty=0,
                )
            ],
        )

        with patch.object(module, "_get_outsource_receipt_doc", return_value=doc), patch.object(
            module,
            "_sync_outsource_order_received_qty",
            return_value=None,
        ), patch.object(module, "ensure_link_exists", return_value=None), patch.object(
            module,
            "now_datetime",
            return_value=datetime(2026, 3, 7, 13, 0, 0),
        ):
            confirm_result = module.confirm_outsource_receipt("DH-001")
            stock_result = module.mark_outsource_receipt_stocked("DH-001", stock_entry_ref="STE-QC-001")
            qc_result = module.complete_outsource_receipt_qc("DH-001", final_stock_entry_ref="STE-FINAL-001")
            with self.assertRaisesRegex(self.env.FrappeThrow, "已入库或已质检的到货单不允许取消"):
                module.cancel_outsource_receipt("DH-001")

        self.assertEqual(confirm_result["receipt_status"], "已收货")
        self.assertEqual(stock_result["receipt_status"], "已入库")
        self.assertEqual(qc_result["receipt_status"], "已质检")
        self.assertEqual(doc.qc_stock_entry, "STE-QC-001")
        self.assertEqual(doc.final_stock_entry, "STE-FINAL-001")
        self.assertEqual(str(doc.qc_completed_at), "2026-03-07 13:00:00")
        self.assertEqual(
            [row.action_type for row in doc.logs],
            ["收货确认", "确认已入库", "确认质检完成"],
        )

    def test_after_sales_refund_workflow_and_close_guards(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        refund_doc = FakeDoc(
            name="TK-001",
            ticket_no="TK-001",
            ticket_type="退货退款",
            ticket_status="新建",
            refund_status="待退款",
            refund_amount=0,
            replacement_sales_order="",
            return_disposition="",
            received_at=None,
            warehouse="",
            warehouse_location="",
            logistics_company="",
            tracking_no="",
            items=[SimpleNamespace(qty=1, received_qty=0)],
        )

        with patch.object(module, "_get_after_sales_ticket_doc", return_value=refund_doc):
            waiting_result = module.move_after_sales_ticket_to_waiting_return("TK-001")
            receive_result = module.receive_after_sales_ticket("TK-001", warehouse="WH-AFTER")
            inspect_result = module.start_after_sales_inspection("TK-001")
            decision_result = module.apply_after_sales_decision("TK-001", refund_amount=99)
            refund_result = module.approve_after_sales_refund("TK-001", refund_amount=99)
            with patch.object(
                module,
                "get_after_sales_inventory_closure_summary",
                return_value={
                    "inventory_closure_status": "已最终处理",
                    "pending_return_stock_entry": "STE-PENDING-001",
                    "final_disposition_stock_entry": "STE-FINAL-001",
                },
            ):
                close_result = module.close_after_sales_ticket("TK-001")

        self.assertEqual(waiting_result["ticket_status"], "待退回")
        self.assertEqual(receive_result["ticket_status"], "已收货")
        self.assertEqual(inspect_result["ticket_status"], "质检中")
        self.assertEqual(decision_result["ticket_status"], "待退款")
        self.assertEqual(refund_result["ticket_status"], "待处理")
        self.assertEqual(refund_result["refund_status"], "已退款")
        self.assertEqual(close_result["ticket_status"], "已关闭")
        self.assertEqual(
            [row.action_type for row in refund_doc.logs],
            ["状态变更", "收货", "质检", "状态变更", "退款", "关闭"],
        )

        replacement_doc = FakeDoc(
            name="TK-002",
            ticket_no="TK-002",
            ticket_type="补发",
            ticket_status="待补发",
            refund_status="无需退款",
            refund_amount=0,
            replacement_sales_order="",
            return_disposition="",
            received_at=None,
            warehouse="",
            warehouse_location="",
            logistics_company="",
            tracking_no="",
            items=[SimpleNamespace(qty=1, received_qty=0)],
        )

        with patch.object(module, "_get_after_sales_ticket_doc", return_value=replacement_doc):
            with self.assertRaisesRegex(self.env.FrappeThrow, "必须先生成补发销售订单"):
                module.close_after_sales_ticket("TK-002")


if __name__ == "__main__":
    unittest.main()
