import frappe
from frappe import _

from fashion_erp.style.services.style_service import (
    get_brand_abbreviation,
    get_enabled_size_codes,
    get_style_variant_generation_issues,
)


def get_brand_sku_prefix(style_doc) -> str:
    brand_prefix = get_brand_abbreviation(style_doc.brand, raise_on_missing_meta=True)
    if not brand_prefix:
        frappe.throw(_("生成单品编码前必须先维护品牌简称。"))
    return brand_prefix


def build_sku_code(style_doc, color_code: str, size_code: str) -> str:
    return f"{get_brand_sku_prefix(style_doc)}-{style_doc.style_code}-{color_code}-{size_code}"


def build_template_item_code(style_doc) -> str:
    return f"TPL-{style_doc.style_code}"


def create_template_item_for_style(style_name: str) -> dict[str, object]:
    style = frappe.get_doc("Style", style_name)

    if not style.item_group:
        frappe.throw(_("创建模板货品前必须先选择物料组。"))

    template_code = build_template_item_code(style)
    template_name = _build_template_item_name(style.style_name)

    if style.item_template and frappe.db.exists("Item", style.item_template):
        item = frappe.get_doc("Item", style.item_template)
        changed = _sync_template_item(item, style, template_name)
        if changed:
            item.save(ignore_permissions=True)
        return {
            "item_code": item.name,
            "created": False,
            "updated": changed,
            "linked": True,
        }

    if frappe.db.exists("Item", template_code):
        item = frappe.get_doc("Item", template_code)
        changed = _sync_template_item(item, style, template_name)
        if changed:
            item.save(ignore_permissions=True)
        _link_template_item(style, item.name)
        return {
            "item_code": item.name,
            "created": False,
            "updated": changed,
            "linked": True,
        }

    item = frappe.get_doc(_build_template_item_doc(style, template_code, template_name))
    item.insert(ignore_permissions=True)
    _link_template_item(style, item.name)
    return {
        "item_code": item.name,
        "created": True,
        "updated": False,
        "linked": True,
    }


def generate_variants_for_style(style_name: str) -> dict[str, object]:
    style = frappe.get_doc("Style", style_name)
    issues = get_style_variant_generation_issues(style)
    if issues:
        frappe.throw("<br>".join(issues))

    size_rows = frappe.get_all(
        "Size Code",
        filters={"size_system": style.size_system, "enabled": 1},
        fields=["name", "size_code", "size_name", "sort_order"],
        order_by="sort_order asc, size_code asc",
    )

    created = []
    updated = []
    skipped = []

    for color_row in style.colors:
        if not color_row.enabled:
            continue

        for size_row in size_rows:
            sku_code = build_sku_code(style, color_row.color_code, size_row.size_code)
            if frappe.db.exists("Item", sku_code):
                item = frappe.get_doc("Item", sku_code)
                changed = _sync_item_from_style(item, style, color_row, size_row)
                if changed:
                    item.save(ignore_permissions=True)
                    updated.append(sku_code)
                else:
                    skipped.append(sku_code)
                continue

            item = frappe.get_doc(_build_item_doc(style, color_row, size_row, sku_code))
            item.insert(ignore_permissions=True)
            created.append(sku_code)

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "size_codes": get_enabled_size_codes(style.size_system),
    }


def build_style_matrix(style_name: str) -> dict[str, object]:
    style = frappe.get_doc("Style", style_name)
    issues = get_style_variant_generation_issues(style)
    matrix_brand_prefix = get_brand_abbreviation(style.brand) or "?"

    size_rows = frappe.get_all(
        "Size Code",
        filters={"size_system": style.size_system, "enabled": 1},
        fields=["size_code", "size_name", "sort_order"],
        order_by="sort_order asc, size_code asc",
    )

    rows = []
    existing_count = 0
    missing_count = 0

    for color_row in style.colors:
        if not color_row.enabled:
            continue

        cells = []
        for size_row in size_rows:
            sku_code = f"{matrix_brand_prefix}-{style.style_code}-{color_row.color_code}-{size_row.size_code}"
            item = _get_item_snapshot(sku_code)
            exists = bool(item)
            if exists:
                existing_count += 1
            else:
                missing_count += 1

            cells.append(
                {
                    "size_code": size_row.size_code,
                    "size_name": size_row.size_name,
                    "sku_code": sku_code,
                    "exists": exists,
                    "item_name": item.item_name if item else "",
                    "sellable": item.sellable if item else 0,
                    "stock_qty": item.stock_qty if item else 0,
                }
            )

        rows.append(
            {
                "color": color_row.color,
                "color_name": color_row.color_name,
                "color_code": color_row.color_code,
                "cells": cells,
            }
        )

    return {
        "style_name": style.style_name,
        "style_code": style.style_code,
        "size_system": style.size_system,
        "size_rows": size_rows,
        "matrix_rows": rows,
        "issues": issues,
        "summary": {
            "existing_count": existing_count,
            "missing_count": missing_count,
            "total_count": existing_count + missing_count,
        },
        "brand_prefix": matrix_brand_prefix,
        "message": _("款色码矩阵加载完成。"),
    }


def _build_item_doc(style, color_row, size_row, sku_code: str) -> dict[str, object]:
    payload = {
        "doctype": "Item",
        "item_code": sku_code,
        "item_name": _build_item_name(style.style_name, color_row.color_name, size_row.size_name),
        "item_group": style.item_group,
        "stock_uom": "Nos",
        "description": style.description,
        "brand": style.brand,
    }
    payload.update(_build_custom_item_fields(style, color_row, size_row))
    return _filter_item_payload(payload)


def _build_template_item_doc(style, template_code: str, template_name: str) -> dict[str, object]:
    payload = {
        "doctype": "Item",
        "item_code": template_code,
        "item_name": template_name,
        "item_group": style.item_group,
        "stock_uom": "Nos",
        "description": style.description,
        "brand": style.brand,
        "is_stock_item": 0,
    }

    meta = frappe.get_meta("Item")
    if meta.has_field("style"):
        payload["style"] = style.name
    if meta.has_field("style_code"):
        payload["style_code"] = style.style_code
    if meta.has_field("size_system"):
        payload["size_system"] = style.size_system
    if meta.has_field("sellable"):
        payload["sellable"] = 0

    return _filter_item_payload(payload)


def _sync_item_from_style(item, style, color_row, size_row) -> bool:
    target_values = {
        "item_name": _build_item_name(style.style_name, color_row.color_name, size_row.size_name),
        "item_group": style.item_group,
        "description": style.description,
        "brand": style.brand,
    }
    target_values.update(_build_custom_item_fields(style, color_row, size_row))

    changed = False
    meta = frappe.get_meta("Item")
    for fieldname, value in target_values.items():
        if not meta.has_field(fieldname):
            continue
        if item.get(fieldname) != value:
            item.set(fieldname, value)
            changed = True

    return changed


def _build_custom_item_fields(style, color_row, size_row) -> dict[str, object]:
    return {
        "style": style.name,
        "style_code": style.style_code,
        "size_system": style.size_system,
        "color_code": color_row.color_code,
        "color_name": color_row.color_name,
        "size_code": size_row.size_code,
        "size_name": size_row.size_name,
        "sellable": 1,
        "sku_status": "正常",
    }


def _build_item_name(style_name: str, color_name: str, size_name: str) -> str:
    item_name = " / ".join(part for part in [style_name, color_name, size_name] if part)
    return item_name[:140]


def _build_template_item_name(style_name: str) -> str:
    item_name = f"{style_name} / 模板货品"
    return item_name[:140]


def _filter_item_payload(payload: dict[str, object]) -> dict[str, object]:
    meta = frappe.get_meta("Item")
    filtered = {"doctype": payload["doctype"]}
    for fieldname, value in payload.items():
        if fieldname == "doctype":
            continue
        if meta.has_field(fieldname):
            filtered[fieldname] = value
    return filtered


def _get_item_snapshot(item_code: str):
    item_meta = frappe.get_meta("Item")
    fields = ["name", "item_name"]
    if item_meta.has_field("sellable"):
        fields.append("sellable")

    item = frappe.db.get_value("Item", item_code, fields, as_dict=True)
    if not item:
        return None

    item["stock_qty"] = _get_stock_qty(item_code)
    if "sellable" not in item:
        item["sellable"] = 0
    return item


def _get_stock_qty(item_code: str) -> float:
    if not frappe.db.exists("DocType", "Bin"):
        return 0

    result = frappe.db.sql(
        """
        select coalesce(sum(actual_qty), 0)
        from `tabBin`
        where item_code = %s
        """,
        (item_code,),
    )
    return float(result[0][0]) if result else 0


def _link_template_item(style, item_code: str) -> None:
    if style.item_template == item_code:
        return
    style.db_set("item_template", item_code, update_modified=False)
    style.item_template = item_code


def _sync_template_item(item, style, template_name: str) -> bool:
    target_values = {
        "item_name": template_name,
        "item_group": style.item_group,
        "description": style.description,
        "brand": style.brand,
        "is_stock_item": 0,
    }

    meta = frappe.get_meta("Item")
    if meta.has_field("style"):
        target_values["style"] = style.name
    if meta.has_field("style_code"):
        target_values["style_code"] = style.style_code
    if meta.has_field("size_system"):
        target_values["size_system"] = style.size_system
    if meta.has_field("sellable"):
        target_values["sellable"] = 0

    changed = False
    for fieldname, value in target_values.items():
        if not meta.has_field(fieldname):
            continue
        if item.get(fieldname) != value:
            item.set(fieldname, value)
            changed = True

    return changed
