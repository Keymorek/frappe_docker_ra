from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from fashion_erp.fashion_stock.report.common import (
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
        {"label": _("销售订单"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
        {"label": _("下单日期"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
        {"label": _("交付日期"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 100},
        {"label": _("客户"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": _("渠道"), "fieldname": "channel", "fieldtype": "Data", "width": 100},
        {"label": _("渠道店铺"), "fieldname": "channel_store", "fieldtype": "Link", "options": "Channel Store", "width": 140},
        {"label": _("外部订单号"), "fieldname": "external_order_id", "fieldtype": "Data", "width": 150},
        {"label": _("履约状态"), "fieldname": "fulfillment_status", "fieldtype": "Data", "width": 100},
        {"label": _("售后工单"), "fieldname": "after_sales_ticket", "fieldtype": "Link", "options": "After Sales Ticket", "width": 130},
        {"label": _("订单金额"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 110},
        {"label": _("订单行数"), "fieldname": "line_count", "fieldtype": "Int", "width": 90},
        {"label": _("订单数量"), "fieldname": "total_qty", "fieldtype": "Float", "width": 100},
        {"label": _("已发货数量"), "fieldname": "delivered_qty", "fieldtype": "Float", "width": 100},
        {"label": _("待发货数量"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 100},
        {"label": _("待发货行数"), "fieldname": "ready_to_ship_lines", "fieldtype": "Int", "width": 90},
    ]


def get_data(filters: dict[str, object]) -> list[dict[str, object]]:
    conditions = ["so.docstatus < 2"]
    params: dict[str, object] = {}

    if filters.get("date_from"):
        conditions.append("so.transaction_date >= %(date_from)s")
        params["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("so.transaction_date <= %(date_to)s")
        params["date_to"] = filters["date_to"]
    if filters.get("channel"):
        conditions.append("coalesce(so.channel, '') = %(channel)s")
        params["channel"] = filters["channel"]
    if filters.get("channel_store"):
        conditions.append("coalesce(so.channel_store, '') = %(channel_store)s")
        params["channel_store"] = filters["channel_store"]
    if filters.get("fulfillment_status"):
        conditions.append("coalesce(so.fulfillment_status, '') = %(fulfillment_status)s")
        params["fulfillment_status"] = filters["fulfillment_status"]
    if filters.get("customer"):
        conditions.append("so.customer = %(customer)s")
        params["customer"] = filters["customer"]

    rows = frappe.db.sql(
        f"""
        select
            so.name as sales_order,
            so.transaction_date,
            so.delivery_date,
            so.customer,
            coalesce(so.channel, '') as channel,
            coalesce(so.channel_store, '') as channel_store,
            coalesce(so.external_order_id, '') as external_order_id,
            coalesce(so.fulfillment_status, '') as fulfillment_status,
            coalesce(so.after_sales_ticket, '') as after_sales_ticket,
            coalesce(so.grand_total, 0) as grand_total,
            count(soi.name) as line_count,
            sum(coalesce(soi.qty, 0)) as total_qty,
            sum(coalesce(soi.delivered_qty, 0)) as delivered_qty,
            sum(
                case
                    when coalesce(soi.qty, 0) > coalesce(soi.delivered_qty, 0)
                    then coalesce(soi.qty, 0) - coalesce(soi.delivered_qty, 0)
                    else 0
                end
            ) as pending_qty,
            sum(
                case
                    when coalesce(soi.fulfillment_status, '') = '待发货' then 1
                    else 0
                end
            ) as ready_to_ship_lines
        from `tabSales Order` so
        left join `tabSales Order Item` soi on soi.parent = so.name
        where {" and ".join(conditions)}
        group by
            so.name,
            so.transaction_date,
            so.delivery_date,
            so.customer,
            coalesce(so.channel, ''),
            coalesce(so.channel_store, ''),
            coalesce(so.external_order_id, ''),
            coalesce(so.fulfillment_status, ''),
            coalesce(so.after_sales_ticket, ''),
            coalesce(so.grand_total, 0)
        order by so.transaction_date desc, so.modified desc
        """,
        params,
        as_dict=True,
    )

    data: list[dict[str, object]] = []
    for row in rows:
        data.append(
            {
                "sales_order": row.get("sales_order"),
                "transaction_date": row.get("transaction_date"),
                "delivery_date": row.get("delivery_date"),
                "customer": row.get("customer"),
                "channel": row.get("channel"),
                "channel_store": row.get("channel_store"),
                "external_order_id": row.get("external_order_id"),
                "fulfillment_status": row.get("fulfillment_status"),
                "after_sales_ticket": row.get("after_sales_ticket"),
                "grand_total": round_float(row.get("grand_total")),
                "line_count": row.get("line_count") or 0,
                "total_qty": round_float(row.get("total_qty"), 6),
                "delivered_qty": round_float(row.get("delivered_qty"), 6),
                "pending_qty": round_float(row.get("pending_qty"), 6),
                "ready_to_ship_lines": row.get("ready_to_ship_lines") or 0,
            }
        )
    return data


def get_summary(data: list[dict[str, object]]) -> list[dict[str, object]]:
    order_count = len(data)
    total_qty = sum(flt(row.get("total_qty")) for row in data)
    delivered_qty = sum(flt(row.get("delivered_qty")) for row in data)
    pending_qty = sum(flt(row.get("pending_qty")) for row in data)
    ready_to_ship_lines = sum(int(row.get("ready_to_ship_lines") or 0) for row in data)
    return [
        make_summary_item(_("订单数"), order_count, indicator="Blue", datatype="Int"),
        make_summary_item(_("订单数量"), round_float(total_qty, 6), indicator="Blue", datatype="Float"),
        make_summary_item(_("已发货数量"), round_float(delivered_qty, 6), indicator="Green", datatype="Float"),
        make_summary_item(_("待发货数量"), round_float(pending_qty, 6), indicator="Orange", datatype="Float"),
        make_summary_item(_("待发货行数"), ready_to_ship_lines, indicator="Red", datatype="Int"),
    ]

