from __future__ import annotations

import unittest

from helpers import build_frappe_env


class TestSalesOrderIndexPatch(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()
        self.env.db.exists_map[("DocType", "Sales Order")] = True
        self.env.meta_fields["Sales Order"] = {"channel_store", "external_order_id"}

    def tearDown(self):
        self.env.cleanup()

    def test_patch_skips_when_target_index_exists(self):
        module = self.env.load_module(
            "fashion_erp.patches.v1_3.add_sales_order_external_order_index"
        )
        self.env.db.sql_result = [
            {
                "Key_name": "idx_sales_order_channel_store_external_order_id",
                "Seq_in_index": 1,
                "Column_name": "channel_store",
            },
            {
                "Key_name": "idx_sales_order_channel_store_external_order_id",
                "Seq_in_index": 2,
                "Column_name": "external_order_id",
            },
        ]

        module.execute()

        self.assertEqual(len(self.env.db.sql_calls), 1)
        self.assertIn("SHOW INDEX", self.env.db.sql_calls[0][0][0])

    def test_patch_adds_index_when_missing(self):
        module = self.env.load_module(
            "fashion_erp.patches.v1_3.add_sales_order_external_order_index"
        )
        self.env.db.sql_result = []

        module.execute()

        self.assertEqual(len(self.env.db.sql_calls), 2)
        self.assertIn("SHOW INDEX", self.env.db.sql_calls[0][0][0])
        self.assertIn(
            "ADD INDEX `idx_sales_order_channel_store_external_order_id`",
            self.env.db.sql_calls[1][0][0],
        )


if __name__ == "__main__":
    unittest.main()
