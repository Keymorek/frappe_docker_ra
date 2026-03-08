from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from fashion_erp.fashion_stock.report.common import (
    is_checked,
    make_summary_item,
    normalize_report_filters,
    round_float,
)


def execute(filters=None):
    filters = normalize_report_filters(filters)
    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data)
    return columns, data, None, None, summary


def get_columns() -> list[dict[str, object]]:
    return [
        {"label": _("款号"), "fieldname": "style", "fieldtype": "Link", "options": "Style", "width": 140},
        {"label": _("款号名称"), "fieldname": "style_name", "fieldtype": "Data", "width": 160},
        {"label": _("SKU"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 180},
        {"label": _("货品名称"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": _("颜色编码"), "fieldname": "color_code", "fieldtype": "Data", "width": 90},
        {"label": _("尺码编码"), "fieldname": "size_code", "fieldtype": "Data", "width": 90},
        {"label": _("仓库"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 160},
        {"label": _("现货数量"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 110},
        {"label": _("预留数量"), "fieldname": "reserved_qty", "fieldtype": "Float", "width": 110},
        {"label": _("预计数量"), "fieldname": "projected_qty", "fieldtype": "Float", "width": 110},
        {"label": _("安全库存"), "fieldname": "safe_stock", "fieldtype": "Float", "width": 110},
        {"label": _("可售"), "fieldname": "sellable", "fieldtype": "Check", "width": 70},
        {"label": _("SKU 状态"), "fieldname": "sku_status", "fieldtype": "Data", "width": 100},
    ]


def get_data(filters: dict[str, object]) -> list[dict[str, object]]:
    conditions = [
        "coalesce(item.disabled, 0) = 0",
        "coalesce(item.item_usage_type, '成品') = '成品'",
    ]
    params: dict[str, object] = {}

    if filters.get("style"):
        conditions.append("item.style = %(style)s")
        params["style"] = filters["style"]
    if filters.get("brand"):
        conditions.append("item.brand = %(brand)s")
        params["brand"] = filters["brand"]
    if filters.get("item_group"):
        conditions.append("item.item_group = %(item_group)s")
        params["item_group"] = filters["item_group"]
    if filters.get("warehouse"):
        conditions.append("bin.warehouse = %(warehouse)s")
        params["warehouse"] = filters["warehouse"]

    having_clause = ""
    if not is_checked(filters, "include_zero_stock", default=False):
        having_clause = """
        having
            round(sum(coalesce(bin.actual_qty, 0)), 6) <> 0
            or round(sum(coalesce(bin.reserved_qty, 0)), 6) <> 0
            or round(sum(coalesce(bin.projected_qty, 0)), 6) <> 0
        """

    rows = frappe.db.sql(
        f"""
        select
            coalesce(item.style, '') as style,
            coalesce(style_doc.style_name, '') as style_name,
            item.item_code,
            item.item_name,
            coalesce(item.color_code, '') as color_code,
            coalesce(item.size_code, '') as size_code,
            coalesce(bin.warehouse, '') as warehouse,
            sum(coalesce(bin.actual_qty, 0)) as actual_qty,
            sum(coalesce(bin.reserved_qty, 0)) as reserved_qty,
            sum(coalesce(bin.projected_qty, 0)) as projected_qty,
            max(coalesce(item.safe_stock, 0)) as safe_stock,
            max(coalesce(item.sellable, 0)) as sellable,
            max(coalesce(item.sku_status, '')) as sku_status
        from `tabItem` item
        left join `tabStyle` style_doc on style_doc.name = item.style
        left join `tabBin` bin on bin.item_code = item.name
        where {" and ".join(conditions)}
        group by
            coalesce(item.style, ''),
            coalesce(style_doc.style_name, ''),
            item.item_code,
            item.item_name,
            coalesce(item.color_code, ''),
            coalesce(item.size_code, ''),
            coalesce(bin.warehouse, '')
        {having_clause}
        order by
            coalesce(item.style, '') asc,
            item.item_code asc,
            coalesce(bin.warehouse, '') asc
        """,
        params,
        as_dict=True,
    )

    data: list[dict[str, object]] = []
    for row in rows:
        data.append(
            {
                "style": row.get("style"),
                "style_name": row.get("style_name"),
                "item_code": row.get("item_code"),
                "item_name": row.get("item_name"),
                "color_code": row.get("color_code"),
                "size_code": row.get("size_code"),
                "warehouse": row.get("warehouse"),
                "actual_qty": round_float(row.get("actual_qty"), 6),
                "reserved_qty": round_float(row.get("reserved_qty"), 6),
                "projected_qty": round_float(row.get("projected_qty"), 6),
                "safe_stock": round_float(row.get("safe_stock"), 6),
                "sellable": row.get("sellable"),
                "sku_status": row.get("sku_status"),
            }
        )
    return data


def get_summary(data: list[dict[str, object]]) -> list[dict[str, object]]:
    sku_count = len({row["item_code"] for row in data if row.get("item_code")})
    total_actual_qty = sum(flt(row.get("actual_qty")) for row in data)
    total_reserved_qty = sum(flt(row.get("reserved_qty")) for row in data)
    total_projected_qty = sum(flt(row.get("projected_qty")) for row in data)
    shortage_count = sum(
        1 for row in data if flt(row.get("actual_qty")) < flt(row.get("safe_stock"))
    )
    return [
        make_summary_item(_("SKU 数"), sku_count, indicator="Blue", datatype="Int"),
        make_summary_item(_("现货数量"), round_float(total_actual_qty, 6), indicator="Green", datatype="Float"),
        make_summary_item(_("预留数量"), round_float(total_reserved_qty, 6), indicator="Orange", datatype="Float"),
        make_summary_item(_("预计数量"), round_float(total_projected_qty, 6), indicator="Blue", datatype="Float"),
        make_summary_item(_("低于安全库存 SKU"), shortage_count, indicator="Red", datatype="Int"),
    ]

