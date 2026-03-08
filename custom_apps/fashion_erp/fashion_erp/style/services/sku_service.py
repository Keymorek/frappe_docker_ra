import frappe
from frappe import _

from fashion_erp.style.services.style_service import (
    get_brand_abbreviation,
    get_selected_style_size_rows,
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


def create_template_item_for_style(style_name: str, *, style_doc=None) -> dict[str, object]:
    style = _get_style_doc(style_name, style_doc=style_doc)

    if not style.item_group:
        frappe.throw(_("创建模板货品前必须先选择成品物料组。"))

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


def generate_variants_for_style(style_name: str, *, style_doc=None) -> dict[str, object]:
    style = _get_style_doc(style_name, style_doc=style_doc)
    size_rows = get_selected_style_size_rows(style)
    size_codes = [size_row.size_code for size_row in size_rows]
    brand_prefix = get_brand_abbreviation(style.brand)
    issues = get_style_variant_generation_issues(
        style,
        enabled_size_codes=size_codes,
        brand_abbreviation=brand_prefix,
    )
    if issues:
        frappe.throw("<br>".join(issues))

    created = []
    updated = []
    skipped = []
    color_rows = [color_row for color_row in style.colors if color_row.enabled]
    existing_item_codes = _get_existing_item_code_set(
        _build_variant_sku_codes(style, color_rows, size_rows, brand_prefix)
    )

    for color_row in color_rows:
        for size_row in size_rows:
            sku_code = _build_sku_code_with_prefix(brand_prefix, style, color_row.color_code, size_row.size_code)
            if sku_code in existing_item_codes:
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
        "size_codes": size_codes,
    }


def build_style_matrix(style_name: str, *, style_doc=None) -> dict[str, object]:
    style = _get_style_doc(style_name, style_doc=style_doc)
    matrix_brand_prefix = get_brand_abbreviation(style.brand) or "?"
    size_rows = get_selected_style_size_rows(style)
    issues = get_style_variant_generation_issues(
        style,
        enabled_size_codes=[size_row.size_code for size_row in size_rows],
        brand_abbreviation="" if matrix_brand_prefix == "?" else matrix_brand_prefix,
    )
    color_rows = [color_row for color_row in style.colors if color_row.enabled]
    item_snapshots = _get_matrix_item_snapshots(style, color_rows, size_rows, matrix_brand_prefix)

    rows = []
    existing_count = 0
    missing_count = 0

    for color_row in color_rows:
        cells = []
        for size_row in size_rows:
            sku_code = f"{matrix_brand_prefix}-{style.style_code}-{color_row.color_code}-{size_row.size_code}"
            item = item_snapshots.get(sku_code)
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


def _get_style_doc(style_name: str | None, *, style_doc=None):
    if style_doc is not None:
        return style_doc
    return frappe.get_doc("Style", style_name)


def _get_matrix_item_snapshots(style, color_rows, size_rows, brand_prefix: str) -> dict[str, object]:
    sku_codes = _build_variant_sku_codes(style, color_rows, size_rows, brand_prefix)
    return _get_item_snapshots(sku_codes)
def _build_variant_sku_codes(style, color_rows, size_rows, brand_prefix: str) -> list[str]:
    return [
        _build_sku_code_with_prefix(brand_prefix, style, color_row.color_code, size_row.size_code)
        for color_row in color_rows
        for size_row in size_rows
    ]


def _build_sku_code_with_prefix(brand_prefix: str, style, color_code: str, size_code: str) -> str:
    return f"{brand_prefix}-{style.style_code}-{color_code}-{size_code}"


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


def _get_item_snapshots(item_codes: list[str]) -> dict[str, object]:
    normalized_codes = [item_code for item_code in item_codes if item_code]
    if not normalized_codes:
        return {}

    item_meta = frappe.get_meta("Item")
    fields = ["name", "item_code", "item_name"]
    if item_meta.has_field("sellable"):
        fields.append("sellable")

    rows = frappe.get_all(
        "Item",
        filters=[["Item", "item_code", "in", normalized_codes]],
        fields=fields,
    )
    stock_qty_map = _get_stock_qty_map(normalized_codes)
    snapshots: dict[str, object] = {}
    for row in rows or []:
        item_code = row.get("item_code") or row.get("name")
        if not item_code:
            continue
        row["stock_qty"] = stock_qty_map.get(item_code, 0.0)
        if "sellable" not in row:
            row["sellable"] = 0
        snapshots[item_code] = row
    return snapshots


def _get_existing_item_code_set(item_codes: list[str]) -> set[str]:
    normalized_codes = [item_code for item_code in item_codes if item_code]
    if not normalized_codes:
        return set()

    rows = frappe.get_all(
        "Item",
        filters=[["Item", "item_code", "in", normalized_codes]],
        fields=["item_code"],
    )
    return {
        row.get("item_code")
        for row in rows or []
        if row.get("item_code")
    }


def _get_stock_qty_map(item_codes: list[str]) -> dict[str, float]:
    normalized_codes = [item_code for item_code in item_codes if item_code]
    if not normalized_codes or not frappe.db.exists("DocType", "Bin"):
        return {}

    rows = frappe.get_all(
        "Bin",
        filters=[["Bin", "item_code", "in", normalized_codes]],
        fields=["item_code", "actual_qty"],
    )
    qty_map: dict[str, float] = {}
    for row in rows or []:
        item_code = row.get("item_code")
        if not item_code:
            continue
        qty_map[item_code] = float(qty_map.get(item_code, 0) + float(row.get("actual_qty") or 0))
    return qty_map


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
