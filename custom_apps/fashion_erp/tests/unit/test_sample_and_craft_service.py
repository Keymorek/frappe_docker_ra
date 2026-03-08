from __future__ import annotations

import unittest
from collections import Counter
from types import SimpleNamespace

from helpers import build_frappe_env


class TestSampleAndCraftService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_validate_sample_ticket_reuses_cached_color_and_user_lookups(self):
        module = self.env.load_module("fashion_erp.style.services.sample_service")
        self.env.db.exists_map.update(
            {
                ("Style", "ST-001"): True,
                ("Item", "IT-TPL-001"): True,
                ("Color", "COLOR-BLK"): True,
                ("Supplier", "SUP-001"): True,
                ("User", "designer@example.com"): True,
            }
        )
        self.env.db.value_map[
            ("Style", "ST-001", ("style_name", "item_template"), True)
        ] = {
            "style_name": "测试款",
            "item_template": "IT-TPL-001",
        }
        self.env.db.value_map[
            ("Color", "COLOR-BLK", ("color_name", "color_group", "enabled"), True)
        ] = {
            "color_name": "黑色",
            "color_group": "BLACK",
            "enabled": 1,
        }
        self.env.db.value_map[("Color Group", "BLACK", "color_group_code", False)] = "BLK"

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
            flags=SimpleNamespace(skip_sample_ticket_system_log=True),
            name="New Sample Ticket 1",
            ticket_no="",
            sample_type="",
            sample_status="",
            priority="",
            style="ST-001",
            style_name="",
            item_template="IT-TPL-001",
            color="COLOR-BLK",
            color_name="",
            color_code="",
            requested_by="designer@example.com",
            handler_user="designer@example.com",
            supplier="SUP-001",
            requested_date="2026-03-08",
            expected_finish_date="",
            finished_at="",
            sample_qty=1,
            estimated_cost=0,
            actual_cost=0,
            sample_note="",
            review_note="",
            logs=[
                SimpleNamespace(
                    action_time="",
                    action_type="备注",
                    from_status="",
                    to_status="",
                    operator="designer@example.com",
                    note="首样备注",
                ),
                SimpleNamespace(
                    action_time="",
                    action_type="备注",
                    from_status="",
                    to_status="",
                    operator="designer@example.com",
                    note="再次备注",
                ),
            ],
        )

        module.validate_sample_ticket(doc)

        self.assertEqual(doc.color_name, "黑色")
        self.assertEqual(doc.color_code, "BLK")
        self.assertEqual(exists_counter[("User", "designer@example.com")], 1)
        self.assertEqual(
            lookup_counter[
                ("Color", "COLOR-BLK", ("color_name", "color_group", "enabled"), True)
            ],
            1,
        )
        self.assertEqual(
            lookup_counter[("Color Group", "BLACK", "color_group_code", False)],
            1,
        )

    def test_validate_craft_sheet_reuses_cached_sample_ticket_color_and_user_lookups(self):
        module = self.env.load_module("fashion_erp.style.services.craft_sheet_service")
        self.env.db.exists_map.update(
            {
                ("Style", "ST-001"): True,
                ("Item", "IT-TPL-001"): True,
                ("Sample Ticket", "SMP-001"): True,
                ("Color", "COLOR-BLK"): True,
                ("User", "designer@example.com"): True,
            }
        )
        self.env.db.value_map[
            ("Style", "ST-001", ("style_name", "item_template"), True)
        ] = {
            "style_name": "测试款",
            "item_template": "IT-TPL-001",
        }
        self.env.db.value_map[
            (
                "Sample Ticket",
                "SMP-001",
                ("style", "style_name", "item_template", "color", "color_name", "color_code"),
                True,
            )
        ] = {
            "style": "ST-001",
            "style_name": "测试款",
            "item_template": "IT-TPL-001",
            "color": "COLOR-BLK",
            "color_name": "黑色",
            "color_code": "BLK",
        }
        self.env.db.value_map[
            ("Color", "COLOR-BLK", ("color_name", "color_group", "enabled"), True)
        ] = {
            "color_name": "黑色",
            "color_group": "BLACK",
            "enabled": 1,
        }
        self.env.db.value_map[("Color Group", "BLACK", "color_group_code", False)] = "BLK"

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
            flags=SimpleNamespace(skip_craft_sheet_system_log=True),
            name="New Craft Sheet 1",
            sheet_no="",
            style="ST-001",
            style_name="",
            item_template="IT-TPL-001",
            sample_ticket="SMP-001",
            version_no="V1",
            sheet_status="",
            prepared_by="designer@example.com",
            effective_date="2026-03-08",
            color="COLOR-BLK",
            color_name="",
            color_code="",
            estimated_unit_cost=0,
            fabric_note="",
            trim_note="",
            size_note="",
            workmanship_note="",
            packaging_note="",
            qc_note="",
            reference_file="",
            remark="",
            logs=[
                SimpleNamespace(
                    action_time="",
                    action_type="备注",
                    from_status="",
                    to_status="",
                    operator="designer@example.com",
                    note="工艺备注",
                ),
                SimpleNamespace(
                    action_time="",
                    action_type="备注",
                    from_status="",
                    to_status="",
                    operator="designer@example.com",
                    note="再次工艺备注",
                ),
            ],
        )

        module.validate_craft_sheet(doc)

        self.assertEqual(doc.color_name, "黑色")
        self.assertEqual(doc.color_code, "BLK")
        self.assertEqual(exists_counter[("User", "designer@example.com")], 1)
        self.assertEqual(
            lookup_counter[
                (
                    "Sample Ticket",
                    "SMP-001",
                    ("style", "style_name", "item_template", "color", "color_name", "color_code"),
                    True,
                )
            ],
            1,
        )
        self.assertEqual(
            lookup_counter[
                ("Color", "COLOR-BLK", ("color_name", "color_group", "enabled"), True)
            ],
            1,
        )
        self.assertEqual(
            lookup_counter[("Color Group", "BLACK", "color_group_code", False)],
            1,
        )


if __name__ == "__main__":
    unittest.main()
