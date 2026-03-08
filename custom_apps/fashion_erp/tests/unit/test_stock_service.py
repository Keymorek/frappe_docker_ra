from __future__ import annotations

import unittest
from unittest.mock import patch

from helpers import build_frappe_env


class TestStockService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_validate_inventory_status_transition_allows_qc_pending_entry(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.stock_service")
        calls = []

        def record_enabled_link(doctype, name, enabled_field="enabled"):
            if name:
                calls.append((doctype, name, enabled_field))

        with patch.object(module, "ensure_enabled_link", side_effect=record_enabled_link):
            module.validate_inventory_status_transition("", "QC_PENDING", row_label="到货明细第 1 行")

        self.assertEqual(calls, [("Inventory Status", "QC_PENDING", "enabled")])

    def test_validate_inventory_status_transition_rejects_invalid_initial_status(self):
        module = self.env.load_module("fashion_erp.fashion_stock.services.stock_service")

        with patch.object(module, "ensure_enabled_link", return_value=None):
            with self.assertRaisesRegex(self.env.FrappeThrow, "不能作为入库初始状态"):
                module.validate_inventory_status_transition("", "RESERVED")


if __name__ == "__main__":
    unittest.main()
