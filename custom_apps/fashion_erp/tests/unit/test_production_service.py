from __future__ import annotations

import unittest
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch

from helpers import build_frappe_env


class TestProductionService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_reference_validation_reuses_cached_link_checks_and_batches_field_queries(self):
        module = self.env.load_module("fashion_erp.garment_mfg.services.production_service")
        self.env.meta_fields["BOM"] = {"style", "production_ticket", "item"}
        self.env.meta_fields["Work Order"] = {"style", "production_ticket"}
        self.env.db.exists_map.update(
            {
                ("Style", "ST-001"): True,
                ("Item", "IT-TPL-001"): True,
                ("BOM", "BOM-001"): True,
                ("Work Order", "WO-001"): True,
                ("Supplier", "SUP-001"): True,
            }
        )
        self.env.db.value_map.update(
            {
                ("BOM", "BOM-001", ("style", "production_ticket", "item"), True): {
                    "style": "ST-001",
                    "production_ticket": "PT-001",
                    "item": "IT-TPL-001",
                },
                ("Work Order", "WO-001", ("style", "production_ticket"), True): {
                    "style": "ST-001",
                    "production_ticket": "PT-001",
                },
                ("Style", "ST-001", ("size_range_summary", "size_system"), True): {
                    "size_range_summary": "S-M",
                    "size_system": "TOP",
                },
            }
        )
        exists_counter = Counter()
        original_exists = self.env.db.exists

        def counting_exists(doctype, name):
            exists_counter[(doctype, name)] += 1
            return original_exists(doctype, name)

        lookup_counter = Counter()
        original_get_value = self.env.db.get_value

        def counting_get_value(doctype, name, fieldname, as_dict=False):
            frozen_field = tuple(fieldname) if isinstance(fieldname, list) else fieldname
            lookup_counter[(doctype, name, frozen_field, as_dict)] += 1
            return original_get_value(doctype, name, fieldname, as_dict=as_dict)

        self.env.db.exists = counting_exists
        self.env.db.get_value = counting_get_value
        doc = SimpleNamespace(
            flags=SimpleNamespace(),
            name="PT-001",
            style="ST-001",
            item_template="IT-TPL-001",
            bom_no="BOM-001",
            work_order="WO-001",
            supplier="SUP-001",
        )

        module._reset_production_ticket_validation_cache(doc)
        module._ensure_cached_link_exists(doc, "Style", doc.style)
        module._ensure_cached_link_exists(doc, "Item", doc.item_template)
        module._ensure_cached_link_exists(doc, "BOM", doc.bom_no)
        module._ensure_cached_link_exists(doc, "Work Order", doc.work_order)
        module._ensure_cached_link_exists(doc, "Supplier", doc.supplier)

        with patch.object(module, "get_size_range_summary", side_effect=lambda size_system: f"SIZE:{size_system}"):
            module._validate_bom_reference(doc)
            module._validate_bom_reference(doc)
            module._validate_work_order_reference(doc)
            module._validate_work_order_reference(doc)
            self.assertEqual(module._build_ticket_size_range(doc), "S-M")
            self.assertEqual(module._build_ticket_size_range(doc), "S-M")

        self.assertEqual(exists_counter[("Style", "ST-001")], 1)
        self.assertEqual(exists_counter[("Item", "IT-TPL-001")], 1)
        self.assertEqual(exists_counter[("BOM", "BOM-001")], 1)
        self.assertEqual(exists_counter[("Work Order", "WO-001")], 1)
        self.assertEqual(exists_counter[("Supplier", "SUP-001")], 1)
        self.assertEqual(
            lookup_counter[("BOM", "BOM-001", ("style", "production_ticket", "item"), True)],
            1,
        )
        self.assertEqual(
            lookup_counter[("Work Order", "WO-001", ("style", "production_ticket"), True)],
            1,
        )
        self.assertEqual(
            lookup_counter[("Style", "ST-001", ("size_range_summary", "size_system"), True)],
            1,
        )

    def test_ticket_company_and_stock_entry_type_reuse_cached_exists_and_reference_queries(self):
        module = self.env.load_module("fashion_erp.garment_mfg.services.production_service")
        self.env.frappe.defaults = SimpleNamespace(
            get_user_default=lambda _key: "",
            get_global_default=lambda _key: "",
        )
        self.env.meta_fields["Work Order"] = {"company"}
        self.env.db.exists_map.update(
            {
                ("Work Order", "WO-002"): True,
                ("Stock Entry Type", "Material Receipt"): True,
            }
        )
        self.env.db.value_map[
            ("Work Order", "WO-002", ("company",), True)
        ] = {
            "company": "COMP-01",
        }
        exists_counter = Counter()
        original_exists = self.env.db.exists

        def counting_exists(doctype, name):
            exists_counter[(doctype, name)] += 1
            return original_exists(doctype, name)

        lookup_counter = Counter()
        original_get_value = self.env.db.get_value

        def counting_get_value(doctype, name, fieldname, as_dict=False):
            frozen_field = tuple(fieldname) if isinstance(fieldname, list) else fieldname
            lookup_counter[(doctype, name, frozen_field, as_dict)] += 1
            return original_get_value(doctype, name, fieldname, as_dict=as_dict)

        self.env.db.exists = counting_exists
        self.env.db.get_value = counting_get_value
        doc = SimpleNamespace(
            flags=SimpleNamespace(),
            work_order="WO-002",
            bom_no="",
        )

        self.assertEqual(module._get_ticket_company(doc), "COMP-01")
        self.assertEqual(module._get_ticket_company(doc), "COMP-01")
        self.assertEqual(module._get_stock_entry_type(doc, "Material Receipt"), "Material Receipt")
        self.assertEqual(module._get_stock_entry_type(doc, "Material Receipt"), "Material Receipt")

        self.assertEqual(exists_counter[("Work Order", "WO-002")], 1)
        self.assertEqual(exists_counter[("Stock Entry Type", "Material Receipt")], 1)
        self.assertEqual(
            lookup_counter[("Work Order", "WO-002", ("company",), True)],
            1,
        )


if __name__ == "__main__":
    unittest.main()
