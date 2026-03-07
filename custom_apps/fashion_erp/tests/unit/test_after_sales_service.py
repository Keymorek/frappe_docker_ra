from __future__ import annotations

import unittest
from types import SimpleNamespace

from helpers import build_frappe_env


class TestAfterSalesService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()

    def tearDown(self):
        self.env.cleanup()

    def test_determine_after_sales_decision_status_maps_ticket_types(self):
        module = self.env.load_module("fashion_erp.stock.services.after_sales_service")

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


if __name__ == "__main__":
    unittest.main()
