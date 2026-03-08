from __future__ import annotations

import unittest
from types import SimpleNamespace
from collections import Counter
from unittest.mock import patch

from helpers import FakeDoc, build_frappe_env


class TestAfterSalesService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_determine_after_sales_decision_status_maps_ticket_types(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")

        self.assertEqual(
            module._determine_after_sales_decision_status(SimpleNamespace(ticket_type="仅退款")),
            "待退款",
        )
        self.assertEqual(
            module._determine_after_sales_decision_status(SimpleNamespace(ticket_type="换货")),
            "待补发",
        )
        self.assertEqual(
            module._determine_after_sales_decision_status(SimpleNamespace(ticket_type="投诉")),
            "待处理",
        )

    def test_validate_items_reuses_cached_sales_order_item_and_item_meta(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        self.env.db.exists_map.update(
            {
                ("Item", "FG-001"): True,
                ("Style", "ST-001"): True,
            }
        )
        self.env.db.value_map[
            (
                "Sales Order Item",
                "SOI-001",
                ("parent", "item_code", "style", "color_code", "size_code", "rate", "uom", "warehouse", "delivery_date"),
                True,
            )
        ] = {
            "parent": "SO-001",
            "item_code": "FG-001",
            "style": "ST-001",
            "color_code": "BLK",
            "size_code": "M",
            "rate": 99,
            "uom": "Nos",
            "warehouse": "WH-01",
            "delivery_date": "2026-03-10",
        }
        self.env.db.value_map[
            ("Item", "FG-001", ("style", "color_code", "size_code"), True)
        ] = {
            "style": "ST-001",
            "color_code": "BLK",
            "size_code": "M",
        }
        lookup_counter = Counter()
        original_get_value = self.env.db.get_value

        def counting_get_value(doctype, name, fieldname, as_dict=False):
            frozen_field = tuple(fieldname) if isinstance(fieldname, list) else fieldname
            lookup_counter[(doctype, name, frozen_field, as_dict)] += 1
            return original_get_value(doctype, name, fieldname, as_dict=as_dict)

        self.env.db.get_value = counting_get_value
        doc = SimpleNamespace(
            flags=SimpleNamespace(),
            ticket_type="退货退款",
            sales_order="",
            delivery_note="",
            return_reason="",
            return_disposition="",
            items=[
                SimpleNamespace(
                    idx=1,
                    sales_order_item_ref="SOI-001",
                    delivery_note_item_ref="",
                    item_code="",
                    style="",
                    color_code="",
                    size_code="",
                    requested_action="",
                    qty=1,
                    received_qty=0,
                    restock_qty=0,
                    defective_qty=0,
                    inspection_note="",
                    return_reason="",
                    return_disposition="",
                    inventory_status_from="",
                    inventory_status_to="",
                ),
                SimpleNamespace(
                    idx=2,
                    sales_order_item_ref="SOI-001",
                    delivery_note_item_ref="",
                    item_code="",
                    style="",
                    color_code="",
                    size_code="",
                    requested_action="",
                    qty=1,
                    received_qty=0,
                    restock_qty=0,
                    defective_qty=0,
                    inspection_note="",
                    return_reason="",
                    return_disposition="",
                    inventory_status_from="",
                    inventory_status_to="",
                ),
            ],
        )

        module._validate_items(doc)

        self.assertEqual(doc.sales_order, "SO-001")
        self.assertEqual(doc.items[0].item_code, "FG-001")
        self.assertEqual(doc.items[1].item_code, "FG-001")
        self.assertEqual(
            lookup_counter[
                (
                    "Sales Order Item",
                    "SOI-001",
                    ("parent", "item_code", "style", "color_code", "size_code", "rate", "uom", "warehouse", "delivery_date"),
                    True,
                )
            ],
            1,
        )
        self.assertEqual(
            lookup_counter[
                ("Item", "FG-001", ("style", "color_code", "size_code"), True)
            ],
            1,
        )

    def test_build_replacement_sales_order_items_reuses_cached_sales_order_item_rows(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        self.env.meta_fields["Sales Order Item"] = {
            "item_code",
            "qty",
            "rate",
            "uom",
            "delivery_date",
            "warehouse",
            "style",
            "color_code",
            "size_code",
        }
        self.env.db.value_map[
            (
                "Sales Order Item",
                "SOI-002",
                ("parent", "item_code", "style", "color_code", "size_code", "rate", "uom", "warehouse", "delivery_date"),
                True,
            )
        ] = {
            "parent": "SO-002",
            "item_code": "FG-002",
            "style": "ST-002",
            "color_code": "WHT",
            "size_code": "L",
            "rate": 129,
            "uom": "Nos",
            "warehouse": "WH-SO",
            "delivery_date": "2026-03-12",
        }
        lookup_counter = Counter()
        original_get_value = self.env.db.get_value

        def counting_get_value(doctype, name, fieldname, as_dict=False):
            frozen_field = tuple(fieldname) if isinstance(fieldname, list) else fieldname
            lookup_counter[(doctype, name, frozen_field, as_dict)] += 1
            return original_get_value(doctype, name, fieldname, as_dict=as_dict)

        self.env.db.get_value = counting_get_value
        doc = SimpleNamespace(
            flags=SimpleNamespace(),
            warehouse="WH-RET",
            items=[
                SimpleNamespace(
                    requested_action="补发",
                    sales_order_item_ref="SOI-002",
                    qty=1,
                    received_qty=0,
                    item_code="FG-002",
                    style="ST-002",
                    color_code="WHT",
                    size_code="L",
                ),
                SimpleNamespace(
                    requested_action="补发",
                    sales_order_item_ref="SOI-002",
                    qty=2,
                    received_qty=0,
                    item_code="FG-002",
                    style="ST-002",
                    color_code="WHT",
                    size_code="L",
                ),
            ],
        )

        module._reset_after_sales_validation_cache(doc)
        items = module._build_replacement_sales_order_items(doc, set_warehouse="")

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["rate"], 129)
        self.assertEqual(items[0]["uom"], "Nos")
        self.assertEqual(items[0]["delivery_date"], "2026-03-12")
        self.assertEqual(items[0]["warehouse"], "WH-SO")
        self.assertEqual(items[1]["qty"], 2.0)
        self.assertEqual(
            lookup_counter[
                (
                    "Sales Order Item",
                    "SOI-002",
                    ("parent", "item_code", "style", "color_code", "size_code", "rate", "uom", "warehouse", "delivery_date"),
                    True,
                )
            ],
            1,
        )

    def test_after_sales_header_sync_reuses_cached_sales_order_and_context_queries(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        self.env.db.value_map.update(
            {
                (
                    "Sales Order",
                    "SO-001",
                    (
                        "customer",
                        "customer_name",
                        "channel",
                        "channel_store",
                        "external_order_id",
                        "company",
                        "delivery_date",
                    ),
                    True,
                ): {
                    "customer": "CUST-001",
                    "customer_name": "张三",
                    "channel": "抖音",
                    "channel_store": "STORE-01",
                    "external_order_id": "EXT-001",
                    "company": "COMP-01",
                    "delivery_date": "2026-03-10",
                },
                ("Channel Store", "STORE-01", "channel", False): "抖音",
                ("Warehouse Location", "LOC-01", "warehouse", False): "WH-01",
            }
        )
        lookup_counter = Counter()
        original_get_value = self.env.db.get_value

        def counting_get_value(doctype, name, fieldname, as_dict=False):
            frozen_field = tuple(fieldname) if isinstance(fieldname, list) else fieldname
            lookup_counter[(doctype, name, frozen_field, as_dict)] += 1
            return original_get_value(doctype, name, fieldname, as_dict=as_dict)

        self.env.db.get_value = counting_get_value
        doc = SimpleNamespace(
            flags=SimpleNamespace(),
            sales_order="SO-001",
            sales_invoice="",
            delivery_note="",
            customer="",
            buyer_name="",
            channel="",
            channel_store="",
            external_order_id="",
            warehouse="",
            warehouse_location="LOC-01",
        )

        module._reset_after_sales_validation_cache(doc)
        module._sync_from_sales_order(doc)
        module._sync_from_sales_order(doc)
        module._sync_location_context(doc)
        module._sync_location_context(doc)

        self.assertEqual(module._get_after_sales_company(doc), "COMP-01")
        self.assertEqual(module._get_after_sales_company(doc), "COMP-01")
        self.assertEqual(module._get_after_sales_delivery_date(doc), "2026-03-10")
        self.assertEqual(module._get_after_sales_delivery_date(doc), "2026-03-10")

        self.assertEqual(doc.customer, "CUST-001")
        self.assertEqual(doc.buyer_name, "张三")
        self.assertEqual(doc.channel_store, "STORE-01")
        self.assertEqual(doc.external_order_id, "EXT-001")
        self.assertEqual(doc.warehouse, "WH-01")
        self.assertEqual(
            lookup_counter[
                (
                    "Sales Order",
                    "SO-001",
                    (
                        "customer",
                        "customer_name",
                        "channel",
                        "channel_store",
                        "external_order_id",
                        "company",
                        "delivery_date",
                    ),
                    True,
                )
            ],
            1,
        )
        self.assertEqual(lookup_counter[("Channel Store", "STORE-01", "channel", False)], 1)
        self.assertEqual(lookup_counter[("Warehouse Location", "LOC-01", "warehouse", False)], 1)

    def test_after_sales_default_company_and_stock_entry_type_reuse_cached_exists_checks(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        self.env.frappe.defaults = SimpleNamespace(
            get_user_default=lambda key: "COMP-01" if key == "Company" else "",
            get_global_default=lambda _key: "",
        )
        self.env.db.exists_map.update(
            {
                ("Company", "COMP-01"): True,
                ("Stock Entry Type", "Material Receipt"): True,
            }
        )
        self.env.meta_fields["Stock Entry"] = {
            "purpose",
            "stock_entry_type",
            "company",
            "after_sales_ticket",
            "from_warehouse",
            "to_warehouse",
            "remarks",
            "items",
        }
        exists_counter = Counter()
        original_exists = self.env.db.exists

        def counting_exists(doctype, name):
            exists_counter[(doctype, name)] += 1
            return original_exists(doctype, name)

        self.env.db.exists = counting_exists
        doc = SimpleNamespace(
            flags=SimpleNamespace(),
            name="TK-001",
            sales_order="",
        )

        module._reset_after_sales_validation_cache(doc)
        self.assertEqual(module._get_after_sales_company(doc), "COMP-01")
        self.assertEqual(module._get_after_sales_company(doc), "COMP-01")
        module._build_after_sales_stock_entry_payload(
            doc,
            company="COMP-01",
            purpose="Material Receipt",
            source_warehouse="",
            target_warehouse="WH-RET",
            remark="",
            entry_mode="待检入库",
            items=[],
        )
        module._build_after_sales_stock_entry_payload(
            doc,
            company="COMP-01",
            purpose="Material Receipt",
            source_warehouse="",
            target_warehouse="WH-RET",
            remark="",
            entry_mode="待检入库",
            items=[],
        )

        self.assertEqual(exists_counter[("Company", "COMP-01")], 1)
        self.assertEqual(exists_counter[("Stock Entry Type", "Material Receipt")], 1)

    def test_approve_after_sales_refund_keeps_ticket_open_until_inventory_is_finalized(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        doc = FakeDoc(
            name="TK-REF-001",
            ticket_no="TK-REF-001",
            ticket_type="退货退款",
            ticket_status="待退款",
            refund_status="待退款",
            refund_amount=99,
            replacement_sales_order="",
            return_disposition="A1",
            received_at=None,
            warehouse="WH-RET",
            warehouse_location="",
            logistics_company="",
            tracking_no="",
            inventory_closure_status="待检已入账",
            pending_return_stock_entry="STE-PENDING-001",
            final_disposition_stock_entry="",
            items=[SimpleNamespace(idx=1, qty=1, received_qty=1, restock_qty=1, defective_qty=0)],
        )

        with patch.object(module, "_get_after_sales_ticket_doc", return_value=doc), patch.object(
            module,
            "get_after_sales_inventory_closure_summary",
            return_value={
                "inventory_closure_status": "待检已入账",
                "pending_return_stock_entry": "STE-PENDING-001",
                "final_disposition_stock_entry": "",
            },
        ):
            result = module.approve_after_sales_refund("TK-REF-001", refund_amount=99)

        self.assertEqual(result["ticket_status"], "待处理")
        self.assertEqual(result["refund_status"], "已退款")
        self.assertEqual(doc.ticket_status, "待处理")
        self.assertEqual(doc.logs[-1].action_type, "退款")

    def test_close_after_sales_ticket_requires_final_inventory_writeback(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        doc = FakeDoc(
            name="TK-CLOSE-001",
            ticket_no="TK-CLOSE-001",
            ticket_type="退货退款",
            ticket_status="待处理",
            refund_status="已退款",
            refund_amount=99,
            replacement_sales_order="",
            return_disposition="A1",
            received_at=None,
            warehouse="WH-RET",
            warehouse_location="",
            logistics_company="",
            tracking_no="",
            inventory_closure_status="待检已入账",
            pending_return_stock_entry="STE-PENDING-001",
            final_disposition_stock_entry="",
            items=[SimpleNamespace(idx=1, qty=1, received_qty=1, restock_qty=1, defective_qty=0)],
        )

        with patch.object(module, "_get_after_sales_ticket_doc", return_value=doc), patch.object(
            module,
            "get_after_sales_inventory_closure_summary",
            return_value={
                "inventory_closure_status": "待检已入账",
                "pending_return_stock_entry": "STE-PENDING-001",
                "final_disposition_stock_entry": "",
            },
        ):
            with self.assertRaisesRegex(self.env.FrappeThrow, "必须先完成最终处理库存回写"):
                module.close_after_sales_ticket("TK-CLOSE-001")

    def test_close_after_sales_ticket_requires_completed_replacement_order(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        doc = FakeDoc(
            name="TK-CLOSE-REPL-001",
            ticket_no="TK-CLOSE-REPL-001",
            ticket_type="补发",
            ticket_status="待补发",
            refund_status="无需退款",
            refund_amount=0,
            replacement_sales_order="SO-REPL-001",
            replacement_fulfillment_status="待发货",
            return_disposition="",
            received_at=None,
            warehouse="WH-RET",
            warehouse_location="",
            logistics_company="",
            tracking_no="",
            inventory_closure_status="未回写",
            pending_return_stock_entry="",
            final_disposition_stock_entry="",
            items=[],
        )

        with patch.object(module, "_get_after_sales_ticket_doc", return_value=doc), patch.object(
            module,
            "_get_replacement_order_fulfillment_status",
            return_value="待发货",
        ):
            with self.assertRaisesRegex(self.env.FrappeThrow, "必须先完成补发销售订单履约"):
                module.close_after_sales_ticket("TK-CLOSE-REPL-001")

    def test_create_replacement_sales_order_inserts_draft_and_syncs_ticket(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        doc = FakeDoc(
            name="TK-REPL-001",
            ticket_no="TK-REPL-001",
            ticket_type="补发",
            ticket_status="待补发",
            refund_status="无需退款",
            refund_amount=0,
            replacement_sales_order="",
            replacement_fulfillment_status="",
            items=[],
        )

        class DraftSalesOrder:
            def __init__(self):
                self.name = "SO-REPL-001"
                self.insert_calls = []

            def insert(self, **kwargs):
                self.insert_calls.append(kwargs)
                return self

        sales_order = DraftSalesOrder()

        def get_doc(payload_or_doctype, name=None):
            if isinstance(payload_or_doctype, dict):
                self.assertEqual(payload_or_doctype.get("doctype"), "Sales Order")
                return sales_order
            raise KeyError((payload_or_doctype, name))

        self.env.get_doc_handler = get_doc

        with patch.object(module, "_get_after_sales_ticket_doc", return_value=doc), patch.object(
            module,
            "_build_replacement_sales_order_payload",
            return_value={"doctype": "Sales Order", "company": "COMP-01", "items": [{"doctype": "Sales Order Item"}]},
        ), patch.object(
            module,
            "sync_after_sales_ticket_replacement_order",
            return_value={
                "replacement_sales_order": "SO-REPL-001",
                "replacement_fulfillment_status": "待配货",
                "ticket_status": "待补发",
            },
        ) as mocked_sync:
            result = module.create_replacement_sales_order("TK-REPL-001", company="COMP-01")

        self.assertEqual(sales_order.insert_calls, [{"ignore_permissions": True}])
        self.assertEqual(result["sales_order"], "SO-REPL-001")
        self.assertEqual(result["replacement_fulfillment_status"], "待配货")
        mocked_sync.assert_called_once_with(
            "TK-REPL-001",
            sales_order_name="SO-REPL-001",
            sales_order_doc=sales_order,
            operation="create",
        )

    def test_submit_after_sales_stock_entry_inserts_and_submits_stock_entry(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")

        class SubmittedStockEntry:
            def __init__(self):
                self.name = "STE-001"
                self.insert_calls = []
                self.submit_calls = []

            def insert(self, **kwargs):
                self.insert_calls.append(kwargs)
                return self

            def submit(self):
                self.submit_calls.append({})
                return self

        stock_entry = SubmittedStockEntry()

        def get_doc(payload_or_doctype, name=None):
            if isinstance(payload_or_doctype, dict):
                self.assertEqual(payload_or_doctype.get("doctype"), "Stock Entry")
                return stock_entry
            raise KeyError((payload_or_doctype, name))

        self.env.get_doc_handler = get_doc

        with patch.object(
            module,
            "prepare_after_sales_stock_entry",
            return_value={
                "ok": True,
                "payload": {"doctype": "Stock Entry", "company": "COMP-01", "items": [{"doctype": "Stock Entry Detail"}]},
            },
        ), patch.object(
            module,
            "sync_after_sales_ticket_inventory_closure",
            return_value={
                "inventory_closure_status": "待检已入账",
                "pending_return_stock_entry": "STE-001",
                "final_disposition_stock_entry": "",
            },
        ) as mocked_sync:
            result = module.submit_after_sales_stock_entry(
                "TK-001",
                entry_mode="待检入库",
                company="COMP-01",
            )

        self.assertEqual(stock_entry.insert_calls, [{"ignore_permissions": True}])
        self.assertEqual(stock_entry.submit_calls, [{}])
        self.assertEqual(result["stock_entry"], "STE-001")
        self.assertEqual(result["inventory_closure_status"], "待检已入账")
        mocked_sync.assert_called_once_with(
            "TK-001",
            stock_entry_name="STE-001",
            operation="submit",
        )

    def test_sync_after_sales_ticket_inventory_closure_reopens_closed_ticket_when_final_entry_is_canceled(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        doc = FakeDoc(
            name="TK-SYNC-001",
            ticket_no="TK-SYNC-001",
            ticket_type="退货退款",
            ticket_status="已关闭",
            refund_status="已退款",
            refund_amount=99,
            replacement_sales_order="",
            inventory_closure_status="已最终处理",
            pending_return_stock_entry="STE-PENDING-001",
            final_disposition_stock_entry="STE-FINAL-001",
            items=[SimpleNamespace(idx=1, qty=1, received_qty=1, restock_qty=1, defective_qty=0)],
        )

        with patch.object(module, "_get_after_sales_ticket_doc", return_value=doc), patch.object(
            module,
            "get_after_sales_inventory_closure_summary",
            return_value={
                "inventory_closure_status": "待检已入账",
                "pending_return_stock_entry": "STE-PENDING-001",
                "final_disposition_stock_entry": "",
            },
        ):
            result = module.sync_after_sales_ticket_inventory_closure(
                "TK-SYNC-001",
                stock_entry_name="STE-FINAL-001",
                operation="cancel",
            )

        self.assertEqual(result["inventory_closure_status"], "待检已入账")
        self.assertEqual(doc.ticket_status, "待处理")
        self.assertEqual(doc.inventory_closure_status, "待检已入账")
        self.assertEqual(doc.final_disposition_stock_entry, "")
        self.assertEqual(doc.logs[-1].action_type, "状态变更")
        self.assertEqual(doc.save_calls, [{"ignore_permissions": True, "ignore_version": True}])

    def test_sync_after_sales_ticket_replacement_order_auto_closes_when_replacement_is_completed(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.after_sales_service")
        doc = FakeDoc(
            name="TK-REPL-SYNC-001",
            ticket_no="TK-REPL-SYNC-001",
            ticket_type="补发",
            ticket_status="待补发",
            refund_status="无需退款",
            refund_amount=0,
            replacement_sales_order="SO-REPL-001",
            replacement_fulfillment_status="待发货",
            inventory_closure_status="未回写",
            pending_return_stock_entry="",
            final_disposition_stock_entry="",
            items=[],
        )

        with patch.object(module, "_get_after_sales_ticket_doc", return_value=doc), patch.object(
            module,
            "_get_replacement_order_fulfillment_status",
            return_value="已发货",
        ):
            result = module.sync_after_sales_ticket_replacement_order(
                "TK-REPL-SYNC-001",
                sales_order_name="SO-REPL-001",
                operation="update",
            )

        self.assertEqual(result["ticket_status"], "已关闭")
        self.assertEqual(doc.ticket_status, "已关闭")
        self.assertEqual(doc.replacement_fulfillment_status, "已发货")
        self.assertEqual(doc.logs[-1].action_type, "关闭")
        self.assertEqual(doc.save_calls, [{"ignore_permissions": True, "ignore_version": True}])


if __name__ == "__main__":
    unittest.main()
