from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from fashion_erp.style.services.style_service import (
    coerce_non_negative_float,
    ensure_link_exists,
    normalize_text,
)


def validate_delivery_note_fulfillment(doc) -> None:
    _reset_delivery_note_fulfillment_validation_cache(doc)
    doc.fulfillment_consumable_stock_entry = normalize_text(
        getattr(doc, "fulfillment_consumable_stock_entry", None)
    )
    doc.manual_logistics_fee = coerce_non_negative_float(
        getattr(doc, "manual_logistics_fee", None),
        "手工快递费",
    )
    doc.fulfillment_consumable_qty = 0
    doc.fulfillment_consumable_amount = 0
    doc.fulfillment_total_cost = 0

    normalized_rows = []
    for row in list(getattr(doc, "fulfillment_consumables", None) or []):
        if _is_empty_consumable_row(row):
            continue

        _prepare_consumable_row(doc, row)
        normalized_rows.append(row)
        doc.fulfillment_consumable_qty = round(
            flt(getattr(doc, "fulfillment_consumable_qty", 0)) + flt(row.qty),
            6,
        )
        doc.fulfillment_consumable_amount = round(
            flt(getattr(doc, "fulfillment_consumable_amount", 0)) + flt(row.estimated_amount),
            2,
        )

    doc.fulfillment_consumables = normalized_rows
    doc.fulfillment_total_cost = round(
        flt(getattr(doc, "fulfillment_consumable_amount", 0)) + flt(getattr(doc, "manual_logistics_fee", 0)),
        2,
    )

    if doc.fulfillment_consumable_stock_entry:
        ensure_link_exists("Stock Entry", doc.fulfillment_consumable_stock_entry)


@frappe.whitelist()
def prepare_delivery_note_fulfillment_stock_entry(
    delivery_note_name: str,
    *,
    company: str | None = None,
    posting_date=None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_delivery_note_doc(delivery_note_name)
    _ensure_delivery_note_actionable(doc)
    validate_delivery_note_fulfillment(doc)

    rows = list(getattr(doc, "fulfillment_consumables", None) or [])
    if not rows:
        frappe.throw(_("出货单 {0} 当前没有包装耗材明细。").format(frappe.bold(doc.name)))

    existing_ref = normalize_text(getattr(doc, "fulfillment_consumable_stock_entry", None))
    if existing_ref and frappe.db.exists("Stock Entry", existing_ref):
        frappe.throw(
            _("出货单 {0} 已关联耗材出库单 {1}。").format(
                frappe.bold(doc.name),
                frappe.bold(existing_ref),
            )
        )

    company = normalize_text(company) or normalize_text(getattr(doc, "company", None))
    if not company:
        frappe.throw(_("生成耗材出库单前必须先填写公司。"))
    ensure_link_exists("Company", company)

    items = [_build_stock_entry_item_payload(doc, row) for row in rows]
    payload = _filter_doc_payload(
        "Stock Entry",
        {
            "doctype": "Stock Entry",
            "purpose": "Material Issue",
            "stock_entry_type": "Material Issue" if frappe.db.exists("Stock Entry Type", "Material Issue") else None,
            "company": company,
            "posting_date": _normalize_date(posting_date, use_today=True),
            "delivery_note": doc.name,
            "remarks": normalize_text(note) or _("由出货单 {0} 自动生成包装耗材出库草稿。").format(doc.name),
            "items": items,
        },
        items=items,
    )

    stock_entry = frappe.get_doc(payload)
    stock_entry.insert(ignore_permissions=True)

    doc.fulfillment_consumable_stock_entry = normalize_text(getattr(stock_entry, "name", None))
    doc.save(ignore_permissions=True, ignore_version=True)

    return {
        "ok": True,
        "delivery_note": doc.name,
        "stock_entry": doc.fulfillment_consumable_stock_entry,
        "row_count": len(rows),
        "fulfillment_consumable_qty": flt(getattr(doc, "fulfillment_consumable_qty", 0)),
        "fulfillment_consumable_amount": flt(getattr(doc, "fulfillment_consumable_amount", 0)),
        "manual_logistics_fee": flt(getattr(doc, "manual_logistics_fee", 0)),
        "fulfillment_total_cost": flt(getattr(doc, "fulfillment_total_cost", 0)),
        "message": _("已生成包装耗材出库草稿 {0}。").format(
            frappe.bold(doc.fulfillment_consumable_stock_entry or _("未命名出库单"))
        ),
    }


@frappe.whitelist()
def get_delivery_note_fulfillment_cost_summary(
    date_from=None,
    date_to=None,
    company: str | None = None,
) -> dict[str, object]:
    filters = [["Delivery Note", "docstatus", "=", 1]]
    if date_from not in (None, ""):
        filters.append(["Delivery Note", "posting_date", ">=", _normalize_date(date_from)])
    if date_to not in (None, ""):
        filters.append(["Delivery Note", "posting_date", "<=", _normalize_date(date_to)])
    company = normalize_text(company)
    if company:
        filters.append(["Delivery Note", "company", "=", company])

    rows = frappe.get_all(
        "Delivery Note",
        filters=filters,
        fields=[
            "name",
            "posting_date",
            "customer",
            "company",
            "fulfillment_consumable_amount",
            "manual_logistics_fee",
            "fulfillment_total_cost",
        ],
        order_by="posting_date asc, modified asc",
    )

    result_rows: list[dict[str, object]] = []
    summary = {
        "delivery_note_count": 0,
        "fulfillment_consumable_amount": 0.0,
        "manual_logistics_fee": 0.0,
        "fulfillment_total_cost": 0.0,
    }
    for row in rows or []:
        consumable_amount = round(flt(row.get("fulfillment_consumable_amount")), 2)
        logistics_fee = round(flt(row.get("manual_logistics_fee")), 2)
        total_cost = round(flt(row.get("fulfillment_total_cost")), 2)
        result_rows.append(
            {
                "delivery_note": normalize_text(row.get("name")),
                "posting_date": normalize_text(row.get("posting_date")),
                "customer": normalize_text(row.get("customer")),
                "company": normalize_text(row.get("company")),
                "fulfillment_consumable_amount": consumable_amount,
                "manual_logistics_fee": logistics_fee,
                "fulfillment_total_cost": total_cost,
            }
        )
        summary["delivery_note_count"] += 1
        summary["fulfillment_consumable_amount"] = round(
            summary["fulfillment_consumable_amount"] + consumable_amount,
            2,
        )
        summary["manual_logistics_fee"] = round(
            summary["manual_logistics_fee"] + logistics_fee,
            2,
        )
        summary["fulfillment_total_cost"] = round(
            summary["fulfillment_total_cost"] + total_cost,
            2,
        )

    return {
        "ok": True,
        "rows": result_rows,
        "summary": summary,
        "message": _("履约成本汇总完成，共 {0} 张已提交出货单。").format(summary["delivery_note_count"]),
    }


def _prepare_consumable_row(doc, row) -> None:
    row.item_code = normalize_text(getattr(row, "item_code", None))
    row.item_name = normalize_text(getattr(row, "item_name", None))
    row.uom = normalize_text(getattr(row, "uom", None))
    row.warehouse = normalize_text(getattr(row, "warehouse", None))

    if not row.item_code:
        frappe.throw(_("包装耗材明细必须填写物料编码。"))
    _ensure_cached_link_exists(doc, "Item", row.item_code)

    item_values = _get_cached_consumable_item_values(doc, row.item_code)
    if not cint(item_values.get("is_fulfillment_consumable")):
        frappe.throw(
            _("物料 {0} 不是包装耗材，不能挂到出货单耗材明细。").format(
                frappe.bold(row.item_code)
            )
        )

    row.item_name = normalize_text(row.item_name or item_values.get("item_name"))
    row.uom = normalize_text(row.uom or item_values.get("stock_uom"))
    row.warehouse = normalize_text(
        row.warehouse
        or item_values.get("supply_warehouse")
        or getattr(doc, "set_warehouse", None)
        or _get_default_delivery_note_warehouse(doc)
    )
    if not row.warehouse:
        frappe.throw(
            _("包装耗材 {0} 缺少仓库，不能挂到出货单。").format(frappe.bold(row.item_code))
        )
    _ensure_cached_link_exists(doc, "Warehouse", row.warehouse)

    row.qty = coerce_non_negative_float(getattr(row, "qty", None), "包装耗材数量")
    if flt(row.qty) <= 0:
        frappe.throw(_("包装耗材 {0} 的数量必须大于 0。").format(frappe.bold(row.item_code)))

    row.valuation_rate = flt(item_values.get("valuation_rate"))
    row.estimated_amount = round(flt(row.qty) * flt(row.valuation_rate), 2)


def _build_stock_entry_item_payload(doc, row) -> dict[str, object]:
    payload = {
        "doctype": "Stock Entry Detail",
        "item_code": normalize_text(getattr(row, "item_code", None)),
        "qty": flt(getattr(row, "qty", 0)),
        "s_warehouse": normalize_text(getattr(row, "warehouse", None)),
        "delivery_note": doc.name,
    }
    return _filter_doc_payload("Stock Entry Detail", payload)


def _get_delivery_note_doc(delivery_note_name: str):
    delivery_note_name = normalize_text(delivery_note_name)
    if not delivery_note_name:
        frappe.throw(_("出货单不能为空。"))
    return frappe.get_doc("Delivery Note", delivery_note_name)


def _ensure_delivery_note_actionable(doc) -> None:
    if cint(getattr(doc, "docstatus", 0)) == 2:
        frappe.throw(_("已取消的出货单不能生成耗材出库单。"))


def _is_empty_consumable_row(row) -> bool:
    return not any(
        [
            normalize_text(getattr(row, "item_code", None)),
            normalize_text(getattr(row, "warehouse", None)),
            flt(getattr(row, "qty", 0)),
        ]
    )


def _get_default_delivery_note_warehouse(doc) -> str:
    for row in list(getattr(doc, "items", None) or []):
        warehouse = normalize_text(getattr(row, "warehouse", None))
        if warehouse:
            return warehouse
    return ""


def _reset_delivery_note_fulfillment_validation_cache(doc) -> None:
    cache = {
        "link_exists": {},
        "item_values": {},
    }
    flags = getattr(doc, "flags", None)
    if flags is not None:
        flags.delivery_note_fulfillment_validation_cache = cache
        return
    doc._delivery_note_fulfillment_validation_cache = cache


def _get_delivery_note_fulfillment_validation_cache(doc) -> dict[str, object]:
    flags = getattr(doc, "flags", None)
    if flags is not None:
        cache = getattr(flags, "delivery_note_fulfillment_validation_cache", None)
        if isinstance(cache, dict):
            return cache
    else:
        cache = getattr(doc, "_delivery_note_fulfillment_validation_cache", None)
        if isinstance(cache, dict):
            return cache

    _reset_delivery_note_fulfillment_validation_cache(doc)
    return _get_delivery_note_fulfillment_validation_cache(doc)


def _ensure_cached_link_exists(doc, doctype: str, name: str | None) -> None:
    normalized_name = normalize_text(name)
    if not normalized_name:
        return

    cache = _get_delivery_note_fulfillment_validation_cache(doc)["link_exists"]
    cache_key = (doctype, normalized_name)
    if cache.get(cache_key):
        return

    ensure_link_exists(doctype, normalized_name)
    cache[cache_key] = True


def _get_cached_consumable_item_values(doc, item_code: str) -> dict[str, object]:
    normalized_item_code = normalize_text(item_code)
    if not normalized_item_code:
        return {}

    cache = _get_delivery_note_fulfillment_validation_cache(doc)["item_values"]
    if normalized_item_code not in cache:
        cache[normalized_item_code] = frappe.db.get_value(
            "Item",
            normalized_item_code,
            ["item_name", "stock_uom", "valuation_rate", "is_fulfillment_consumable", "supply_warehouse"],
            as_dict=True,
        ) or {}
    return cache[normalized_item_code]


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


def _normalize_date(value, *, use_today: bool = False) -> str:
    if value in (None, ""):
        return nowdate() if use_today else ""
    return str(getdate(value))
