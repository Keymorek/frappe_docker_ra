from __future__ import annotations

import csv
import hashlib
import io

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import getdate, now_datetime

from fashion_erp.style.services.style_service import (
    coerce_non_negative_float,
    ensure_link_exists,
    normalize_select,
    normalize_text,
)


ORDER_SYNC_TEMPLATE_VERSIONS = ("V1",)
ORDER_SYNC_BATCH_STATUSES = ("草稿", "待校验", "待导入", "部分导入", "已完成", "已取消")
ORDER_SYNC_BATCH_STATUS_ALIASES = {
    "Draft": "草稿",
    "Pending Review": "待校验",
    "Ready": "待导入",
    "Partial": "部分导入",
    "Completed": "已完成",
    "Cancelled": "已取消",
}
ORDER_SYNC_ROW_STATUSES = ("草稿", "待导入", "已导入", "重复跳过", "校验失败")
ORDER_SYNC_ROW_STATUS_ALIASES = {
    "Draft": "草稿",
    "Ready": "待导入",
    "Imported": "已导入",
    "Skipped Duplicate": "重复跳过",
    "Failed": "校验失败",
}
ORDER_SYNC_BIZ_TYPES = ("零售", "批发", "预售", "换货")
ORDER_SYNC_BIZ_TYPE_ALIASES = {
    "Retail": "零售",
    "Wholesale": "批发",
    "Presale": "预售",
    "Exchange": "换货",
}
ORDER_SYNC_CSV_FIELDS = (
    ("external_order_id", True),
    ("order_date", True),
    ("item_code", True),
    ("qty", True),
    ("rate", False),
    ("biz_type", False),
    ("delivery_date", False),
    ("warehouse", False),
    ("platform_sku", False),
    ("line_no", False),
    ("customer", False),
)


def autoname_order_sync_batch(doc) -> None:
    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.batch_no = doc.name
        return

    prefix = "OSB-"
    batch_no = make_autoname(f"{prefix}####")
    doc.name = batch_no
    doc.batch_no = batch_no


def validate_order_sync_batch(doc) -> None:
    _reset_order_sync_cache(doc)
    doc.batch_no = normalize_text(getattr(doc, "batch_no", None))
    doc.channel_store = normalize_text(getattr(doc, "channel_store", None))
    doc.channel = normalize_text(getattr(doc, "channel", None))
    doc.default_company = normalize_text(getattr(doc, "default_company", None))
    doc.default_customer = normalize_text(getattr(doc, "default_customer", None))
    doc.default_warehouse = normalize_text(getattr(doc, "default_warehouse", None))
    doc.default_price_list = normalize_text(getattr(doc, "default_price_list", None))
    doc.template_version = normalize_select(
        getattr(doc, "template_version", None),
        "模板版本",
        ORDER_SYNC_TEMPLATE_VERSIONS,
        default="V1",
    )
    doc.batch_status = normalize_select(
        getattr(doc, "batch_status", None),
        "批次状态",
        ORDER_SYNC_BATCH_STATUSES,
        default="草稿",
        alias_map=ORDER_SYNC_BATCH_STATUS_ALIASES,
    )
    doc.source_file_name = normalize_text(getattr(doc, "source_file_name", None))
    doc.source_hash = normalize_text(getattr(doc, "source_hash", None))
    doc.remark = normalize_text(getattr(doc, "remark", None))

    _sync_from_channel_store(doc)

    _ensure_cached_link_exists(doc, "Company", doc.default_company)
    _ensure_cached_link_exists(doc, "Customer", doc.default_customer)
    _ensure_cached_link_exists(doc, "Warehouse", doc.default_warehouse)
    _ensure_cached_link_exists(doc, "Price List", doc.default_price_list)

    _normalize_batch_rows(doc)
    _sync_batch_status(doc)


def get_channel_store_defaults(store_name: str) -> dict[str, str]:
    store_name = normalize_text(store_name)
    ensure_link_exists("Channel Store", store_name)
    row = frappe.db.get_value(
        "Channel Store",
        store_name,
        ["channel", "warehouse", "price_list", "default_company", "default_customer", "status"],
        as_dict=True,
    )
    return {
        "channel": normalize_text((row or {}).get("channel")),
        "warehouse": normalize_text((row or {}).get("warehouse")),
        "price_list": normalize_text((row or {}).get("price_list")),
        "default_company": normalize_text((row or {}).get("default_company")),
        "default_customer": normalize_text((row or {}).get("default_customer")),
        "status": normalize_text((row or {}).get("status")),
    }


def summarize_order_sync_batch(doc) -> dict[str, int]:
    stats = {
        "total_rows": 0,
        "valid_rows": 0,
        "failed_rows": 0,
        "imported_rows": 0,
        "duplicate_rows": 0,
        "pending_rows": 0,
        "imported_orders": 0,
        "duplicate_orders": 0,
    }
    imported_orders: set[str] = set()
    duplicate_orders: set[str] = set()

    for row in list(getattr(doc, "items", None) or []):
        status = normalize_text(getattr(row, "row_status", None))
        order_key = normalize_text(getattr(row, "external_order_id", None))
        stats["total_rows"] += 1

        if status == "校验失败":
            stats["failed_rows"] += 1
            continue

        stats["valid_rows"] += 1
        if status == "已导入":
            stats["imported_rows"] += 1
            if order_key:
                imported_orders.add(order_key)
        elif status == "重复跳过":
            stats["duplicate_rows"] += 1
            if order_key:
                duplicate_orders.add(order_key)
        else:
            stats["pending_rows"] += 1

    stats["imported_orders"] = len(imported_orders)
    stats["duplicate_orders"] = len(duplicate_orders)
    return stats


def preview_order_sync_batch(batch_name: str) -> dict[str, object]:
    doc = _get_order_sync_batch_doc(batch_name)
    order_groups = _prepare_order_sync_batch(doc)
    _save_order_sync_batch(doc)
    return _build_order_sync_preview_response(doc, order_groups)


def load_order_sync_batch_csv(
    batch_name: str,
    *,
    csv_content: str,
    source_file_name: str | None = None,
    replace_existing: int | str | bool | None = 1,
) -> dict[str, object]:
    doc = _get_order_sync_batch_doc(batch_name)
    parsed_rows = _parse_order_sync_csv(csv_content)

    if _coerce_bool(replace_existing, default=True):
        doc.set("items", [])

    start_index = len(list(getattr(doc, "items", None) or [])) + 1
    for offset, row in enumerate(parsed_rows, start=start_index):
        doc.append(
            "items",
            {
                "row_no": offset,
                "external_order_id": row["external_order_id"],
                "line_no": row["line_no"],
                "order_date": row["order_date"],
                "customer": row["customer"],
                "item_code": row["item_code"],
                "platform_sku": row["platform_sku"],
                "qty": row["qty"],
                "rate": row["rate"],
                "biz_type": row["biz_type"],
                "delivery_date": row["delivery_date"],
                "warehouse": row["warehouse"],
                "row_status": "草稿",
                "sales_order": "",
                "sales_order_item_ref": "",
                "message": "",
            },
        )

    doc.source_file_name = normalize_text(source_file_name) or doc.source_file_name
    doc.source_hash = _build_source_hash(csv_content)
    validate_order_sync_batch(doc)
    _save_order_sync_batch(doc)
    summary = summarize_order_sync_batch(doc)
    return {
        "ok": True,
        "name": doc.name,
        "batch_no": doc.batch_no or doc.name,
        "loaded_rows": len(parsed_rows),
        "batch_status": doc.batch_status,
        "summary": summary,
        "message": _("已导入 {0} 行 CSV 数据到批次。").format(len(parsed_rows)),
    }


def execute_order_sync_batch(batch_name: str) -> dict[str, object]:
    doc = _get_order_sync_batch_doc(batch_name)
    order_groups = _prepare_order_sync_batch(doc)

    created_orders: list[str] = []
    failed_orders: list[str] = []

    for group in order_groups:
        if group["group_status"] != "待导入":
            continue

        try:
            payload = _build_sales_order_payload(doc, group)
            sales_order = frappe.get_doc(payload)
            sales_order.insert(ignore_permissions=True)
        except Exception as exc:  # pragma: no cover - exercised via tests with fake insert
            failed_orders.append(group["external_order_id"])
            _mark_group_as_failed(group, str(exc))
            continue

        created_orders.append(sales_order.name)
        _mark_group_as_imported(group, sales_order)

    doc.last_import_at = now_datetime()
    _refresh_batch_totals(doc)
    _sync_batch_status(doc)
    _save_order_sync_batch(doc)

    summary = summarize_order_sync_batch(doc)
    return {
        "ok": True,
        "name": doc.name,
        "batch_no": doc.batch_no or doc.name,
        "batch_status": doc.batch_status,
        "created_orders": created_orders,
        "created_count": len(created_orders),
        "failed_orders": failed_orders,
        "summary": summary,
        "message": _build_execute_message(created_orders, failed_orders, summary),
    }


def _sync_from_channel_store(doc) -> None:
    defaults = _get_cached_channel_store_defaults(doc, doc.channel_store)
    if not doc.channel:
        doc.channel = defaults["channel"]
    if not doc.default_company:
        doc.default_company = defaults["default_company"]
    if not doc.default_customer:
        doc.default_customer = defaults["default_customer"]
    if not doc.default_warehouse:
        doc.default_warehouse = defaults["warehouse"]
    if not doc.default_price_list:
        doc.default_price_list = defaults["price_list"]


def _normalize_batch_rows(doc) -> None:
    for idx, row in enumerate(list(getattr(doc, "items", None) or []), start=1):
        _normalize_batch_row(doc, row, idx)

    _refresh_batch_totals(doc)


def _normalize_batch_row(doc, row, idx: int) -> None:
    row.row_no = _coerce_positive_int(getattr(row, "row_no", None), default=idx)
    row.external_order_id = normalize_text(getattr(row, "external_order_id", None))
    row.line_no = normalize_text(getattr(row, "line_no", None))
    row.order_date = _normalize_date(getattr(row, "order_date", None))
    row.customer = normalize_text(getattr(row, "customer", None)) or doc.default_customer
    row.item_code = normalize_text(getattr(row, "item_code", None))
    row.platform_sku = normalize_text(getattr(row, "platform_sku", None))
    row.qty = coerce_non_negative_float(getattr(row, "qty", None), f"第 {idx} 行数量")
    row.rate = coerce_non_negative_float(getattr(row, "rate", None), f"第 {idx} 行单价")
    row.biz_type = normalize_select(
        getattr(row, "biz_type", None),
        f"第 {idx} 行业务类型",
        ORDER_SYNC_BIZ_TYPES,
        default="零售",
        alias_map=ORDER_SYNC_BIZ_TYPE_ALIASES,
    )
    row.delivery_date = _normalize_date(getattr(row, "delivery_date", None)) or row.order_date
    row.warehouse = normalize_text(getattr(row, "warehouse", None)) or doc.default_warehouse
    row.row_status = normalize_select(
        getattr(row, "row_status", None),
        f"第 {idx} 行状态",
        ORDER_SYNC_ROW_STATUSES,
        default="草稿",
        alias_map=ORDER_SYNC_ROW_STATUS_ALIASES,
    )
    row.sales_order = normalize_text(getattr(row, "sales_order", None))
    row.sales_order_item_ref = normalize_text(getattr(row, "sales_order_item_ref", None))
    row.message = normalize_text(getattr(row, "message", None))

    errors: list[str] = []
    if not row.external_order_id:
        errors.append(_("外部订单号不能为空。"))
    if not row.order_date:
        errors.append(_("下单日期不能为空。"))
    if not row.item_code:
        errors.append(_("SKU不能为空。"))
    if row.qty <= 0:
        errors.append(_("数量必须大于 0。"))
    if not doc.default_company:
        errors.append(_("批次默认公司不能为空。"))
    if not row.customer:
        errors.append(_("客户不能为空。"))

    if row.customer:
        try:
            _ensure_cached_link_exists(doc, "Customer", row.customer)
        except Exception as exc:  # pragma: no cover - delegated by helper
            errors.append(str(exc))
    if row.item_code:
        try:
            _ensure_cached_link_exists(doc, "Item", row.item_code)
        except Exception as exc:  # pragma: no cover - delegated by helper
            errors.append(str(exc))
    if row.warehouse:
        try:
            _ensure_cached_link_exists(doc, "Warehouse", row.warehouse)
        except Exception as exc:  # pragma: no cover - delegated by helper
            errors.append(str(exc))

    if errors:
        row.row_status = "校验失败"
        row.message = "；".join(errors)
        return

    if row.row_status not in ("已导入", "重复跳过"):
        row.row_status = "待导入"
    row.message = ""


def _sync_batch_status(doc) -> None:
    if doc.batch_status in ("已完成", "已取消", "部分导入"):
        return

    if not getattr(doc, "items", None):
        doc.batch_status = "草稿"
        return

    stats = summarize_order_sync_batch(doc)
    if stats["pending_rows"] > 0:
        doc.batch_status = "待导入"
        return

    if stats["failed_rows"] > 0 and (stats["imported_rows"] > 0 or stats["duplicate_rows"] > 0):
        doc.batch_status = "部分导入"
        return

    if stats["failed_rows"] > 0:
        doc.batch_status = "待校验"
        return

    if stats["imported_rows"] > 0 or stats["duplicate_rows"] > 0:
        doc.batch_status = "已完成"
        return

    doc.batch_status = "草稿"


def _prepare_order_sync_batch(doc) -> list[dict[str, object]]:
    validate_order_sync_batch(doc)
    order_groups = _build_order_groups(doc)
    existing_orders = _get_existing_sales_orders_map(doc.channel_store, [group["external_order_id"] for group in order_groups])

    for group in order_groups:
        if group["group_status"] == "校验失败":
            continue

        existing_order = existing_orders.get(group["external_order_id"])
        if existing_order:
            _mark_group_as_duplicate(group, existing_order)
            continue

        _mark_group_as_pending(group)

    _refresh_batch_totals(doc)
    _sync_batch_status(doc)
    return order_groups


def _parse_order_sync_csv(csv_content: str) -> list[dict[str, str]]:
    content = str(csv_content or "").strip()
    if not content:
        frappe.throw(_("CSV 内容不能为空。"))

    reader = csv.reader(io.StringIO(content))
    headers = next(reader, None)
    if not headers:
        frappe.throw(_("CSV 缺少表头。"))

    header_map = {
        _normalize_csv_header(header): index
        for index, header in enumerate(headers)
        if _normalize_csv_header(header)
    }
    required_fields = [fieldname for fieldname, required in ORDER_SYNC_CSV_FIELDS if required]
    missing_fields = [fieldname for fieldname in required_fields if fieldname not in header_map]
    if missing_fields:
        frappe.throw(
            _("CSV 缺少必要列：{0}。").format("、".join(missing_fields))
        )

    rows: list[dict[str, str]] = []
    for row_values in reader:
        if not any(normalize_text(cell) for cell in row_values):
            continue
        payload = {}
        for fieldname, _required in ORDER_SYNC_CSV_FIELDS:
            column_index = header_map.get(fieldname)
            payload[fieldname] = normalize_text(row_values[column_index]) if column_index is not None and column_index < len(row_values) else ""
        rows.append(payload)

    if not rows:
        frappe.throw(_("CSV 没有可导入的数据行。"))
    return rows


def _build_order_groups(doc) -> list[dict[str, object]]:
    groups: dict[str, dict[str, object]] = {}
    for row in sorted(list(getattr(doc, "items", None) or []), key=lambda item: getattr(item, "row_no", 0) or 0):
        if normalize_text(getattr(row, "row_status", None)) == "已导入":
            continue
        if normalize_text(getattr(row, "row_status", None)) == "校验失败":
            continue

        external_order_id = normalize_text(getattr(row, "external_order_id", None))
        if not external_order_id:
            continue

        group = groups.setdefault(
            external_order_id,
            {
                "external_order_id": external_order_id,
                "rows": [],
                "customer": normalize_text(getattr(row, "customer", None)),
                "order_date": normalize_text(getattr(row, "order_date", None)),
                "biz_type": normalize_text(getattr(row, "biz_type", None)),
                "group_status": "待导入",
                "message": "",
                "sales_order": "",
            },
        )
        group["rows"].append(row)

        if (
            group["customer"] != normalize_text(getattr(row, "customer", None))
            or group["order_date"] != normalize_text(getattr(row, "order_date", None))
            or group["biz_type"] != normalize_text(getattr(row, "biz_type", None))
        ):
            group["group_status"] = "校验失败"
            group["message"] = _("同一外部订单号下的客户、下单日期或业务类型不一致。")

    order_groups = list(groups.values())
    for group in order_groups:
        if group["group_status"] == "校验失败":
            _mark_group_as_failed(group, group["message"])
    return order_groups


def _get_existing_sales_orders_map(channel_store: str, external_order_ids: list[str]) -> dict[str, str]:
    keys = [normalize_text(value) for value in external_order_ids if normalize_text(value)]
    if not channel_store or not keys:
        return {}

    rows = frappe.get_all(
        "Sales Order",
        filters=[
            ["Sales Order", "channel_store", "=", channel_store],
            ["Sales Order", "external_order_id", "in", keys],
            ["Sales Order", "docstatus", "<", 2],
        ],
        fields=["name", "external_order_id"],
    )
    return {
        normalize_text(row.get("external_order_id")): normalize_text(row.get("name"))
        for row in (rows or [])
        if normalize_text(row.get("external_order_id")) and normalize_text(row.get("name"))
    }


def _build_sales_order_payload(doc, group: dict[str, object]) -> dict[str, object]:
    _ensure_cached_link_exists(doc, "Company", doc.default_company)

    customer = normalize_text(group["customer"])
    if not customer:
        frappe.throw(_("外部订单 {0} 缺少客户。").format(frappe.bold(group["external_order_id"])))
    _ensure_cached_link_exists(doc, "Customer", customer)

    items = [_build_sales_order_item_payload(doc, row) for row in group["rows"]]
    if not items:
        frappe.throw(_("外部订单 {0} 没有可导入的有效明细。").format(frappe.bold(group["external_order_id"])))

    payload = {
        "doctype": "Sales Order",
        "company": doc.default_company,
        "customer": customer,
        "transaction_date": group["order_date"],
        "delivery_date": _get_group_delivery_date(group),
        "channel": doc.channel,
        "channel_store": doc.channel_store,
        "selling_price_list": doc.default_price_list,
        "set_warehouse": doc.default_warehouse,
        "external_order_id": group["external_order_id"],
        "biz_type": group["biz_type"],
        "remarks": _("由订单同步批次 {0} 自动导入。").format(doc.name),
        "items": items,
    }
    return _filter_doc_payload("Sales Order", payload, items=items)


def _build_sales_order_item_payload(doc, row) -> dict[str, object]:
    item_values = _get_cached_order_sync_item_values(doc, row.item_code)

    payload = {
        "doctype": "Sales Order Item",
        "item_code": row.item_code,
        "qty": row.qty,
        "rate": row.rate,
        "delivery_date": row.delivery_date or row.order_date,
        "warehouse": row.warehouse or doc.default_warehouse,
        "platform_sku": row.platform_sku,
        "style": normalize_text(item_values.get("style")),
        "color_code": normalize_text(item_values.get("color_code")),
        "color_name": normalize_text(item_values.get("color_name")),
        "size_code": normalize_text(item_values.get("size_code")),
        "size_name": normalize_text(item_values.get("size_name")),
    }
    return _filter_doc_payload("Sales Order Item", payload)


def _get_group_delivery_date(group: dict[str, object]) -> str:
    delivery_dates = sorted(
        normalize_text(getattr(row, "delivery_date", None))
        for row in group["rows"]
        if normalize_text(getattr(row, "delivery_date", None))
    )
    return delivery_dates[0] if delivery_dates else normalize_text(group["order_date"])


def _mark_group_as_failed(group: dict[str, object], message: str) -> None:
    group["group_status"] = "校验失败"
    group["message"] = normalize_text(message)
    for row in group["rows"]:
        row.row_status = "校验失败"
        row.message = group["message"]
        row.sales_order = ""
        row.sales_order_item_ref = ""


def _mark_group_as_duplicate(group: dict[str, object], sales_order_name: str) -> None:
    group["group_status"] = "重复跳过"
    group["sales_order"] = normalize_text(sales_order_name)
    group["message"] = _("外部订单 {0} 已存在销售订单 {1}。").format(
        frappe.bold(group["external_order_id"]),
        frappe.bold(sales_order_name),
    )
    for row in group["rows"]:
        row.row_status = "重复跳过"
        row.message = group["message"]
        row.sales_order = group["sales_order"]
        row.sales_order_item_ref = ""


def _mark_group_as_pending(group: dict[str, object]) -> None:
    group["group_status"] = "待导入"
    group["message"] = ""
    for row in group["rows"]:
        row.row_status = "待导入"
        row.message = ""
        row.sales_order = ""
        row.sales_order_item_ref = ""


def _mark_group_as_imported(group: dict[str, object], sales_order) -> None:
    item_rows = list(getattr(sales_order, "items", None) or [])
    for idx, row in enumerate(group["rows"]):
        row.row_status = "已导入"
        row.message = ""
        row.sales_order = sales_order.name
        row.sales_order_item_ref = normalize_text(getattr(item_rows[idx], "name", None)) if idx < len(item_rows) else ""


def _refresh_batch_totals(doc) -> None:
    stats = summarize_order_sync_batch(doc)
    doc.total_rows = stats["total_rows"]
    doc.valid_rows = stats["valid_rows"]
    doc.failed_rows = stats["failed_rows"]
    doc.imported_orders = stats["imported_orders"]
    doc.duplicate_orders = stats["duplicate_orders"]


def _build_order_sync_preview_response(doc, order_groups: list[dict[str, object]]) -> dict[str, object]:
    summary = summarize_order_sync_batch(doc)
    return {
        "ok": True,
        "name": doc.name,
        "batch_no": doc.batch_no or doc.name,
        "batch_status": doc.batch_status,
        "summary": summary,
        "orders": [
            {
                "external_order_id": group["external_order_id"],
                "row_count": len(group["rows"]),
                "customer": group["customer"],
                "order_date": group["order_date"],
                "biz_type": group["biz_type"],
                "group_status": group["group_status"],
                "sales_order": group["sales_order"],
                "message": group["message"],
            }
            for group in order_groups
        ],
        "message": _build_preview_message(summary),
    }


def _build_preview_message(summary: dict[str, int]) -> str:
    if summary["pending_rows"] > 0:
        return _("批次预览完成，存在 {0} 行待导入明细。").format(summary["pending_rows"])
    if summary["duplicate_rows"] > 0:
        return _("批次预览完成，所有有效明细均已识别为重复订单。")
    if summary["failed_rows"] > 0:
        return _("批次预览完成，但仍有 {0} 行需要修正。").format(summary["failed_rows"])
    return _("批次预览完成。")


def _build_execute_message(
    created_orders: list[str],
    failed_orders: list[str],
    summary: dict[str, int],
) -> str:
    if created_orders and not failed_orders:
        return _("订单导入完成，共创建 {0} 张销售订单。").format(len(created_orders))
    if created_orders and failed_orders:
        return _(
            "订单导入部分完成，已创建 {0} 张销售订单，仍有 {1} 个外部订单失败。"
        ).format(len(created_orders), len(failed_orders))
    if summary["duplicate_rows"] > 0 and not failed_orders:
        return _("当前批次没有新订单可导入，重复订单已跳过。")
    return _("当前批次没有可导入的有效订单。")


def _save_order_sync_batch(doc) -> None:
    doc.save(ignore_permissions=True)


def _get_order_sync_batch_doc(batch_name: str):
    return frappe.get_doc("Order Sync Batch", batch_name)


def _filter_doc_payload(
    doctype: str,
    payload: dict[str, object],
    *,
    items: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    meta = frappe.get_meta(doctype)
    filtered = {"doctype": doctype}
    for fieldname, value in payload.items():
        if fieldname == "doctype":
            continue
        if fieldname == "items":
            if meta.has_field("items") and items is not None:
                filtered["items"] = items
            continue
        if value in (None, ""):
            continue
        if meta.has_field(fieldname):
            filtered[fieldname] = value
    return filtered


def _normalize_date(value) -> str:
    if value in (None, ""):
        return ""
    return str(getdate(value))


def _normalize_csv_header(value: str) -> str:
    return normalize_text(value).lstrip("\ufeff")


def _build_source_hash(csv_content: str) -> str:
    return hashlib.sha1(str(csv_content or "").encode("utf-8")).hexdigest()


def _coerce_bool(value, *, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = normalize_text(str(value)).lower()
    if normalized in ("1", "true", "yes", "y", "on"):
        return True
    if normalized in ("0", "false", "no", "n", "off"):
        return False
    return default


def _coerce_positive_int(value, *, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        row_no = int(float(value))
    except (TypeError, ValueError):
        return default
    return row_no if row_no > 0 else default


def _is_unsaved_name(value: str) -> bool:
    normalized = normalize_text(value)
    return not normalized or normalized.startswith("New ")


def _reset_order_sync_cache(doc) -> None:
    cache = {
        "channel_store_defaults": {},
        "link_exists": {},
        "item_values": {},
    }
    flags = getattr(doc, "flags", None)
    if flags is not None:
        flags.order_sync_cache = cache
        return
    doc._order_sync_cache = cache


def _get_order_sync_cache(doc) -> dict[str, dict[object, object]]:
    flags = getattr(doc, "flags", None)
    if flags is not None:
        cache = getattr(flags, "order_sync_cache", None)
        if isinstance(cache, dict):
            return cache
    else:
        cache = getattr(doc, "_order_sync_cache", None)
        if isinstance(cache, dict):
            return cache

    _reset_order_sync_cache(doc)
    return _get_order_sync_cache(doc)


def _ensure_cached_link_exists(doc, doctype: str, name: str | None) -> None:
    normalized_name = normalize_text(name)
    if not normalized_name:
        return

    cache = _get_order_sync_cache(doc)["link_exists"]
    cache_key = (doctype, normalized_name)
    if cache.get(cache_key):
        return

    ensure_link_exists(doctype, normalized_name)
    cache[cache_key] = True


def _get_cached_channel_store_defaults(doc, store_name: str) -> dict[str, str]:
    normalized_store_name = normalize_text(store_name)
    if not normalized_store_name:
        return {
            "channel": "",
            "warehouse": "",
            "price_list": "",
            "default_company": "",
            "default_customer": "",
            "status": "",
        }

    cache = _get_order_sync_cache(doc)["channel_store_defaults"]
    if normalized_store_name not in cache:
        cache[normalized_store_name] = get_channel_store_defaults(normalized_store_name)
    return cache[normalized_store_name]


def _get_cached_order_sync_item_values(doc, item_code: str) -> dict[str, object]:
    normalized_item_code = normalize_text(item_code)
    if not normalized_item_code:
        return {}

    cache = _get_order_sync_cache(doc)["item_values"]
    if normalized_item_code not in cache:
        cache[normalized_item_code] = frappe.db.get_value(
            "Item",
            normalized_item_code,
            ["style", "color_code", "color_name", "size_code", "size_name"],
            as_dict=True,
        ) or {}
    return cache[normalized_item_code]
