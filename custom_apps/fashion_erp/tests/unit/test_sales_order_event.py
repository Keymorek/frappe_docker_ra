from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from helpers import FakeDoc, build_frappe_env


class TestSalesOrderEvent(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_validate_sales_order_channel_context_syncs_channel_from_store(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.exists_map[("Channel Store", "STORE-01")] = True
        self.env.db.value_map[("Channel Store", "STORE-01", "channel")] = "抖音"
        self.env.get_all_handler = lambda *args, **kwargs: []
        doc = FakeDoc(
            name="SO-001",
            channel_store="STORE-01",
            channel="",
            external_order_id="EXT-001",
            after_sales_ticket="",
            items=[],
        )

        module.validate_sales_order_channel_context(doc)

        self.assertEqual(doc.channel, "抖音")
        self.assertEqual(doc.external_order_id, "EXT-001")
        self.assertEqual(doc.fulfillment_status, "待配货")

    def test_validate_sales_order_channel_context_rejects_duplicate_external_order(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.exists_map[("Channel Store", "STORE-01")] = True
        self.env.db.value_map[("Channel Store", "STORE-01", "channel")] = "抖音"
        self.env.get_all_handler = lambda doctype, **kwargs: (
            [{"name": "SO-EXISTS-001", "after_sales_ticket": ""}] if doctype == "Sales Order" else []
        )
        doc = FakeDoc(
            name="SO-001",
            channel_store="STORE-01",
            channel="抖音",
            external_order_id="EXT-001",
            after_sales_ticket="",
            items=[],
        )

        with self.assertRaisesRegex(self.env.FrappeThrow, "已存在于销售订单"):
            module.validate_sales_order_channel_context(doc)

    def test_validate_sales_order_channel_context_allows_after_sales_replacement(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.exists_map[("Channel Store", "STORE-01")] = True
        self.env.db.value_map[("Channel Store", "STORE-01", "channel")] = "抖音"
        self.env.get_all_handler = lambda doctype, **kwargs: (
            [{"name": "SO-EXISTS-001", "after_sales_ticket": ""}] if doctype == "Sales Order" else []
        )
        doc = FakeDoc(
            name="SO-REPLACE-001",
            channel_store="STORE-01",
            channel="抖音",
            external_order_id="EXT-001",
            after_sales_ticket="TK-001",
            items=[],
        )

        module.validate_sales_order_channel_context(doc)

        self.assertEqual(doc.channel, "抖音")

    def test_validate_sales_order_channel_context_requires_store_when_external_id_present(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.get_all_handler = lambda *args, **kwargs: []
        doc = FakeDoc(
            name="SO-001",
            channel_store="",
            channel="",
            external_order_id="EXT-001",
            after_sales_ticket="",
            items=[],
        )

        with self.assertRaisesRegex(self.env.FrappeThrow, "必须先填写渠道店铺"):
            module.validate_sales_order_channel_context(doc)

    def test_validate_sales_order_channel_context_initializes_item_fulfillment_status(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.exists_map[("Channel Store", "STORE-01")] = True
        self.env.db.value_map[("Channel Store", "STORE-01", "channel")] = "抖音"
        self.env.get_all_handler = lambda *args, **kwargs: []
        doc = FakeDoc(
            name="SO-INIT-001",
            channel_store="STORE-01",
            channel="",
            external_order_id="EXT-INIT-001",
            after_sales_ticket="",
            items=[
                SimpleNamespace(qty=2, delivered_qty=0, fulfillment_status=""),
                SimpleNamespace(qty=1, delivered_qty=0, fulfillment_status=""),
            ],
        )

        module.validate_sales_order_channel_context(doc)

        self.assertEqual(doc.fulfillment_status, "待配货")
        self.assertEqual(doc.items[0].fulfillment_status, "待处理")
        self.assertEqual(doc.items[1].fulfillment_status, "待处理")

    def test_validate_sales_order_channel_context_aggregates_manual_progress(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.exists_map[("Channel Store", "STORE-01")] = True
        self.env.db.value_map[("Channel Store", "STORE-01", "channel")] = "抖音"
        self.env.get_all_handler = lambda *args, **kwargs: []
        doc = FakeDoc(
            name="SO-PROGRESS-001",
            channel_store="STORE-01",
            channel="",
            external_order_id="EXT-PROGRESS-001",
            after_sales_ticket="",
            items=[
                SimpleNamespace(qty=2, delivered_qty=0, fulfillment_status="已拣货"),
                SimpleNamespace(qty=1, delivered_qty=0, fulfillment_status="待发货"),
            ],
        )

        module.validate_sales_order_channel_context(doc)

        self.assertEqual(doc.fulfillment_status, "履约中")
        self.assertEqual(doc.items[0].fulfillment_status, "已拣货")
        self.assertEqual(doc.items[1].fulfillment_status, "待发货")

    def test_validate_sales_order_channel_context_marks_partial_shipment(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.exists_map[("Channel Store", "STORE-01")] = True
        self.env.db.value_map[("Channel Store", "STORE-01", "channel")] = "抖音"
        self.env.get_all_handler = lambda *args, **kwargs: []
        doc = FakeDoc(
            name="SO-SHIP-001",
            channel_store="STORE-01",
            channel="",
            external_order_id="EXT-SHIP-001",
            after_sales_ticket="",
            items=[
                SimpleNamespace(qty=2, delivered_qty=1, fulfillment_status="待处理"),
                SimpleNamespace(qty=1, delivered_qty=1, fulfillment_status=""),
            ],
        )

        module.validate_sales_order_channel_context(doc)

        self.assertEqual(doc.fulfillment_status, "部分发货")
        self.assertEqual(doc.items[0].fulfillment_status, "部分发货")
        self.assertEqual(doc.items[1].fulfillment_status, "已发货")

    def test_validate_sales_order_channel_context_marks_after_sales_items_in_progress(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.exists_map[("Channel Store", "STORE-01")] = True
        self.env.db.value_map[("Channel Store", "STORE-01", "channel")] = "抖音"

        def get_all(doctype, **kwargs):
            if doctype == "Sales Order":
                return []
            if doctype == "After Sales Ticket":
                return [{"name": "TK-001", "ticket_status": "待退款"}]
            if doctype == "After Sales Item":
                return [{"parent": "TK-001", "sales_order_item_ref": "SOI-001"}]
            return []

        self.env.get_all_handler = get_all
        doc = FakeDoc(
            name="SO-AFTER-001",
            channel_store="STORE-01",
            channel="",
            external_order_id="EXT-AFTER-001",
            after_sales_ticket="",
            items=[
                SimpleNamespace(name="SOI-001", qty=1, delivered_qty=1, fulfillment_status="已发货"),
                SimpleNamespace(name="SOI-002", qty=1, delivered_qty=1, fulfillment_status="已发货"),
            ],
        )

        module.validate_sales_order_channel_context(doc)

        self.assertEqual(doc.fulfillment_status, "售后中")
        self.assertEqual(doc.items[0].fulfillment_status, "售后中")
        self.assertEqual(doc.items[1].fulfillment_status, "已发货")

    def test_validate_sales_order_channel_context_marks_after_sales_items_closed(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.exists_map[("Channel Store", "STORE-01")] = True
        self.env.db.value_map[("Channel Store", "STORE-01", "channel")] = "抖音"

        def get_all(doctype, **kwargs):
            if doctype == "Sales Order":
                return []
            if doctype == "After Sales Ticket":
                return [{"name": "TK-002", "ticket_status": "已关闭"}]
            if doctype == "After Sales Item":
                return [{"parent": "TK-002", "sales_order_item_ref": "SOI-003"}]
            return []

        self.env.get_all_handler = get_all
        doc = FakeDoc(
            name="SO-AFTER-002",
            channel_store="STORE-01",
            channel="",
            external_order_id="EXT-AFTER-002",
            after_sales_ticket="",
            items=[SimpleNamespace(name="SOI-003", qty=1, delivered_qty=1, fulfillment_status="已发货")],
        )

        module.validate_sales_order_channel_context(doc)

        self.assertEqual(doc.fulfillment_status, "已关闭")
        self.assertEqual(doc.items[0].fulfillment_status, "已关闭")

    def test_validate_sales_order_channel_context_marks_completed_and_cancelled(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.exists_map[("Channel Store", "STORE-01")] = True
        self.env.db.value_map[("Channel Store", "STORE-01", "channel")] = "抖音"
        self.env.get_all_handler = lambda *args, **kwargs: []
        completed_doc = FakeDoc(
            name="SO-DONE-001",
            status="Completed",
            channel_store="STORE-01",
            channel="",
            external_order_id="EXT-DONE-001",
            after_sales_ticket="",
            items=[
                SimpleNamespace(qty=1, delivered_qty=1, fulfillment_status="已签收"),
                SimpleNamespace(qty=1, delivered_qty=1, fulfillment_status="已关闭"),
            ],
        )

        module.validate_sales_order_channel_context(completed_doc)

        self.assertEqual(completed_doc.fulfillment_status, "已完成")

        cancelled_doc = FakeDoc(
            name="SO-CANCEL-001",
            docstatus=2,
            channel_store="STORE-01",
            channel="",
            external_order_id="EXT-CANCEL-001",
            after_sales_ticket="",
            items=[SimpleNamespace(qty=1, delivered_qty=0, fulfillment_status="待处理")],
        )

        module.validate_sales_order_channel_context(cancelled_doc)

        self.assertEqual(cancelled_doc.fulfillment_status, "已取消")
        self.assertEqual(cancelled_doc.items[0].fulfillment_status, "已取消")

    def test_sync_after_sales_replacement_order_backfills_ticket(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.value_map[
            (
                "After Sales Ticket",
                "TK-001",
                ("replacement_sales_order", "replacement_fulfillment_status", "ticket_status", "ticket_type"),
                True,
            )
        ] = {
            "replacement_sales_order": "",
            "replacement_fulfillment_status": "",
            "ticket_status": "待补发",
            "ticket_type": "补发",
        }
        doc = FakeDoc(
            name="SO-001",
            after_sales_ticket="TK-001",
            fulfillment_status="待配货",
            docstatus=0,
            status="Draft",
        )

        with patch.object(module, "sync_after_sales_ticket_replacement_order") as mocked_sync:
            module.sync_after_sales_replacement_order(doc)

        self.assertEqual(
            self.env.db.set_value_calls,
            [
                ("After Sales Ticket", "TK-001", "replacement_sales_order", "SO-001", {"update_modified": False}),
                ("After Sales Ticket", "TK-001", "replacement_fulfillment_status", "待配货", {"update_modified": False}),
            ],
        )
        mocked_sync.assert_not_called()

    def test_sync_after_sales_replacement_order_skips_get_doc_when_ticket_already_linked(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.value_map[
            (
                "After Sales Ticket",
                "TK-002",
                ("replacement_sales_order", "replacement_fulfillment_status", "ticket_status", "ticket_type"),
                True,
            )
        ] = {
            "replacement_sales_order": "SO-002",
            "replacement_fulfillment_status": "待配货",
            "ticket_status": "待补发",
            "ticket_type": "补发",
        }

        def fail_exists(doctype, name):
            if (doctype, name) == ("After Sales Ticket", "TK-002"):
                self.fail("expected direct lightweight lookup without exists")
            return False

        def fail_get_doc(doctype, name=None):
            if (doctype, name) == ("After Sales Ticket", "TK-002"):
                self.fail("expected no full ticket load when replacement order already matches")
            return None

        self.env.db.exists = fail_exists
        self.env.get_doc_handler = fail_get_doc
        doc = FakeDoc(
            name="SO-002",
            after_sales_ticket="TK-002",
            fulfillment_status="待配货",
            docstatus=0,
            status="Draft",
        )

        with patch.object(module, "sync_after_sales_ticket_replacement_order") as mocked_sync:
            module.sync_after_sales_replacement_order(doc)

        mocked_sync.assert_not_called()
        self.assertEqual(self.env.db.set_value_calls, [])

    def test_sync_after_sales_replacement_order_uses_full_sync_when_replacement_is_completed(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.value_map[
            (
                "After Sales Ticket",
                "TK-003",
                ("replacement_sales_order", "replacement_fulfillment_status", "ticket_status", "ticket_type"),
                True,
            )
        ] = {
            "replacement_sales_order": "SO-003",
            "replacement_fulfillment_status": "待发货",
            "ticket_status": "待补发",
            "ticket_type": "补发",
        }
        doc = FakeDoc(
            name="SO-003",
            after_sales_ticket="TK-003",
            fulfillment_status="已发货",
            docstatus=0,
            status="Draft",
        )

        with patch.object(module, "sync_after_sales_ticket_replacement_order") as mocked_sync:
            module.sync_after_sales_replacement_order(doc)

        mocked_sync.assert_called_once_with(
            "TK-003",
            sales_order_name="SO-003",
            sales_order_doc=doc,
            operation="update",
        )

    def test_sync_after_sales_replacement_order_uses_full_sync_when_replacement_is_canceled(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.value_map[
            (
                "After Sales Ticket",
                "TK-004",
                ("replacement_sales_order", "replacement_fulfillment_status", "ticket_status", "ticket_type"),
                True,
            )
        ] = {
            "replacement_sales_order": "SO-004",
            "replacement_fulfillment_status": "待发货",
            "ticket_status": "待补发",
            "ticket_type": "补发",
        }
        doc = FakeDoc(
            name="SO-004",
            after_sales_ticket="TK-004",
            fulfillment_status="待发货",
            docstatus=2,
            status="Cancelled",
        )

        with patch.object(module, "sync_after_sales_ticket_replacement_order") as mocked_sync:
            module.sync_after_sales_replacement_order(doc, method="on_cancel")

        mocked_sync.assert_called_once_with(
            "TK-004",
            sales_order_name="SO-004",
            sales_order_doc=doc,
            operation="cancel",
        )

    def test_sync_linked_sales_orders_fulfillment_status_updates_linked_orders(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.sales_order")
        self.env.db.exists_map[("Sales Order", "SO-001")] = True
        sales_order = FakeDoc(
            name="SO-001",
            docstatus=1,
            status="To Deliver and Bill",
            fulfillment_status="待配货",
            items=[SimpleNamespace(qty=2, delivered_qty=2, fulfillment_status="待处理")],
        )
        self.env.get_doc_handler = lambda doctype, name=None: sales_order if (doctype, name) == ("Sales Order", "SO-001") else None
        delivery_note = FakeDoc(
            items=[
                SimpleNamespace(against_sales_order="SO-001"),
                SimpleNamespace(sales_order="SO-001"),
            ]
        )

        module.sync_linked_sales_orders_fulfillment_status(delivery_note)

        self.assertEqual(sales_order.fulfillment_status, "已发货")
        self.assertEqual(sales_order.items[0].fulfillment_status, "已发货")
        self.assertEqual(sales_order.save_calls, [{"ignore_permissions": True, "ignore_version": True}])


if __name__ == "__main__":
    unittest.main()
