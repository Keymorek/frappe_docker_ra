from __future__ import annotations

import unittest
from collections import Counter
from types import SimpleNamespace

from helpers import FakeDoc, build_frappe_env


class TestSalesOrderFulfillmentService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()
        self.env.db.exists_map.update(
            {
                ("Company", "COMP-01"): True,
                ("Customer", "CUST-01"): True,
                ("Warehouse", "WH-01"): True,
            }
        )

    def tearDown(self):
        self.env.cleanup()

    def test_allocate_pick_and_pack_sales_order(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.sales_order_fulfillment_service")
        sales_order = FakeDoc(
            doctype="Sales Order",
            name="SO-001",
            company="COMP-01",
            customer="CUST-01",
            set_warehouse="WH-01",
            fulfillment_status="待配货",
            items=[
                SimpleNamespace(
                    name="SOI-001",
                    item_code="SKU-001",
                    qty=2,
                    delivered_qty=0,
                    warehouse="WH-01",
                    fulfillment_status="待处理",
                )
            ],
        )
        self.env.get_doc_handler = lambda doctype, name=None: sales_order if (doctype, name) == ("Sales Order", "SO-001") else None

        allocate_result = module.allocate_sales_order("SO-001")
        self.assertEqual(allocate_result["action"], "配货")
        self.assertEqual(sales_order.fulfillment_status, "履约中")
        self.assertEqual(sales_order.items[0].fulfillment_status, "已锁库存")

        pick_result = module.pick_sales_order("SO-001")
        self.assertEqual(pick_result["action"], "拣货")
        self.assertEqual(sales_order.items[0].fulfillment_status, "已拣货")

        pack_result = module.pack_sales_order("SO-001")
        self.assertEqual(pack_result["action"], "打包")
        self.assertEqual(sales_order.fulfillment_status, "待发货")
        self.assertEqual(sales_order.items[0].fulfillment_status, "待发货")
        self.assertEqual(
            sales_order.save_calls,
            [
                {"ignore_permissions": True},
                {"ignore_permissions": True},
                {"ignore_permissions": True},
            ],
        )

    def test_allocate_sales_order_supports_selected_rows(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.sales_order_fulfillment_service")
        sales_order = FakeDoc(
            doctype="Sales Order",
            name="SO-002",
            company="COMP-01",
            customer="CUST-01",
            set_warehouse="WH-01",
            fulfillment_status="待配货",
            items=[
                SimpleNamespace(
                    name="SOI-001",
                    item_code="SKU-001",
                    qty=1,
                    delivered_qty=0,
                    warehouse="WH-01",
                    fulfillment_status="待处理",
                ),
                SimpleNamespace(
                    name="SOI-002",
                    item_code="SKU-002",
                    qty=1,
                    delivered_qty=0,
                    warehouse="WH-01",
                    fulfillment_status="待处理",
                ),
            ],
        )
        self.env.get_doc_handler = lambda doctype, name=None: sales_order if (doctype, name) == ("Sales Order", "SO-002") else None

        result = module.allocate_sales_order("SO-002", item_names='["SOI-002"]')

        self.assertEqual(result["affected_rows"], 1)
        self.assertEqual(sales_order.items[0].fulfillment_status, "待处理")
        self.assertEqual(sales_order.items[1].fulfillment_status, "已锁库存")

    def test_prepare_sales_order_delivery_note_creates_draft(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.sales_order_fulfillment_service")
        self.env.meta_fields["Delivery Note"] = {
            "customer",
            "company",
            "posting_date",
            "posting_time",
            "set_warehouse",
            "remarks",
            "items",
        }
        self.env.meta_fields["Delivery Note Item"] = {
            "against_sales_order",
            "so_detail",
            "item_code",
            "qty",
            "rate",
            "warehouse",
            "description",
            "uom",
        }
        sales_order = FakeDoc(
            doctype="Sales Order",
            name="SO-003",
            company="COMP-01",
            customer="CUST-01",
            set_warehouse="WH-01",
            fulfillment_status="部分发货",
            items=[
                SimpleNamespace(
                    name="SOI-001",
                    item_code="SKU-001",
                    qty=2,
                    delivered_qty=0,
                    rate=99,
                    warehouse="WH-01",
                    description="SKU-001",
                    uom="Nos",
                    fulfillment_status="待发货",
                ),
                SimpleNamespace(
                    name="SOI-002",
                    item_code="SKU-002",
                    qty=3,
                    delivered_qty=1,
                    rate=59,
                    warehouse="WH-01",
                    description="SKU-002",
                    uom="Nos",
                    fulfillment_status="部分发货",
                ),
                SimpleNamespace(
                    name="SOI-003",
                    item_code="SKU-003",
                    qty=1,
                    delivered_qty=0,
                    rate=39,
                    warehouse="WH-01",
                    description="SKU-003",
                    uom="Nos",
                    fulfillment_status="已拣货",
                ),
            ],
        )
        created_docs = []

        def get_doc(arg1, arg2=None):
            if isinstance(arg1, dict):
                payload = dict(arg1)
                payload.pop("doctype", None)
                items = [FakeDoc(**item) for item in payload.pop("items", [])]
                doc = FakeDoc(doctype="Delivery Note", name="DN-0001", items=items, **payload)

                def insert(ignore_permissions=False, *, _doc=doc):
                    created_docs.append(_doc)
                    _doc.insert_calls.append({"ignore_permissions": ignore_permissions})
                    return _doc

                doc.insert = insert
                return doc

            if (arg1, arg2) == ("Sales Order", "SO-003"):
                return sales_order
            raise KeyError((arg1, arg2))

        self.env.get_doc_handler = get_doc

        result = module.prepare_sales_order_delivery_note("SO-003")

        self.assertEqual(result["delivery_note"], "DN-0001")
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(len(created_docs), 1)
        self.assertEqual(created_docs[0].insert_calls, [{"ignore_permissions": True}])
        self.assertEqual(created_docs[0].items[0].qty, 2)
        self.assertEqual(created_docs[0].items[1].qty, 2)
        self.assertEqual(created_docs[0].items[0].against_sales_order, "SO-003")
        self.assertEqual(created_docs[0].items[0].so_detail, "SOI-001")
        self.assertEqual(created_docs[0].items[1].so_detail, "SOI-002")

    def test_prepare_sales_order_delivery_note_requires_pending_rows(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.sales_order_fulfillment_service")
        sales_order = FakeDoc(
            doctype="Sales Order",
            name="SO-004",
            company="COMP-01",
            customer="CUST-01",
            set_warehouse="WH-01",
            fulfillment_status="履约中",
            items=[
                SimpleNamespace(
                    name="SOI-001",
                    item_code="SKU-001",
                    qty=1,
                    delivered_qty=0,
                    warehouse="WH-01",
                    fulfillment_status="已拣货",
                )
            ],
        )
        self.env.get_doc_handler = lambda doctype, name=None: sales_order if (doctype, name) == ("Sales Order", "SO-004") else None

        with self.assertRaisesRegex(self.env.FrappeThrow, "没有待发货明细"):
            module.prepare_sales_order_delivery_note("SO-004")

    def test_sync_sales_order_fulfillment_status_batches_after_sales_ticket_item_queries(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.sales_order_fulfillment_service")
        get_all_counter = Counter()

        def get_all(doctype, **kwargs):
            get_all_counter[doctype] += 1
            if doctype == "After Sales Ticket":
                return [
                    {"name": "TK-001", "ticket_status": "待退款"},
                    {"name": "TK-002", "ticket_status": "已关闭"},
                ]
            if doctype == "After Sales Item":
                return [
                    {"parent": "TK-001", "sales_order_item_ref": "SOI-001"},
                    {"parent": "TK-002", "sales_order_item_ref": "SOI-002"},
                ]
            return []

        self.env.get_all_handler = get_all

        def get_doc(doctype, name=None):
            if doctype == "After Sales Ticket":
                raise AssertionError("should not load after sales tickets one by one")
            raise KeyError((doctype, name))

        self.env.get_doc_handler = get_doc
        sales_order = FakeDoc(
            doctype="Sales Order",
            name="SO-005",
            status="To Deliver and Bill",
            fulfillment_status="部分发货",
            items=[
                SimpleNamespace(name="SOI-001", qty=1, delivered_qty=1, fulfillment_status="已发货"),
                SimpleNamespace(name="SOI-002", qty=1, delivered_qty=1, fulfillment_status="已发货"),
                SimpleNamespace(name="SOI-003", qty=1, delivered_qty=1, fulfillment_status="已发货"),
            ],
        )

        changed = module.sync_sales_order_fulfillment_status(sales_order)

        self.assertTrue(changed)
        self.assertEqual(sales_order.fulfillment_status, "售后中")
        self.assertEqual(sales_order.items[0].fulfillment_status, "售后中")
        self.assertEqual(sales_order.items[1].fulfillment_status, "已关闭")
        self.assertEqual(sales_order.items[2].fulfillment_status, "已发货")
        self.assertEqual(get_all_counter["After Sales Ticket"], 1)
        self.assertEqual(get_all_counter["After Sales Item"], 1)


if __name__ == "__main__":
    unittest.main()
