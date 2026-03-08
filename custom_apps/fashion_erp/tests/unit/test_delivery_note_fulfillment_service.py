from __future__ import annotations

import unittest
from collections import Counter
from types import SimpleNamespace

from helpers import FakeDoc, build_frappe_env


class TestDeliveryNoteFulfillmentService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()
        self.env.db.exists_map.update(
            {
                ("Company", "COMP-01"): True,
                ("Warehouse", "WH-PACK"): True,
                ("Warehouse", "WH-FG"): True,
                ("Item", "PKG-001"): True,
                ("Item", "SKU-001"): True,
            }
        )
        self.env.db.value_map[
            ("Item", "PKG-001", ("item_name", "stock_uom", "valuation_rate", "is_fulfillment_consumable", "supply_warehouse"), True)
        ] = {
            "item_name": "快递袋",
            "stock_uom": "Nos",
            "valuation_rate": 1.5,
            "is_fulfillment_consumable": 1,
            "supply_warehouse": "WH-PACK",
        }
        self.env.db.value_map[
            ("Item", "SKU-001", ("item_name", "stock_uom", "valuation_rate", "is_fulfillment_consumable", "supply_warehouse"), True)
        ] = {
            "item_name": "成衣",
            "stock_uom": "Nos",
            "valuation_rate": 99,
            "is_fulfillment_consumable": 0,
            "supply_warehouse": "WH-FG",
        }

    def tearDown(self):
        self.env.cleanup()

    def test_validate_delivery_note_fulfillment_applies_defaults_and_summary(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.delivery_note_fulfillment_service")
        doc = FakeDoc(
            name="DN-001",
            set_warehouse="WH-FG",
            fulfillment_consumable_stock_entry="",
            manual_logistics_fee="8",
            fulfillment_consumable_qty=0,
            fulfillment_consumable_amount=0,
            fulfillment_total_cost=0,
            items=[],
            fulfillment_consumables=[
                SimpleNamespace(
                    item_code="PKG-001",
                    item_name="",
                    qty="2",
                    uom="",
                    warehouse="",
                    valuation_rate=0,
                    estimated_amount=0,
                )
            ],
        )

        module.validate_delivery_note_fulfillment(doc)

        self.assertEqual(doc.fulfillment_consumable_qty, 2)
        self.assertEqual(doc.fulfillment_consumable_amount, 3.0)
        self.assertEqual(doc.manual_logistics_fee, 8.0)
        self.assertEqual(doc.fulfillment_total_cost, 11.0)
        self.assertEqual(doc.fulfillment_consumables[0].item_name, "快递袋")
        self.assertEqual(doc.fulfillment_consumables[0].uom, "Nos")
        self.assertEqual(doc.fulfillment_consumables[0].warehouse, "WH-PACK")
        self.assertEqual(doc.fulfillment_consumables[0].valuation_rate, 1.5)
        self.assertEqual(doc.fulfillment_consumables[0].estimated_amount, 3.0)

    def test_validate_delivery_note_fulfillment_reuses_cached_item_and_warehouse_lookups(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.delivery_note_fulfillment_service")
        lookup_counter = Counter()
        original_get_value = self.env.db.get_value

        def counting_get_value(doctype, name, fieldname, as_dict=False):
            frozen_field = tuple(fieldname) if isinstance(fieldname, list) else fieldname
            lookup_counter[(doctype, name, frozen_field, as_dict)] += 1
            return original_get_value(doctype, name, fieldname, as_dict=as_dict)

        exists_counter = Counter()
        original_exists = self.env.db.exists

        def counting_exists(doctype, name):
            exists_counter[(doctype, name)] += 1
            return original_exists(doctype, name)

        self.env.db.get_value = counting_get_value
        self.env.db.exists = counting_exists
        doc = FakeDoc(
            name="DN-CACHE-001",
            set_warehouse="WH-FG",
            fulfillment_consumable_stock_entry="",
            manual_logistics_fee="6",
            fulfillment_consumable_qty=0,
            fulfillment_consumable_amount=0,
            fulfillment_total_cost=0,
            items=[],
            fulfillment_consumables=[
                SimpleNamespace(
                    item_code="PKG-001",
                    item_name="",
                    qty="2",
                    uom="",
                    warehouse="",
                    valuation_rate=0,
                    estimated_amount=0,
                ),
                SimpleNamespace(
                    item_code="PKG-001",
                    item_name="",
                    qty="1",
                    uom="",
                    warehouse="",
                    valuation_rate=0,
                    estimated_amount=0,
                ),
            ],
        )

        module.validate_delivery_note_fulfillment(doc)

        self.assertEqual(doc.fulfillment_consumable_qty, 3)
        self.assertEqual(doc.fulfillment_consumable_amount, 4.5)
        self.assertEqual(doc.fulfillment_total_cost, 10.5)
        self.assertEqual(
            lookup_counter[
                (
                    "Item",
                    "PKG-001",
                    ("item_name", "stock_uom", "valuation_rate", "is_fulfillment_consumable", "supply_warehouse"),
                    True,
                )
            ],
            1,
        )
        self.assertEqual(exists_counter[("Item", "PKG-001")], 1)
        self.assertEqual(exists_counter[("Warehouse", "WH-PACK")], 1)

    def test_validate_delivery_note_fulfillment_rejects_non_consumable_item(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.delivery_note_fulfillment_service")
        doc = FakeDoc(
            name="DN-002",
            set_warehouse="WH-FG",
            fulfillment_consumable_stock_entry="",
            manual_logistics_fee=0,
            fulfillment_consumable_qty=0,
            fulfillment_consumable_amount=0,
            fulfillment_total_cost=0,
            items=[],
            fulfillment_consumables=[
                SimpleNamespace(
                    item_code="SKU-001",
                    item_name="",
                    qty="1",
                    uom="",
                    warehouse="",
                    valuation_rate=0,
                    estimated_amount=0,
                )
            ],
        )

        with self.assertRaisesRegex(self.env.FrappeThrow, "不是包装耗材"):
            module.validate_delivery_note_fulfillment(doc)

    def test_validate_delivery_note_fulfillment_rejects_negative_manual_logistics_fee(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.delivery_note_fulfillment_service")
        doc = FakeDoc(
            name="DN-005",
            set_warehouse="WH-FG",
            fulfillment_consumable_stock_entry="",
            manual_logistics_fee="-1",
            fulfillment_consumable_qty=0,
            fulfillment_consumable_amount=0,
            fulfillment_total_cost=0,
            items=[],
            fulfillment_consumables=[],
        )

        with self.assertRaisesRegex(self.env.FrappeThrow, "手工快递费不能为负数"):
            module.validate_delivery_note_fulfillment(doc)

    def test_prepare_delivery_note_fulfillment_stock_entry_creates_draft_and_backfills_ref(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.delivery_note_fulfillment_service")
        self.env.meta_fields["Stock Entry"] = {
            "purpose",
            "stock_entry_type",
            "company",
            "posting_date",
            "delivery_note",
            "remarks",
            "items",
        }
        self.env.meta_fields["Stock Entry Detail"] = {
            "item_code",
            "qty",
            "s_warehouse",
            "delivery_note",
        }
        delivery_note = FakeDoc(
            doctype="Delivery Note",
            name="DN-003",
            company="COMP-01",
            docstatus=1,
            set_warehouse="WH-FG",
            fulfillment_consumable_stock_entry="",
            manual_logistics_fee="5.5",
            fulfillment_consumable_qty=0,
            fulfillment_consumable_amount=0,
            fulfillment_total_cost=0,
            items=[SimpleNamespace(warehouse="WH-FG")],
            fulfillment_consumables=[
                SimpleNamespace(
                    item_code="PKG-001",
                    item_name="",
                    qty="2",
                    uom="",
                    warehouse="",
                    valuation_rate=0,
                    estimated_amount=0,
                )
            ],
        )
        created_docs = []

        def get_doc(arg1, arg2=None):
            if isinstance(arg1, dict):
                payload = dict(arg1)
                payload.pop("doctype", None)
                items = [FakeDoc(**item) for item in payload.pop("items", [])]
                doc = FakeDoc(doctype="Stock Entry", name="STE-0001", items=items, **payload)

                def insert(ignore_permissions=False, *, _doc=doc):
                    created_docs.append(_doc)
                    _doc.insert_calls.append({"ignore_permissions": ignore_permissions})
                    return _doc

                doc.insert = insert
                return doc

            if (arg1, arg2) == ("Delivery Note", "DN-003"):
                return delivery_note
            raise KeyError((arg1, arg2))

        self.env.get_doc_handler = get_doc

        result = module.prepare_delivery_note_fulfillment_stock_entry("DN-003")

        self.assertEqual(result["stock_entry"], "STE-0001")
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(delivery_note.fulfillment_consumable_stock_entry, "STE-0001")
        self.assertEqual(delivery_note.fulfillment_consumable_amount, 3.0)
        self.assertEqual(delivery_note.fulfillment_total_cost, 8.5)
        self.assertEqual(result["manual_logistics_fee"], 5.5)
        self.assertEqual(result["fulfillment_total_cost"], 8.5)
        self.assertEqual(delivery_note.save_calls, [{"ignore_permissions": True, "ignore_version": True}])
        self.assertEqual(len(created_docs), 1)
        self.assertEqual(created_docs[0].insert_calls, [{"ignore_permissions": True}])
        self.assertEqual(created_docs[0].delivery_note, "DN-003")
        self.assertEqual(created_docs[0].items[0].item_code, "PKG-001")
        self.assertEqual(created_docs[0].items[0].s_warehouse, "WH-PACK")
        self.assertEqual(created_docs[0].items[0].qty, 2)

    def test_prepare_delivery_note_fulfillment_stock_entry_blocks_duplicate_reference(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.delivery_note_fulfillment_service")
        self.env.db.exists_map[("Stock Entry", "STE-EXISTS-001")] = True
        delivery_note = FakeDoc(
            doctype="Delivery Note",
            name="DN-004",
            company="COMP-01",
            docstatus=1,
            set_warehouse="WH-FG",
            fulfillment_consumable_stock_entry="STE-EXISTS-001",
            manual_logistics_fee=0,
            fulfillment_consumable_qty=0,
            fulfillment_consumable_amount=0,
            fulfillment_total_cost=0,
            items=[SimpleNamespace(warehouse="WH-FG")],
            fulfillment_consumables=[
                SimpleNamespace(
                    item_code="PKG-001",
                    item_name="",
                    qty="1",
                    uom="",
                    warehouse="",
                    valuation_rate=0,
                    estimated_amount=0,
                )
            ],
        )
        self.env.get_doc_handler = lambda doctype, name=None: delivery_note if (doctype, name) == ("Delivery Note", "DN-004") else None

        with self.assertRaisesRegex(self.env.FrappeThrow, "已关联耗材出库单"):
            module.prepare_delivery_note_fulfillment_stock_entry("DN-004")

    def test_get_delivery_note_fulfillment_cost_summary_aggregates_submitted_delivery_notes(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.delivery_note_fulfillment_service")
        captured = {}

        def get_all(doctype, **kwargs):
            captured["doctype"] = doctype
            captured["filters"] = kwargs.get("filters")
            captured["fields"] = kwargs.get("fields")
            captured["order_by"] = kwargs.get("order_by")
            return [
                {
                    "name": "DN-101",
                    "posting_date": "2026-03-01",
                    "customer": "CUST-01",
                    "company": "COMP-01",
                    "fulfillment_consumable_amount": 3,
                    "manual_logistics_fee": 10,
                    "fulfillment_total_cost": 13,
                },
                {
                    "name": "DN-102",
                    "posting_date": "2026-03-02",
                    "customer": "CUST-02",
                    "company": "COMP-01",
                    "fulfillment_consumable_amount": "4.5",
                    "manual_logistics_fee": "0",
                    "fulfillment_total_cost": "4.5",
                },
            ]

        self.env.get_all_handler = get_all

        result = module.get_delivery_note_fulfillment_cost_summary(
            date_from="2026-03-01",
            date_to="2026-03-31",
            company="COMP-01",
        )

        self.assertEqual(captured["doctype"], "Delivery Note")
        self.assertEqual(
            captured["filters"],
            [
                ["Delivery Note", "docstatus", "=", 1],
                ["Delivery Note", "posting_date", ">=", "2026-03-01"],
                ["Delivery Note", "posting_date", "<=", "2026-03-31"],
                ["Delivery Note", "company", "=", "COMP-01"],
            ],
        )
        self.assertEqual(
            captured["fields"],
            [
                "name",
                "posting_date",
                "customer",
                "company",
                "fulfillment_consumable_amount",
                "manual_logistics_fee",
                "fulfillment_total_cost",
            ],
        )
        self.assertEqual(captured["order_by"], "posting_date asc, modified asc")
        self.assertEqual(result["summary"]["delivery_note_count"], 2)
        self.assertEqual(result["summary"]["fulfillment_consumable_amount"], 7.5)
        self.assertEqual(result["summary"]["manual_logistics_fee"], 10.0)
        self.assertEqual(result["summary"]["fulfillment_total_cost"], 17.5)
        self.assertEqual(result["rows"][0]["delivery_note"], "DN-101")
        self.assertEqual(result["rows"][1]["posting_date"], "2026-03-02")
        self.assertIn("共 2 张已提交出货单", result["message"])


if __name__ == "__main__":
    unittest.main()
