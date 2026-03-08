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
        {"label": _("发货单"), "fieldname": "delivery_note", "fieldtype": "Link", "options": "Delivery Note", "width": 140},
        {"label": _("发货日期"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("客户"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": _("公司"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": _("销售订单"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
        {"label": _("发货数量"), "fieldname": "delivered_qty", "fieldtype": "Float", "width": 100},
        {"label": _("耗材数量"), "fieldname": "fulfillment_consumable_qty", "fieldtype": "Float", "width": 100},
        {"label": _("耗材金额"), "fieldname": "fulfillment_consumable_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("手工快递费"), "fieldname": "manual_logistics_fee", "fieldtype": "Currency", "width": 110},
        {"label": _("履约总成本"), "fieldname": "fulfillment_total_cost", "fieldtype": "Currency", "width": 110},
        {"label": _("单件履约成本"), "fieldname": "cost_per_unit", "fieldtype": "Currency", "width": 110},
        {"label": _("耗材出库单"), "fieldname": "fulfillment_consumable_stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 140},
    ]


def get_data(filters: dict[str, object]) -> list[dict[str, object]]:
    conditions = ["dn.docstatus = 1"]
    params: dict[str, object] = {}

    if filters.get("date_from"):
        conditions.append("dn.posting_date >= %(date_from)s")
        params["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("dn.posting_date <= %(date_to)s")
        params["date_to"] = filters["date_to"]
    if filters.get("company"):
        conditions.append("dn.company = %(company)s")
        params["company"] = filters["company"]
    if filters.get("customer"):
        conditions.append("dn.customer = %(customer)s")
        params["customer"] = filters["customer"]

    rows = frappe.db.sql(
        f"""
        select
            dn.name as delivery_note,
            dn.posting_date,
            dn.customer,
            dn.company,
            min(coalesce(dni.against_sales_order, '')) as sales_order,
            sum(coalesce(dni.qty, 0)) as delivered_qty,
            coalesce(dn.fulfillment_consumable_qty, 0) as fulfillment_consumable_qty,
            coalesce(dn.fulfillment_consumable_amount, 0) as fulfillment_consumable_amount,
            coalesce(dn.manual_logistics_fee, 0) as manual_logistics_fee,
            coalesce(dn.fulfillment_total_cost, 0) as fulfillment_total_cost,
            coalesce(dn.fulfillment_consumable_stock_entry, '') as fulfillment_consumable_stock_entry
        from `tabDelivery Note` dn
        left join `tabDelivery Note Item` dni on dni.parent = dn.name
        where {" and ".join(conditions)}
        group by
            dn.name,
            dn.posting_date,
            dn.customer,
            dn.company,
            coalesce(dn.fulfillment_consumable_qty, 0),
            coalesce(dn.fulfillment_consumable_amount, 0),
            coalesce(dn.manual_logistics_fee, 0),
            coalesce(dn.fulfillment_total_cost, 0),
            coalesce(dn.fulfillment_consumable_stock_entry, '')
        order by dn.posting_date desc, dn.modified desc
        """,
        params,
        as_dict=True,
    )

    data: list[dict[str, object]] = []
    for row in rows:
        delivered_qty = flt(row.get("delivered_qty"))
        total_cost = flt(row.get("fulfillment_total_cost"))
        data.append(
            {
                "delivery_note": row.get("delivery_note"),
                "posting_date": row.get("posting_date"),
                "customer": row.get("customer"),
                "company": row.get("company"),
                "sales_order": row.get("sales_order"),
                "delivered_qty": round_float(delivered_qty, 6),
                "fulfillment_consumable_qty": round_float(row.get("fulfillment_consumable_qty"), 6),
                "fulfillment_consumable_amount": round_float(row.get("fulfillment_consumable_amount")),
                "manual_logistics_fee": round_float(row.get("manual_logistics_fee")),
                "fulfillment_total_cost": round_float(total_cost),
                "cost_per_unit": round_float(total_cost / delivered_qty) if delivered_qty else 0,
                "fulfillment_consumable_stock_entry": row.get("fulfillment_consumable_stock_entry"),
            }
        )
    return data


def get_summary(data: list[dict[str, object]]) -> list[dict[str, object]]:
    total_delivered_qty = sum(flt(row.get("delivered_qty")) for row in data)
    total_consumable_amount = sum(flt(row.get("fulfillment_consumable_amount")) for row in data)
    total_logistics_fee = sum(flt(row.get("manual_logistics_fee")) for row in data)
    total_cost = sum(flt(row.get("fulfillment_total_cost")) for row in data)
    avg_cost_per_unit = round(total_cost / total_delivered_qty, 2) if total_delivered_qty else 0
    return [
        make_summary_item(_("发货单数"), len(data), indicator="Blue", datatype="Int"),
        make_summary_item(_("发货数量"), round_float(total_delivered_qty, 6), indicator="Blue", datatype="Float"),
        make_summary_item(_("耗材金额"), round_float(total_consumable_amount), indicator="Green", datatype="Currency"),
        make_summary_item(_("快递费"), round_float(total_logistics_fee), indicator="Orange", datatype="Currency"),
        make_summary_item(_("履约总成本"), round_float(total_cost), indicator="Blue", datatype="Currency"),
        make_summary_item(_("平均单件履约成本"), avg_cost_per_unit, indicator="Red", datatype="Currency"),
    ]

