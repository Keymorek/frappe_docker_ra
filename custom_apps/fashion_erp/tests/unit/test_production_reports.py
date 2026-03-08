from __future__ import annotations

import unittest
from unittest.mock import patch

from helpers import build_frappe_env


class TestProductionReports(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_production_board_returns_rows_summary_and_chart(self):
        module = self.env.load_module("fashion_erp.garment_mfg.report.production_board.production_board")

        def get_all(doctype, **kwargs):
            if doctype == "Production Ticket":
                return [
                    {
                        "name": "PT-001",
                        "style": "ST-001",
                        "color_code": "BLK",
                        "qty": 12,
                        "stage": "车缝",
                        "status": "进行中",
                        "planned_start_date": "2026-03-01",
                        "planned_end_date": "2026-03-06",
                        "actual_start_date": "2026-03-02",
                        "actual_end_date": "",
                        "defect_qty": 1,
                        "bom_no": "BOM-001",
                        "work_order": "WO-001",
                        "supplier": "SUP-001",
                    },
                    {
                        "name": "PT-002",
                        "style": "ST-002",
                        "color_code": "WHT",
                        "qty": 8,
                        "stage": "完成",
                        "status": "已完成",
                        "planned_start_date": "2026-03-05",
                        "planned_end_date": "2026-03-08",
                        "actual_start_date": "2026-03-05",
                        "actual_end_date": "2026-03-08",
                        "defect_qty": 0,
                        "bom_no": "",
                        "work_order": "",
                        "supplier": "",
                    },
                ]
            if doctype == "Production Stage Log":
                return [
                    {
                        "parent": "PT-001",
                        "stage": "裁剪",
                        "qty_out": 10,
                        "log_time": "2026-03-05 09:00:00",
                    },
                    {
                        "parent": "PT-001",
                        "stage": "车缝",
                        "qty_out": 9,
                        "log_time": "2026-03-06 18:00:00",
                    },
                    {
                        "parent": "PT-002",
                        "stage": "完成",
                        "qty_out": 8,
                        "log_time": "2026-03-08 20:00:00",
                    },
                ]
            if doctype == "Stock Entry Detail":
                return [
                    {"parent": "STE-001", "production_ticket": "PT-001"},
                    {"parent": "STE-002", "production_ticket": "PT-001"},
                    {"parent": "STE-003", "production_ticket": "PT-002"},
                    {"parent": "STE-003", "production_ticket": "PT-002"},
                ]
            if doctype == "Stock Entry":
                return [
                    {
                        "name": "STE-001",
                        "stock_entry_type": "Material Receipt",
                        "purpose": "Material Receipt",
                        "posting_date": "2026-03-05",
                        "posting_time": "09:00:00",
                        "docstatus": 1,
                    },
                    {
                        "name": "STE-002",
                        "stock_entry_type": "Material Transfer for Manufacture",
                        "purpose": "Material Transfer for Manufacture",
                        "posting_date": "2026-03-07",
                        "posting_time": "11:00:00",
                        "docstatus": 1,
                    },
                    {
                        "name": "STE-003",
                        "stock_entry_type": "Material Receipt",
                        "purpose": "Material Receipt",
                        "posting_date": "2026-03-08",
                        "posting_time": "12:00:00",
                        "docstatus": 2,
                    },
                ]
            return []

        self.env.get_all_handler = get_all

        with patch.object(module, "nowdate", return_value="2026-03-08"):
            columns, data, _, chart, summary = module.execute({"style": "ST-001"})

        self.assertEqual(columns[0]["fieldname"], "production_ticket")
        self.assertEqual(data[0]["production_ticket"], "PT-001")
        self.assertEqual(data[0]["schedule_status"], "已逾期")
        self.assertEqual(data[0]["delay_days"], 2)
        self.assertEqual(data[0]["progress_percent"], 40.0)
        self.assertEqual(data[0]["stage_log_count"], 2)
        self.assertEqual(data[0]["last_log_stage"], "车缝")
        self.assertEqual(data[0]["last_qty_out"], 9.0)
        self.assertEqual(data[0]["stock_entry_count"], 2)
        self.assertEqual(data[0]["latest_stock_entry"], "STE-002")
        self.assertEqual(data[0]["latest_stock_entry_type"], "Material Transfer for Manufacture")
        summary_by_label = {item["label"]: item["value"] for item in summary}
        self.assertEqual(summary_by_label["生产卡数"], 2)
        self.assertEqual(summary_by_label["延期卡数"], 1)
        self.assertEqual(summary_by_label["已联动库存"], 1)
        self.assertEqual(chart["data"]["labels"], ["计划", "裁剪", "车缝", "后整", "包装", "完成"])
        self.assertEqual(chart["data"]["datasets"][0]["values"], [0, 0, 1, 0, 0, 1])

    def test_production_board_supports_only_open_and_only_overdue_filters(self):
        module = self.env.load_module("fashion_erp.garment_mfg.report.production_board.production_board")

        def get_all(doctype, **kwargs):
            if doctype == "Production Ticket":
                return [
                    {
                        "name": "PT-001",
                        "style": "ST-001",
                        "color_code": "BLK",
                        "qty": 12,
                        "stage": "车缝",
                        "status": "进行中",
                        "planned_start_date": "2026-03-01",
                        "planned_end_date": "2026-03-06",
                        "actual_start_date": "2026-03-02",
                        "actual_end_date": "",
                        "defect_qty": 1,
                        "bom_no": "",
                        "work_order": "",
                        "supplier": "",
                    },
                    {
                        "name": "PT-002",
                        "style": "ST-002",
                        "color_code": "WHT",
                        "qty": 8,
                        "stage": "完成",
                        "status": "已完成",
                        "planned_start_date": "2026-03-05",
                        "planned_end_date": "2026-03-06",
                        "actual_start_date": "2026-03-05",
                        "actual_end_date": "2026-03-08",
                        "defect_qty": 0,
                        "bom_no": "",
                        "work_order": "",
                        "supplier": "",
                    },
                ]
            return []

        self.env.get_all_handler = get_all

        with patch.object(module, "nowdate", return_value="2026-03-08"):
            _, data, _, _, summary = module.execute({"only_open": 1, "only_overdue": 1})

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["production_ticket"], "PT-001")
        self.assertEqual(summary[0]["value"], 1)


if __name__ == "__main__":
    unittest.main()
