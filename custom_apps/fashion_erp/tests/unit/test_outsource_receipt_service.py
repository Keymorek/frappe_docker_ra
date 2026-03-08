from __future__ import annotations

import unittest
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch

from helpers import FakeDoc, build_frappe_env


class TestOutsourceReceiptService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()
        self.env.db.exists_map.update(
            {
                ("Item", "FG-BLK-M"): True,
                ("Item", "FG-RED-M"): True,
                ("Style", "ST-001"): True,
            }
        )
        self.env.db.value_map[
            ("Item", "FG-BLK-M", ("item_name", "item_usage_type", "style", "color_code", "size_code"), True)
        ] = {
            "item_name": "黑色 M",
            "item_usage_type": "成品",
            "style": "ST-001",
            "color_code": "BLK",
            "size_code": "M",
        }
        self.env.db.value_map[
            ("Item", "FG-RED-M", ("item_name", "item_usage_type", "style", "color_code", "size_code"), True)
        ] = {
            "item_name": "红色 M",
            "item_usage_type": "成品",
            "style": "ST-001",
            "color_code": "RED",
            "size_code": "M",
        }

    def tearDown(self):
        self.env.cleanup()

    def test_normalize_items_allows_shortage_only_rows_and_builds_exception_summary(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_receipt_service")
        doc = SimpleNamespace(
            style="ST-001",
            color_code="BLK",
            items=[
                SimpleNamespace(
                    idx=1,
                    item_code="FG-BLK-M",
                    item_name="",
                    style="",
                    color_code="",
                    size_code="",
                    qty=0,
                    shortage_qty=2,
                    wrong_color_qty=0,
                    wrong_size_qty=0,
                    sellable_qty=0,
                    repair_qty=0,
                    defective_qty=0,
                    frozen_qty=0,
                    qc_note="",
                    exception_note="工厂少发 2 件",
                    remark="",
                ),
                SimpleNamespace(
                    idx=2,
                    item_code="FG-RED-M",
                    item_name="",
                    style="",
                    color_code="",
                    size_code="",
                    qty=3,
                    shortage_qty=0,
                    wrong_color_qty=3,
                    wrong_size_qty=0,
                    sellable_qty=0,
                    repair_qty=0,
                    defective_qty=1,
                    frozen_qty=0,
                    qc_note="",
                    exception_note="整行错色",
                    remark="",
                ),
            ],
        )

        module._normalize_items(doc)
        module._sync_exception_summary(doc)

        self.assertEqual(doc.items[0].item_name, "黑色 M")
        self.assertEqual(doc.items[1].color_code, "RED")
        self.assertEqual(doc.exception_row_count, 2)
        self.assertEqual(doc.total_shortage_qty, 2.0)
        self.assertEqual(doc.total_wrong_color_qty, 3.0)
        self.assertEqual(doc.total_wrong_size_qty, 0.0)
        self.assertEqual(doc.total_defective_qty, 1.0)
        self.assertEqual(doc.exception_summary, "短装 2.0；错色 3.0；次品 1.0")

    def test_normalize_items_rejects_color_mismatch_without_wrong_color_qty(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_receipt_service")
        doc = SimpleNamespace(
            style="ST-001",
            color_code="BLK",
            items=[
                SimpleNamespace(
                    idx=1,
                    item_code="FG-RED-M",
                    item_name="",
                    style="",
                    color_code="",
                    size_code="",
                    qty=2,
                    shortage_qty=0,
                    wrong_color_qty=0,
                    wrong_size_qty=0,
                    sellable_qty=0,
                    repair_qty=0,
                    defective_qty=0,
                    frozen_qty=0,
                    qc_note="",
                    exception_note="",
                    remark="",
                )
            ],
        )

        with self.assertRaisesRegex(self.env.FrappeThrow, "颜色编码与外包单不一致"):
            module._normalize_items(doc)

    def test_validate_qc_result_completion_requires_full_allocation(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_receipt_service")
        doc = SimpleNamespace(
            items=[
                SimpleNamespace(
                    idx=1,
                    qty=10,
                    sellable_qty=7,
                    repair_qty=1,
                    defective_qty=0,
                    frozen_qty=0,
                )
            ]
        )

        with self.assertRaisesRegex(self.env.FrappeThrow, "质检分配数量必须等于到货数量"):
            module._validate_qc_result_completion(doc)

    def test_build_final_stock_entry_items_splits_qc_results_by_target_status(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_receipt_service")
        transition_calls = []

        def build_row_payload(doc, row, **kwargs):
            return {
                "item_code": row.item_code,
                "qty": kwargs["qty"],
                "inventory_status_to": kwargs["inventory_status_to"],
            }

        with patch.object(module, "_build_stock_entry_row_payload", side_effect=build_row_payload), patch.object(
            module,
            "validate_inventory_status_transition",
            side_effect=lambda from_status, to_status, row_label="": transition_calls.append(
                (from_status, to_status, row_label)
            ),
        ):
            doc = SimpleNamespace(
                name="DH-001",
                outsource_order="WB-001",
                warehouse="WH-QC",
                items=[
                    SimpleNamespace(
                        idx=1,
                        item_code="FG-001",
                        qty=10,
                        sellable_qty=8,
                        repair_qty=1,
                        defective_qty=0,
                        frozen_qty=1,
                        style="ST-001",
                        color_code="BLK",
                        size_code="M",
                    )
                ],
            )

            items = module._build_final_stock_entry_items(doc)

        self.assertEqual(
            items,
            [
                {"item_code": "FG-001", "qty": 8, "inventory_status_to": "SELLABLE"},
                {"item_code": "FG-001", "qty": 1, "inventory_status_to": "REPAIR"},
                {"item_code": "FG-001", "qty": 1, "inventory_status_to": "FROZEN"},
            ],
        )
        self.assertEqual(
            transition_calls,
            [
                ("QC_PENDING", "SELLABLE", "到货明细第 1 行"),
                ("QC_PENDING", "REPAIR", "到货明细第 1 行"),
                ("QC_PENDING", "FROZEN", "到货明细第 1 行"),
            ],
        )

    def test_build_qc_stock_entry_items_skips_shortage_only_rows(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_receipt_service")
        transition_calls = []

        def build_row_payload(doc, row, **kwargs):
            return {
                "item_code": row.item_code,
                "qty": kwargs["qty"],
                "inventory_status_to": kwargs["inventory_status_to"],
            }

        with patch.object(module, "_build_stock_entry_row_payload", side_effect=build_row_payload), patch.object(
            module,
            "validate_inventory_status_transition",
            side_effect=lambda from_status, to_status, row_label="": transition_calls.append(
                (from_status, to_status, row_label)
            ),
        ):
            doc = SimpleNamespace(
                name="DH-002",
                outsource_order="WB-001",
                warehouse="WH-QC",
                items=[
                    SimpleNamespace(idx=1, item_code="FG-BLK-M", qty=0, shortage_qty=2),
                    SimpleNamespace(idx=2, item_code="FG-BLK-M", qty=3, shortage_qty=0),
                ],
            )

            items = module._build_qc_stock_entry_items(doc)

        self.assertEqual(
            items,
            [{"item_code": "FG-BLK-M", "qty": 3, "inventory_status_to": "QC_PENDING"}],
        )
        self.assertEqual(
            transition_calls,
            [("", "QC_PENDING", "到货明细第 2 行")],
        )

    def test_outsource_receipt_validation_helpers_reuse_cached_order_location_item_and_user_queries(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.outsource_receipt_service")
        self.env.db.exists_map.update(
            {
                ("Item", "FG-BLK-M"): True,
                ("Style", "ST-001"): True,
                ("User", "checker@example.com"): True,
            }
        )
        self.env.db.value_map.update(
            {
                (
                    "Outsource Order",
                    "WB-001",
                    (
                        "supplier",
                        "style",
                        "style_name",
                        "item_template",
                        "craft_sheet",
                        "sample_ticket",
                        "color",
                        "color_name",
                        "color_code",
                        "receipt_warehouse",
                    ),
                    True,
                ): {
                    "supplier": "SUP-001",
                    "style": "ST-001",
                    "style_name": "连衣裙",
                    "item_template": "IT-TPL-001",
                    "craft_sheet": "CS-001",
                    "sample_ticket": "SMP-001",
                    "color": "COL-BLK",
                    "color_name": "黑色",
                    "color_code": "BLK",
                    "receipt_warehouse": "WH-QC",
                },
                ("Warehouse Location", "QC-A01", "warehouse", False): "WH-QC",
                ("Item", "FG-BLK-M", ("item_name", "item_usage_type", "style", "color_code", "size_code"), True): {
                    "item_name": "黑色 M",
                    "item_usage_type": "成品",
                    "style": "ST-001",
                    "color_code": "BLK",
                    "size_code": "M",
                },
                ("Item", "FG-BLK-M", ("item_name", "stock_uom"), True): {
                    "item_name": "黑色 M",
                    "stock_uom": "Nos",
                },
            }
        )
        self.env.meta_fields["Stock Entry Detail"] = {
            "item_code",
            "item_name",
            "qty",
            "transfer_qty",
            "basic_qty",
            "uom",
            "stock_uom",
            "s_warehouse",
            "t_warehouse",
            "style",
            "color_code",
            "size_code",
            "inventory_status_from",
            "inventory_status_to",
            "outsource_order",
            "outsource_receipt",
        }
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
            name="DH-003",
            outsource_order="WB-001",
            warehouse="",
            warehouse_location="QC-A01",
            style="",
            color_code="",
            items=[
                SimpleNamespace(
                    idx=1,
                    item_code="FG-BLK-M",
                    item_name="",
                    style="",
                    color_code="",
                    size_code="",
                    qty=2,
                    shortage_qty=0,
                    wrong_color_qty=0,
                    wrong_size_qty=0,
                    sellable_qty=0,
                    repair_qty=0,
                    defective_qty=0,
                    frozen_qty=0,
                    qc_note="",
                    exception_note="",
                    remark="",
                ),
                SimpleNamespace(
                    idx=2,
                    item_code="FG-BLK-M",
                    item_name="",
                    style="",
                    color_code="",
                    size_code="",
                    qty=1,
                    shortage_qty=0,
                    wrong_color_qty=0,
                    wrong_size_qty=0,
                    sellable_qty=0,
                    repair_qty=0,
                    defective_qty=0,
                    frozen_qty=0,
                    qc_note="",
                    exception_note="",
                    remark="",
                ),
            ],
            logs=[
                SimpleNamespace(
                    action_time="2026-03-07 12:00:00",
                    action_type="备注",
                    from_status="",
                    to_status="",
                    operator="checker@example.com",
                    note="首次备注",
                ),
                SimpleNamespace(
                    action_time="2026-03-07 12:01:00",
                    action_type="备注",
                    from_status="",
                    to_status="",
                    operator="checker@example.com",
                    note="再次备注",
                ),
            ],
        )

        module._reset_outsource_receipt_validation_cache(doc)
        module._sync_from_order(doc)
        module._sync_from_order(doc)
        module._sync_location_context(doc)
        module._sync_location_context(doc)
        module._normalize_items(doc)
        module._normalize_items(doc)
        module._normalize_logs(doc)
        module._normalize_logs(doc)
        module._build_stock_entry_row_payload(
            doc,
            doc.items[0],
            qty=2,
            s_warehouse="",
            t_warehouse="WH-QC",
            inventory_status_from="",
            inventory_status_to="QC_PENDING",
        )
        module._build_stock_entry_row_payload(
            doc,
            doc.items[1],
            qty=1,
            s_warehouse="WH-QC",
            t_warehouse="WH-FG",
            inventory_status_from="QC_PENDING",
            inventory_status_to="SELLABLE",
        )

        self.assertEqual(doc.supplier, "SUP-001")
        self.assertEqual(doc.style, "ST-001")
        self.assertEqual(doc.warehouse, "WH-QC")
        self.assertEqual(doc.items[0].item_name, "黑色 M")
        self.assertEqual(doc.items[1].size_code, "M")
        self.assertEqual(
            lookup_counter[
                (
                    "Outsource Order",
                    "WB-001",
                    (
                        "supplier",
                        "style",
                        "style_name",
                        "item_template",
                        "craft_sheet",
                        "sample_ticket",
                        "color",
                        "color_name",
                        "color_code",
                        "receipt_warehouse",
                    ),
                    True,
                )
            ],
            1,
        )
        self.assertEqual(lookup_counter[("Warehouse Location", "QC-A01", "warehouse", False)], 1)
        self.assertEqual(
            lookup_counter[
                ("Item", "FG-BLK-M", ("item_name", "item_usage_type", "style", "color_code", "size_code"), True)
            ],
            1,
        )
        self.assertEqual(lookup_counter[("Item", "FG-BLK-M", ("item_name", "stock_uom"), True)], 1)
        self.assertEqual(exists_counter[("Item", "FG-BLK-M")], 1)
        self.assertEqual(exists_counter[("Style", "ST-001")], 1)
        self.assertEqual(exists_counter[("User", "checker@example.com")], 1)


if __name__ == "__main__":
    unittest.main()
