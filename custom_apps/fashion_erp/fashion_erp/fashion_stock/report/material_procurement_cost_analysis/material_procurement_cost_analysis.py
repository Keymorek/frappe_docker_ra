from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from fashion_erp.fashion_stock.report.common import make_summary_item, normalize_report_filters, round_float


def execute(filters=None):
    filters = normalize_report_filters(filters)
    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data)
    return columns, data, None, None, summary


def get_columns() -> list[dict[str, object]]:
    return [
        {"label": _("采购单"), "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 140},
        {"label": _("下单日期"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
        {"label": _("单据状态"), "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": _("供应商"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
        {"label": _("采购用途"), "fieldname": "supply_order_type", "fieldtype": "Data", "width": 110},
        {"label": _("物料"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("物料用途"), "fieldname": "item_usage_type", "fieldtype": "Data", "width": 100},
        {"label": _("采购场景"), "fieldname": "supply_context", "fieldtype": "Data", "width": 100},
        {"label": _("关联款号"), "fieldname": "reference_style", "fieldtype": "Link", "options": "Style", "width": 130},
        {"label": _("关联外包单"), "fieldname": "reference_outsource_order", "fieldtype": "Link", "options": "Outsource Order", "width": 140},
        {"label": _("数量"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
        {"label": _("已收货数量"), "fieldname": "received_qty", "fieldtype": "Float", "width": 100},
        {"label": _("未收货数量"), "fieldname": "outstanding_qty", "fieldtype": "Float", "width": 100},
        {"label": _("单价"), "fieldname": "rate", "fieldtype": "Currency", "width": 90},
        {"label": _("下单金额"), "fieldname": "ordered_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("已收货估算金额"), "fieldname": "received_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("未收货估算金额"), "fieldname": "open_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("仓库"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140},
    ]


def get_data(filters: dict[str, object]) -> list[dict[str, object]]:
    conditions = ["po.docstatus < 2"]
    params: dict[str, object] = {}

    if filters.get("date_from"):
        conditions.append("po.transaction_date >= %(date_from)s")
        params["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("po.transaction_date <= %(date_to)s")
        params["date_to"] = filters["date_to"]
    if filters.get("supplier"):
        conditions.append("po.supplier = %(supplier)s")
        params["supplier"] = filters["supplier"]
    if filters.get("supply_order_type"):
        conditions.append("coalesce(po.supply_order_type, '') = %(supply_order_type)s")
        params["supply_order_type"] = filters["supply_order_type"]
    if filters.get("item_usage_type"):
        conditions.append("coalesce(poi.item_usage_type, '') = %(item_usage_type)s")
        params["item_usage_type"] = filters["item_usage_type"]
    if filters.get("supply_context"):
        conditions.append("coalesce(poi.supply_context, '') = %(supply_context)s")
        params["supply_context"] = filters["supply_context"]
    if filters.get("reference_outsource_order"):
        conditions.append("coalesce(poi.reference_outsource_order, '') = %(reference_outsource_order)s")
        params["reference_outsource_order"] = filters["reference_outsource_order"]

    rows = frappe.db.sql(
        f"""
        select
            po.name as purchase_order,
            po.transaction_date,
            coalesce(po.status, '') as status,
            po.supplier,
            coalesce(po.supply_order_type, '') as supply_order_type,
            poi.item_code,
            coalesce(poi.item_usage_type, '') as item_usage_type,
            coalesce(poi.supply_context, '') as supply_context,
            coalesce(poi.reference_style, '') as reference_style,
            coalesce(poi.reference_outsource_order, '') as reference_outsource_order,
            coalesce(poi.qty, 0) as qty,
            coalesce(poi.received_qty, 0) as received_qty,
            case
                when coalesce(poi.qty, 0) > coalesce(poi.received_qty, 0)
                then coalesce(poi.qty, 0) - coalesce(poi.received_qty, 0)
                else 0
            end as outstanding_qty,
            coalesce(poi.rate, 0) as rate,
            coalesce(poi.amount, 0) as ordered_amount,
            coalesce(poi.rate, 0) * coalesce(poi.received_qty, 0) as received_amount,
            case
                when coalesce(poi.qty, 0) > coalesce(poi.received_qty, 0)
                then coalesce(poi.rate, 0) * (coalesce(poi.qty, 0) - coalesce(poi.received_qty, 0))
                else 0
            end as open_amount,
            coalesce(poi.warehouse, '') as warehouse
        from `tabPurchase Order Item` poi
        inner join `tabPurchase Order` po on po.name = poi.parent
        where {" and ".join(conditions)}
        order by po.transaction_date desc, po.modified desc, poi.idx asc
        """,
        params,
        as_dict=True,
    )

    data: list[dict[str, object]] = []
    for row in rows:
        data.append(
            {
                "purchase_order": row.get("purchase_order"),
                "transaction_date": row.get("transaction_date"),
                "status": row.get("status"),
                "supplier": row.get("supplier"),
                "supply_order_type": row.get("supply_order_type"),
                "item_code": row.get("item_code"),
                "item_usage_type": row.get("item_usage_type"),
                "supply_context": row.get("supply_context"),
                "reference_style": row.get("reference_style"),
                "reference_outsource_order": row.get("reference_outsource_order"),
                "qty": round_float(row.get("qty"), 6),
                "received_qty": round_float(row.get("received_qty"), 6),
                "outstanding_qty": round_float(row.get("outstanding_qty"), 6),
                "rate": round_float(row.get("rate")),
                "ordered_amount": round_float(row.get("ordered_amount")),
                "received_amount": round_float(row.get("received_amount")),
                "open_amount": round_float(row.get("open_amount")),
                "warehouse": row.get("warehouse"),
            }
        )
    return data


def get_summary(data: list[dict[str, object]]) -> list[dict[str, object]]:
    total_ordered_amount = sum(flt(row.get("ordered_amount")) for row in data)
    total_received_amount = sum(flt(row.get("received_amount")) for row in data)
    total_open_amount = sum(flt(row.get("open_amount")) for row in data)
    total_qty = sum(flt(row.get("qty")) for row in data)
    total_open_qty = sum(flt(row.get("outstanding_qty")) for row in data)
    return [
        make_summary_item(_("采购行数"), len(data), indicator="Blue", datatype="Int"),
        make_summary_item(_("采购数量"), round_float(total_qty, 6), indicator="Blue", datatype="Float"),
        make_summary_item(_("下单金额"), round_float(total_ordered_amount), indicator="Blue", datatype="Currency"),
        make_summary_item(_("已收货估算金额"), round_float(total_received_amount), indicator="Green", datatype="Currency"),
        make_summary_item(_("未收货估算金额"), round_float(total_open_amount), indicator="Orange", datatype="Currency"),
        make_summary_item(_("未收货数量"), round_float(total_open_qty, 6), indicator="Red", datatype="Float"),
    ]

