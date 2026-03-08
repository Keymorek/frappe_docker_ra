from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from helpers import FakeDoc, build_frappe_env


class TestStockEntryEvent(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_validate_inventory_status_rules_syncs_header_delivery_note_to_rows(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.stock_entry")
        doc = FakeDoc(
            delivery_note="DN-001",
            items=[
                SimpleNamespace(
                    item_code="PKG-001",
                    delivery_note="",
                    inventory_status_from="",
                    inventory_status_to="",
                    return_reason="",
                    return_disposition="",
                )
            ],
        )

        module.validate_inventory_status_rules(doc)

        self.assertEqual(doc.items[0].delivery_note, "DN-001")

    def test_validate_inventory_status_rules_promotes_row_delivery_note_to_header(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.stock_entry")
        doc = FakeDoc(
            delivery_note="",
            items=[
                SimpleNamespace(
                    item_code="PKG-001",
                    delivery_note="DN-002",
                    inventory_status_from="",
                    inventory_status_to="",
                    return_reason="",
                    return_disposition="",
                )
            ],
        )

        module.validate_inventory_status_rules(doc)

        self.assertEqual(doc.delivery_note, "DN-002")

    def test_sync_linked_after_sales_ticket_inventory_closure_batches_existing_ticket_queries(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.stock_entry")
        doc = FakeDoc(
            name="STE-001",
            docstatus=1,
            after_sales_ticket="",
            items=[
                SimpleNamespace(after_sales_ticket="TK-001"),
                SimpleNamespace(after_sales_ticket="TK-001"),
                SimpleNamespace(after_sales_ticket="TK-002"),
            ],
        )

        def get_all(doctype, **kwargs):
            if doctype == "After Sales Ticket":
                self.assertEqual(kwargs.get("filters"), {"name": ["in", ["TK-001", "TK-002"]]})
                return [{"name": "TK-001"}]
            return []

        self.env.get_all_handler = get_all

        with patch.object(module, "sync_after_sales_ticket_inventory_closure") as mocked_sync:
            module.sync_linked_after_sales_ticket_inventory_closure(doc)

        mocked_sync.assert_called_once_with(
            "TK-001",
            stock_entry_name="STE-001",
            operation="submit",
        )

    def test_sync_linked_after_sales_ticket_inventory_closure_uses_cancel_operation(self):
        module = self.env.load_module("fashion_erp.fashion_stock.events.stock_entry")
        doc = FakeDoc(
            name="STE-002",
            docstatus=2,
            after_sales_ticket="TK-003",
            items=[SimpleNamespace(after_sales_ticket="")],
        )
        self.env.get_all_handler = lambda doctype, **kwargs: (
            [{"name": "TK-003"}] if doctype == "After Sales Ticket" else []
        )

        with patch.object(module, "sync_after_sales_ticket_inventory_closure") as mocked_sync:
            module.sync_linked_after_sales_ticket_inventory_closure(doc, method="on_cancel")

        mocked_sync.assert_called_once_with(
            "TK-003",
            stock_entry_name="STE-002",
            operation="cancel",
        )


if __name__ == "__main__":
    unittest.main()
