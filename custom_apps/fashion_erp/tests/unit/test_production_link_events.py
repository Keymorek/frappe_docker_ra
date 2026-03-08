from __future__ import annotations

import unittest
from types import SimpleNamespace

from helpers import FakeDoc, build_frappe_env


class TestProductionLinkEvents(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()
        self.env.frappe.flags = SimpleNamespace()

    def tearDown(self):
        self.env.cleanup()

    def test_bom_event_updates_production_ticket_when_fields_need_backfill(self):
        module = self.env.load_module("fashion_erp.garment_mfg.events.bom")
        self.env.db.value_map[("Production Ticket", "PT-001", ("bom_no", "item_template"), True)] = {
            "bom_no": "",
            "item_template": "",
        }
        ticket = FakeDoc(name="PT-001", bom_no="", item_template="")
        self.env.get_doc_handler = (
            lambda doctype, name=None: ticket if (doctype, name) == ("Production Ticket", "PT-001") else None
        )
        doc = FakeDoc(name="BOM-001", production_ticket="PT-001", item="SKU-001")

        module.sync_production_ticket(doc)

        self.assertEqual(ticket.bom_no, "BOM-001")
        self.assertEqual(ticket.item_template, "SKU-001")
        self.assertEqual(ticket.save_calls, [{"ignore_permissions": True}])

    def test_bom_event_skips_full_ticket_load_when_already_synced(self):
        module = self.env.load_module("fashion_erp.garment_mfg.events.bom")
        self.env.db.value_map[("Production Ticket", "PT-002", ("bom_no", "item_template"), True)] = {
            "bom_no": "BOM-002",
            "item_template": "SKU-002",
        }

        def fail_exists(doctype, name):
            if (doctype, name) == ("Production Ticket", "PT-002"):
                self.fail("expected lightweight row lookup without exists")
            return False

        def fail_get_doc(doctype, name=None):
            if (doctype, name) == ("Production Ticket", "PT-002"):
                self.fail("expected no full ticket load when BOM link is already synced")
            return None

        self.env.db.exists = fail_exists
        self.env.get_doc_handler = fail_get_doc
        doc = FakeDoc(name="BOM-002", production_ticket="PT-002", item="SKU-002")

        module.sync_production_ticket(doc)

    def test_work_order_event_updates_production_ticket_when_fields_need_backfill(self):
        module = self.env.load_module("fashion_erp.garment_mfg.events.work_order")
        self.env.db.value_map[("Production Ticket", "PT-003", ("work_order", "bom_no", "item_template"), True)] = {
            "work_order": "",
            "bom_no": "",
            "item_template": "",
        }
        ticket = FakeDoc(name="PT-003", work_order="", bom_no="", item_template="")
        self.env.get_doc_handler = (
            lambda doctype, name=None: ticket if (doctype, name) == ("Production Ticket", "PT-003") else None
        )
        doc = FakeDoc(
            name="WO-001",
            production_ticket="PT-003",
            bom_no="BOM-003",
            production_item="SKU-003",
        )

        module.sync_production_ticket(doc)

        self.assertEqual(ticket.work_order, "WO-001")
        self.assertEqual(ticket.bom_no, "BOM-003")
        self.assertEqual(ticket.item_template, "SKU-003")
        self.assertEqual(ticket.save_calls, [{"ignore_permissions": True}])

    def test_work_order_event_skips_full_ticket_load_when_already_synced(self):
        module = self.env.load_module("fashion_erp.garment_mfg.events.work_order")
        self.env.db.value_map[("Production Ticket", "PT-004", ("work_order", "bom_no", "item_template"), True)] = {
            "work_order": "WO-002",
            "bom_no": "BOM-004",
            "item_template": "SKU-004",
        }

        def fail_exists(doctype, name):
            if (doctype, name) == ("Production Ticket", "PT-004"):
                self.fail("expected lightweight row lookup without exists")
            return False

        def fail_get_doc(doctype, name=None):
            if (doctype, name) == ("Production Ticket", "PT-004"):
                self.fail("expected no full ticket load when work order link is already synced")
            return None

        self.env.db.exists = fail_exists
        self.env.get_doc_handler = fail_get_doc
        doc = FakeDoc(
            name="WO-002",
            production_ticket="PT-004",
            bom_no="BOM-004",
            production_item="SKU-004",
        )

        module.sync_production_ticket(doc)


if __name__ == "__main__":
    unittest.main()
