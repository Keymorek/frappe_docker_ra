from __future__ import annotations

import unittest
from collections import Counter
from types import SimpleNamespace

from helpers import FakeDoc, build_frappe_env


class TestOrderSyncService(unittest.TestCase):
    def setUp(self):
        self.env = build_frappe_env()
        self.env.db.exists_map.update(
            {
                ("Channel Store", "STORE-01"): True,
                ("Company", "COMP-01"): True,
                ("Customer", "CUST-01"): True,
                ("Warehouse", "WH-01"): True,
                ("Price List", "PL-01"): True,
                ("Item", "SKU-001"): True,
                ("Item", "SKU-002"): True,
            }
        )
        self.env.db.value_map[
            ("Channel Store", "STORE-01", ("channel", "warehouse", "price_list", "default_company", "default_customer", "status"), True)
        ] = {
            "channel": "抖音",
            "warehouse": "WH-01",
            "price_list": "PL-01",
            "default_company": "COMP-01",
            "default_customer": "CUST-01",
            "status": "启用",
        }

    def tearDown(self):
        self.env.cleanup()

    def test_validate_order_sync_batch_applies_store_defaults_and_stats(self):
        module = self.env.load_module("fashion_erp.channel.services.order_sync_service")
        doc = FakeDoc(
            name="New Order Sync Batch 1",
            batch_no="",
            channel_store="STORE-01",
            channel="",
            default_company="",
            default_customer="",
            default_warehouse="",
            default_price_list="",
            template_version="",
            batch_status="",
            source_file_name="orders.xlsx",
            source_hash="abc123",
            remark="",
            items=[
                SimpleNamespace(
                    row_no="",
                    external_order_id="EXT-001",
                    line_no="1",
                    order_date="2026-03-08",
                    customer="",
                    item_code="SKU-001",
                    platform_sku="PLAT-001",
                    qty="2",
                    rate="99",
                    biz_type="",
                    delivery_date="",
                    warehouse="",
                    row_status="",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
                SimpleNamespace(
                    row_no="",
                    external_order_id="EXT-002",
                    line_no="2",
                    order_date="2026-03-08",
                    customer="",
                    item_code="",
                    platform_sku="PLAT-002",
                    qty="1",
                    rate="59",
                    biz_type="零售",
                    delivery_date="",
                    warehouse="",
                    row_status="",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
            ],
        )

        module.validate_order_sync_batch(doc)

        self.assertEqual(doc.channel, "抖音")
        self.assertEqual(doc.default_company, "COMP-01")
        self.assertEqual(doc.default_customer, "CUST-01")
        self.assertEqual(doc.default_warehouse, "WH-01")
        self.assertEqual(doc.default_price_list, "PL-01")
        self.assertEqual(doc.template_version, "V1")
        self.assertEqual(doc.total_rows, 2)
        self.assertEqual(doc.valid_rows, 1)
        self.assertEqual(doc.failed_rows, 1)
        self.assertEqual(doc.batch_status, "待导入")
        self.assertEqual(doc.items[0].row_status, "待导入")
        self.assertEqual(doc.items[0].warehouse, "WH-01")
        self.assertEqual(doc.items[0].customer, "CUST-01")
        self.assertEqual(doc.items[1].row_status, "校验失败")
        self.assertIn("SKU不能为空", doc.items[1].message)

    def test_validate_order_sync_batch_reuses_cached_link_checks_for_repeated_rows(self):
        module = self.env.load_module("fashion_erp.channel.services.order_sync_service")
        exists_counter = Counter()
        original_exists = self.env.db.exists

        def counting_exists(doctype, name):
            exists_counter[(doctype, name)] += 1
            return original_exists(doctype, name)

        self.env.db.exists = counting_exists
        doc = FakeDoc(
            name="New Order Sync Batch 2",
            batch_no="",
            channel_store="STORE-01",
            channel="",
            default_company="",
            default_customer="",
            default_warehouse="",
            default_price_list="",
            template_version="",
            batch_status="",
            source_file_name="orders.xlsx",
            source_hash="abc123",
            remark="",
            items=[
                SimpleNamespace(
                    row_no="",
                    external_order_id="EXT-100",
                    line_no="1",
                    order_date="2026-03-08",
                    customer="",
                    item_code="SKU-001",
                    platform_sku="PLAT-001",
                    qty="1",
                    rate="99",
                    biz_type="",
                    delivery_date="",
                    warehouse="",
                    row_status="",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
                SimpleNamespace(
                    row_no="",
                    external_order_id="EXT-101",
                    line_no="2",
                    order_date="2026-03-08",
                    customer="",
                    item_code="SKU-001",
                    platform_sku="PLAT-001",
                    qty="2",
                    rate="99",
                    biz_type="",
                    delivery_date="",
                    warehouse="",
                    row_status="",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
            ],
        )

        module.validate_order_sync_batch(doc)

        self.assertEqual(exists_counter[("Channel Store", "STORE-01")], 1)
        self.assertEqual(exists_counter[("Company", "COMP-01")], 1)
        self.assertEqual(exists_counter[("Customer", "CUST-01")], 1)
        self.assertEqual(exists_counter[("Warehouse", "WH-01")], 1)
        self.assertEqual(exists_counter[("Price List", "PL-01")], 1)
        self.assertEqual(exists_counter[("Item", "SKU-001")], 1)

    def test_load_order_sync_batch_csv_replaces_rows_and_generates_source_hash(self):
        module = self.env.load_module("fashion_erp.channel.services.order_sync_service")
        batch_doc = FakeDoc(
            doctype="Order Sync Batch",
            name="OSB-0003",
            batch_no="OSB-0003",
            channel_store="STORE-01",
            channel="",
            default_company="",
            default_customer="",
            default_warehouse="",
            default_price_list="",
            template_version="V1",
            batch_status="草稿",
            source_file_name="",
            source_hash="",
            remark="",
            items=[
                SimpleNamespace(
                    row_no=1,
                    external_order_id="OLD-001",
                    line_no="1",
                    order_date="2026-03-07",
                    customer="CUST-01",
                    item_code="SKU-001",
                    platform_sku="",
                    qty=1,
                    rate=10,
                    biz_type="零售",
                    delivery_date="2026-03-07",
                    warehouse="WH-01",
                    row_status="草稿",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                )
            ],
        )
        self.env.get_doc_handler = lambda doctype, name=None: batch_doc if (doctype, name) == ("Order Sync Batch", "OSB-0003") else None
        csv_content = (
            "external_order_id,order_date,item_code,qty,rate,biz_type,delivery_date,warehouse,platform_sku,line_no,customer\n"
            "EXT-CSV-001,2026-03-08,SKU-001,2,199,零售,2026-03-09,WH-01,PLAT-001,1,CUST-01\n"
        )

        payload = module.load_order_sync_batch_csv(
            "OSB-0003",
            csv_content=csv_content,
            source_file_name="orders.csv",
            replace_existing=1,
        )

        self.assertEqual(payload["loaded_rows"], 1)
        self.assertEqual(batch_doc.source_file_name, "orders.csv")
        self.assertTrue(batch_doc.source_hash)
        self.assertEqual(len(batch_doc.items), 1)
        self.assertEqual(batch_doc.items[0].external_order_id, "EXT-CSV-001")
        self.assertEqual(batch_doc.items[0].row_status, "待导入")

    def test_load_order_sync_batch_csv_appends_rows(self):
        module = self.env.load_module("fashion_erp.channel.services.order_sync_service")
        batch_doc = FakeDoc(
            doctype="Order Sync Batch",
            name="OSB-0004",
            batch_no="OSB-0004",
            channel_store="STORE-01",
            channel="",
            default_company="",
            default_customer="",
            default_warehouse="",
            default_price_list="",
            template_version="V1",
            batch_status="草稿",
            source_file_name="",
            source_hash="",
            remark="",
            items=[
                SimpleNamespace(
                    row_no=1,
                    external_order_id="EXT-OLD-001",
                    line_no="1",
                    order_date="2026-03-07",
                    customer="CUST-01",
                    item_code="SKU-001",
                    platform_sku="",
                    qty=1,
                    rate=10,
                    biz_type="零售",
                    delivery_date="2026-03-07",
                    warehouse="WH-01",
                    row_status="待导入",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                )
            ],
        )
        self.env.get_doc_handler = lambda doctype, name=None: batch_doc if (doctype, name) == ("Order Sync Batch", "OSB-0004") else None
        csv_content = (
            "external_order_id,order_date,item_code,qty,rate,biz_type,delivery_date,warehouse,platform_sku,line_no,customer\n"
            "EXT-NEW-001,2026-03-08,SKU-002,2,59,零售,2026-03-10,WH-01,PLAT-002,2,CUST-01\n"
        )

        module.load_order_sync_batch_csv(
            "OSB-0004",
            csv_content=csv_content,
            source_file_name="orders.csv",
            replace_existing=0,
        )

        self.assertEqual(len(batch_doc.items), 2)
        self.assertEqual(batch_doc.items[0].external_order_id, "EXT-OLD-001")
        self.assertEqual(batch_doc.items[1].external_order_id, "EXT-NEW-001")
        self.assertEqual(batch_doc.items[1].row_no, 2)

    def test_load_order_sync_batch_csv_requires_required_headers(self):
        module = self.env.load_module("fashion_erp.channel.services.order_sync_service")
        batch_doc = FakeDoc(
            doctype="Order Sync Batch",
            name="OSB-0005",
            batch_no="OSB-0005",
            channel_store="STORE-01",
            channel="",
            default_company="",
            default_customer="",
            default_warehouse="",
            default_price_list="",
            template_version="V1",
            batch_status="草稿",
            source_file_name="",
            source_hash="",
            remark="",
            items=[],
        )
        self.env.get_doc_handler = lambda doctype, name=None: batch_doc if (doctype, name) == ("Order Sync Batch", "OSB-0005") else None
        csv_content = "external_order_id,order_date,qty\nEXT-1,2026-03-08,1\n"

        with self.assertRaisesRegex(self.env.FrappeThrow, "缺少必要列"):
            module.load_order_sync_batch_csv(
                "OSB-0005",
                csv_content=csv_content,
                source_file_name="orders.csv",
                replace_existing=1,
            )

    def test_summarize_order_sync_batch_counts_imported_and_duplicates_by_order(self):
        module = self.env.load_module("fashion_erp.channel.services.order_sync_service")
        doc = FakeDoc(
            items=[
                SimpleNamespace(external_order_id="EXT-001", row_status="已导入"),
                SimpleNamespace(external_order_id="EXT-001", row_status="已导入"),
                SimpleNamespace(external_order_id="EXT-002", row_status="重复跳过"),
                SimpleNamespace(external_order_id="EXT-003", row_status="校验失败"),
                SimpleNamespace(external_order_id="EXT-004", row_status="待导入"),
            ]
        )

        stats = module.summarize_order_sync_batch(doc)

        self.assertEqual(stats["total_rows"], 5)
        self.assertEqual(stats["valid_rows"], 4)
        self.assertEqual(stats["failed_rows"], 1)
        self.assertEqual(stats["imported_rows"], 2)
        self.assertEqual(stats["duplicate_rows"], 1)
        self.assertEqual(stats["pending_rows"], 1)
        self.assertEqual(stats["imported_orders"], 1)
        self.assertEqual(stats["duplicate_orders"], 1)

    def test_preview_order_sync_batch_marks_duplicates_and_conflicts(self):
        module = self.env.load_module("fashion_erp.channel.services.order_sync_service")
        batch_doc = FakeDoc(
            doctype="Order Sync Batch",
            name="OSB-0001",
            batch_no="OSB-0001",
            channel_store="STORE-01",
            channel="",
            default_company="",
            default_customer="",
            default_warehouse="",
            default_price_list="",
            template_version="V1",
            batch_status="草稿",
            source_file_name="orders.xlsx",
            source_hash="hash",
            remark="",
            items=[
                SimpleNamespace(
                    row_no=1,
                    external_order_id="EXT-DUP",
                    line_no="1",
                    order_date="2026-03-08",
                    customer="CUST-01",
                    item_code="SKU-001",
                    platform_sku="",
                    qty=1,
                    rate=99,
                    biz_type="零售",
                    delivery_date="2026-03-08",
                    warehouse="WH-01",
                    row_status="草稿",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
                SimpleNamespace(
                    row_no=2,
                    external_order_id="EXT-CONFLICT",
                    line_no="1",
                    order_date="2026-03-08",
                    customer="CUST-01",
                    item_code="SKU-001",
                    platform_sku="",
                    qty=1,
                    rate=99,
                    biz_type="零售",
                    delivery_date="2026-03-08",
                    warehouse="WH-01",
                    row_status="草稿",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
                SimpleNamespace(
                    row_no=3,
                    external_order_id="EXT-CONFLICT",
                    line_no="2",
                    order_date="2026-03-08",
                    customer="CUST-ALT",
                    item_code="SKU-002",
                    platform_sku="",
                    qty=1,
                    rate=59,
                    biz_type="零售",
                    delivery_date="2026-03-08",
                    warehouse="WH-01",
                    row_status="草稿",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
                SimpleNamespace(
                    row_no=4,
                    external_order_id="EXT-OK",
                    line_no="1",
                    order_date="2026-03-08",
                    customer="CUST-01",
                    item_code="SKU-002",
                    platform_sku="",
                    qty=1,
                    rate=59,
                    biz_type="零售",
                    delivery_date="2026-03-08",
                    warehouse="WH-01",
                    row_status="草稿",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
            ],
        )
        self.env.db.exists_map[("Customer", "CUST-ALT")] = True
        self.env.get_doc_handler = lambda doctype, name=None: batch_doc if (doctype, name) == ("Order Sync Batch", "OSB-0001") else None
        self.env.get_all_handler = lambda doctype, **kwargs: (
            [{"name": "SO-DUP-001", "external_order_id": "EXT-DUP"}] if doctype == "Sales Order" else []
        )

        payload = module.preview_order_sync_batch("OSB-0001")

        self.assertEqual(payload["batch_status"], "待导入")
        self.assertEqual(batch_doc.items[0].row_status, "重复跳过")
        self.assertEqual(batch_doc.items[0].sales_order, "SO-DUP-001")
        self.assertEqual(batch_doc.items[1].row_status, "校验失败")
        self.assertEqual(batch_doc.items[2].row_status, "校验失败")
        self.assertEqual(batch_doc.items[3].row_status, "待导入")
        self.assertEqual(batch_doc.duplicate_orders, 1)
        self.assertEqual(batch_doc.failed_rows, 2)
        self.assertEqual(len(batch_doc.save_calls), 1)

    def test_execute_order_sync_batch_creates_sales_orders_and_links_rows(self):
        module = self.env.load_module("fashion_erp.channel.services.order_sync_service")
        self.env.meta_fields["Sales Order"] = {
            "company",
            "customer",
            "transaction_date",
            "delivery_date",
            "channel",
            "channel_store",
            "selling_price_list",
            "set_warehouse",
            "external_order_id",
            "biz_type",
            "remarks",
            "items",
        }
        self.env.meta_fields["Sales Order Item"] = {
            "item_code",
            "qty",
            "rate",
            "delivery_date",
            "warehouse",
            "platform_sku",
            "style",
            "color_code",
            "color_name",
            "size_code",
            "size_name",
        }
        batch_doc = FakeDoc(
            doctype="Order Sync Batch",
            name="OSB-0002",
            batch_no="OSB-0002",
            channel_store="STORE-01",
            channel="",
            default_company="",
            default_customer="",
            default_warehouse="",
            default_price_list="",
            template_version="V1",
            batch_status="草稿",
            source_file_name="orders.xlsx",
            source_hash="hash",
            remark="",
            last_import_at=None,
            items=[
                SimpleNamespace(
                    row_no=1,
                    external_order_id="EXT-NEW",
                    line_no="1",
                    order_date="2026-03-08",
                    customer="CUST-01",
                    item_code="SKU-001",
                    platform_sku="PLAT-001",
                    qty=1,
                    rate=99,
                    biz_type="零售",
                    delivery_date="2026-03-09",
                    warehouse="WH-01",
                    row_status="草稿",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
                SimpleNamespace(
                    row_no=2,
                    external_order_id="EXT-NEW",
                    line_no="2",
                    order_date="2026-03-08",
                    customer="CUST-01",
                    item_code="SKU-002",
                    platform_sku="PLAT-002",
                    qty=2,
                    rate=59,
                    biz_type="零售",
                    delivery_date="2026-03-10",
                    warehouse="WH-01",
                    row_status="草稿",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
            ],
        )
        self.env.db.value_map[("Item", "SKU-001", ("style", "color_code", "color_name", "size_code", "size_name"), True)] = {
            "style": "ST-001",
            "color_code": "BLK",
            "color_name": "黑色",
            "size_code": "S",
            "size_name": "S",
        }
        self.env.db.value_map[("Item", "SKU-002", ("style", "color_code", "color_name", "size_code", "size_name"), True)] = {
            "style": "ST-001",
            "color_code": "BLK",
            "color_name": "黑色",
            "size_code": "M",
            "size_name": "M",
        }
        self.env.get_all_handler = lambda doctype, **kwargs: []
        created_docs = []

        def get_doc(arg1, arg2=None):
            if isinstance(arg1, dict):
                payload = dict(arg1)
                payload.pop("doctype", None)
                items = [FakeDoc(**item) for item in payload.pop("items", [])]
                doc = FakeDoc(doctype="Sales Order", name="SO-NEW-001", items=items, **payload)

                def insert(ignore_permissions=False, *, _doc=doc):
                    created_docs.append(_doc)
                    _doc.insert_calls.append({"ignore_permissions": ignore_permissions})
                    for index, row in enumerate(_doc.items, start=1):
                        row.name = f"SOI-{index:03d}"
                    return _doc

                doc.insert = insert
                return doc

            if (arg1, arg2) == ("Order Sync Batch", "OSB-0002"):
                return batch_doc
            raise KeyError((arg1, arg2))

        self.env.get_doc_handler = get_doc

        payload = module.execute_order_sync_batch("OSB-0002")

        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["created_orders"], ["SO-NEW-001"])
        self.assertEqual(batch_doc.batch_status, "已完成")
        self.assertIsNotNone(batch_doc.last_import_at)
        self.assertEqual(batch_doc.items[0].row_status, "已导入")
        self.assertEqual(batch_doc.items[1].row_status, "已导入")
        self.assertEqual(batch_doc.items[0].sales_order_item_ref, "SOI-001")
        self.assertEqual(batch_doc.items[1].sales_order_item_ref, "SOI-002")
        self.assertEqual(created_docs[0].customer, "CUST-01")
        self.assertEqual(created_docs[0].external_order_id, "EXT-NEW")
        self.assertEqual(created_docs[0].selling_price_list, "PL-01")
        self.assertEqual(created_docs[0].items[0].style, "ST-001")
        self.assertEqual(created_docs[0].items[1].size_code, "M")

    def test_build_sales_order_payload_reuses_cached_item_values_for_duplicate_skus(self):
        module = self.env.load_module("fashion_erp.channel.services.order_sync_service")
        self.env.meta_fields["Sales Order"] = {
            "company",
            "customer",
            "transaction_date",
            "delivery_date",
            "channel",
            "channel_store",
            "selling_price_list",
            "set_warehouse",
            "external_order_id",
            "biz_type",
            "remarks",
            "items",
        }
        self.env.meta_fields["Sales Order Item"] = {
            "item_code",
            "qty",
            "rate",
            "delivery_date",
            "warehouse",
            "platform_sku",
            "style",
            "color_code",
            "color_name",
            "size_code",
            "size_name",
        }
        lookup_counter = Counter()
        original_get_value = self.env.db.get_value

        def counting_get_value(doctype, name, fieldname, as_dict=False):
            frozen_field = tuple(fieldname) if isinstance(fieldname, list) else fieldname
            lookup_counter[(doctype, name, frozen_field, as_dict)] += 1
            return original_get_value(doctype, name, fieldname, as_dict=as_dict)

        self.env.db.get_value = counting_get_value
        self.env.db.value_map[("Item", "SKU-001", ("style", "color_code", "color_name", "size_code", "size_name"), True)] = {
            "style": "ST-001",
            "color_code": "BLK",
            "color_name": "黑色",
            "size_code": "S",
            "size_name": "S",
        }
        doc = FakeDoc(
            name="OSB-0100",
            batch_no="OSB-0100",
            channel_store="STORE-01",
            channel="抖音",
            default_company="COMP-01",
            default_customer="CUST-01",
            default_warehouse="WH-01",
            default_price_list="PL-01",
            template_version="V1",
            batch_status="待导入",
            source_file_name="orders.xlsx",
            source_hash="hash",
            remark="",
            items=[
                SimpleNamespace(
                    row_no=1,
                    external_order_id="EXT-200",
                    line_no="1",
                    order_date="2026-03-08",
                    customer="CUST-01",
                    item_code="SKU-001",
                    platform_sku="PLAT-001",
                    qty=1,
                    rate=99,
                    biz_type="零售",
                    delivery_date="2026-03-09",
                    warehouse="WH-01",
                    row_status="待导入",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
                SimpleNamespace(
                    row_no=2,
                    external_order_id="EXT-200",
                    line_no="2",
                    order_date="2026-03-08",
                    customer="CUST-01",
                    item_code="SKU-001",
                    platform_sku="PLAT-001",
                    qty=2,
                    rate=99,
                    biz_type="零售",
                    delivery_date="2026-03-10",
                    warehouse="WH-01",
                    row_status="待导入",
                    sales_order="",
                    sales_order_item_ref="",
                    message="",
                ),
            ],
        )

        module.validate_order_sync_batch(doc)
        group = module._build_order_groups(doc)[0]
        payload = module._build_sales_order_payload(doc, group)

        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["items"][0]["style"], "ST-001")
        self.assertEqual(
            lookup_counter[
                ("Item", "SKU-001", ("style", "color_code", "color_name", "size_code", "size_name"), True)
            ],
            1,
        )

    def test_autoname_order_sync_batch_sets_batch_no(self):
        module = self.env.load_module("fashion_erp.channel.services.order_sync_service")
        doc = FakeDoc(name="New Order Sync Batch 1", batch_no="")

        module.autoname_order_sync_batch(doc)

        self.assertEqual(doc.name, "OSB-0001")
        self.assertEqual(doc.batch_no, "OSB-0001")


if __name__ == "__main__":
    unittest.main()
