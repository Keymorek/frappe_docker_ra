from __future__ import annotations

import unittest
from collections import Counter
from types import SimpleNamespace

from helpers import FakeDoc, build_frappe_env


class TestAfterSalesTicketEvent(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_sync_linked_sales_orders_after_sales_status_updates_original_order(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.after_sales_ticket")

        original_order = FakeDoc(
            name="SO-001",
            docstatus=1,
            status="To Deliver and Bill",
            fulfillment_status="已发货",
            items=[SimpleNamespace(name="SOI-001", qty=1, delivered_qty=1, fulfillment_status="已发货")],
        )
        replacement_order = FakeDoc(
            name="SO-REPL-001",
            docstatus=0,
            status="Draft",
            fulfillment_status="待配货",
            items=[SimpleNamespace(name="SOI-REPL-001", qty=1, delivered_qty=0, fulfillment_status="待处理")],
        )
        ticket = FakeDoc(
            name="TK-001",
            sales_order="",
            replacement_sales_order="SO-REPL-001",
            items=[SimpleNamespace(sales_order_item_ref="SOI-001")],
        )

        def get_all(doctype, **kwargs):
            if doctype == "Sales Order Item":
                return [{"name": "SOI-001", "parent": "SO-001"}]
            if doctype == "Sales Order":
                self.assertEqual(
                    kwargs.get("filters"),
                    {"name": ["in", ["SO-001", "SO-REPL-001"]]},
                )
                return [{"name": "SO-001"}, {"name": "SO-REPL-001"}]
            if doctype == "After Sales Item":
                return [{"parent": "TK-001", "sales_order_item_ref": "SOI-001"}]
            if doctype != "After Sales Ticket":
                return []

            filters = kwargs.get("filters") or []
            for row in filters:
                if row == ["After Sales Ticket", "sales_order", "=", "SO-001"]:
                    return [{"name": "TK-001", "ticket_status": "待补发"}]
            return []

        def get_doc(doctype, name=None):
            if (doctype, name) == ("Sales Order", "SO-001"):
                return original_order
            if (doctype, name) == ("Sales Order", "SO-REPL-001"):
                return replacement_order
            raise KeyError((doctype, name))

        self.env.get_all_handler = get_all
        self.env.get_doc_handler = get_doc

        module.sync_linked_sales_orders_after_sales_status(ticket)

        self.assertEqual(original_order.fulfillment_status, "售后中")
        self.assertEqual(original_order.items[0].fulfillment_status, "售后中")
        self.assertEqual(
            original_order.save_calls,
            [{"ignore_permissions": True, "ignore_version": True}],
        )
        self.assertEqual(replacement_order.fulfillment_status, "待配货")
        self.assertEqual(replacement_order.save_calls, [])

    def test_collect_related_sales_orders_batches_sales_order_item_parent_queries(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.after_sales_ticket")
        ticket = FakeDoc(
            name="TK-002",
            sales_order="SO-DIRECT-001",
            replacement_sales_order="SO-REPL-002",
            items=[
                SimpleNamespace(sales_order_item_ref="SOI-001"),
                SimpleNamespace(sales_order_item_ref="SOI-002"),
                SimpleNamespace(sales_order_item_ref="SOI-001"),
                SimpleNamespace(sales_order_item_ref=""),
            ],
        )
        get_all_counter = Counter()
        original_get_value = self.env.db.get_value

        def counting_get_all(doctype, **kwargs):
            get_all_counter[doctype] += 1
            if doctype == "Sales Order Item":
                self.assertEqual(
                    kwargs.get("filters"),
                    {"name": ["in", ["SOI-001", "SOI-002"]]},
                )
                return [
                    {"name": "SOI-001", "parent": "SO-001"},
                    {"name": "SOI-002", "parent": "SO-002"},
                ]
            return []

        def fail_get_value(doctype, name, fieldname, as_dict=False):
            if (doctype, fieldname) == ("Sales Order Item", "parent"):
                self.fail("expected batched Sales Order Item parent lookup")
            return original_get_value(doctype, name, fieldname, as_dict=as_dict)

        self.env.get_all_handler = counting_get_all
        self.env.db.get_value = fail_get_value

        result = module._collect_related_sales_orders(ticket)

        self.assertEqual(result, ["SO-001", "SO-002", "SO-DIRECT-001", "SO-REPL-002"])
        self.assertEqual(get_all_counter["Sales Order Item"], 1)

    def test_sync_linked_sales_orders_after_sales_status_batches_sales_order_existence_queries(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.after_sales_ticket")
        get_all_counter = Counter()
        original_order = FakeDoc(
            name="SO-001",
            docstatus=1,
            status="To Deliver and Bill",
            fulfillment_status="已发货",
            items=[SimpleNamespace(name="SOI-001", qty=1, delivered_qty=1, fulfillment_status="已发货")],
        )
        ticket = FakeDoc(
            name="TK-003",
            sales_order="SO-001",
            replacement_sales_order="SO-MISSING",
            items=[SimpleNamespace(sales_order_item_ref="SOI-001")],
        )

        def counting_get_all(doctype, **kwargs):
            get_all_counter[doctype] += 1
            if doctype == "Sales Order Item":
                return [{"name": "SOI-001", "parent": "SO-001"}]
            if doctype == "Sales Order":
                self.assertEqual(
                    kwargs.get("filters"),
                    {"name": ["in", ["SO-001", "SO-MISSING"]]},
                )
                return [{"name": "SO-001"}]
            if doctype == "After Sales Ticket":
                return [{"name": "TK-003", "ticket_status": "待补发"}]
            if doctype == "After Sales Item":
                return [{"parent": "TK-003", "sales_order_item_ref": "SOI-001"}]
            return []

        def fail_exists(doctype, name):
            if doctype == "Sales Order":
                self.fail("expected batched Sales Order existence lookup")
            return False

        def get_doc(doctype, name=None):
            if (doctype, name) == ("Sales Order", "SO-001"):
                return original_order
            raise KeyError((doctype, name))

        self.env.get_all_handler = counting_get_all
        self.env.db.exists = fail_exists
        self.env.get_doc_handler = get_doc

        module.sync_linked_sales_orders_after_sales_status(ticket)

        self.assertEqual(get_all_counter["Sales Order"], 1)
        self.assertEqual(original_order.save_calls, [{"ignore_permissions": True, "ignore_version": True}])


if __name__ == "__main__":
    unittest.main()
