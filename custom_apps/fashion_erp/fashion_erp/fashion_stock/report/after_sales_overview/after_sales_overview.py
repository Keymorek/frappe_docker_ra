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
        {"label": _("售后工单"), "fieldname": "after_sales_ticket", "fieldtype": "Link", "options": "After Sales Ticket", "width": 140},
        {"label": _("售后单号"), "fieldname": "ticket_no", "fieldtype": "Data", "width": 130},
        {"label": _("申请时间"), "fieldname": "apply_time", "fieldtype": "Datetime", "width": 150},
        {"label": _("工单类型"), "fieldname": "ticket_type", "fieldtype": "Data", "width": 100},
        {"label": _("工单状态"), "fieldname": "ticket_status", "fieldtype": "Data", "width": 100},
        {"label": _("优先级"), "fieldname": "priority", "fieldtype": "Data", "width": 80},
        {"label": _("渠道"), "fieldname": "channel", "fieldtype": "Data", "width": 90},
        {"label": _("渠道店铺"), "fieldname": "channel_store", "fieldtype": "Link", "options": "Channel Store", "width": 140},
        {"label": _("外部订单号"), "fieldname": "external_order_id", "fieldtype": "Data", "width": 150},
        {"label": _("销售订单"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
        {"label": _("客户"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": _("退货原因"), "fieldname": "return_reason", "fieldtype": "Link", "options": "Return Reason", "width": 120},
        {"label": _("处理结果"), "fieldname": "return_disposition", "fieldtype": "Link", "options": "Return Disposition", "width": 120},
        {"label": _("退款状态"), "fieldname": "refund_status", "fieldtype": "Data", "width": 100},
        {"label": _("退款金额"), "fieldname": "refund_amount", "fieldtype": "Currency", "width": 100},
        {"label": _("补发销售订单"), "fieldname": "replacement_sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
        {"label": _("处理人"), "fieldname": "handler_user", "fieldtype": "Link", "options": "User", "width": 140},
        {"label": _("申请数量"), "fieldname": "requested_qty", "fieldtype": "Float", "width": 100},
        {"label": _("实收数量"), "fieldname": "received_qty", "fieldtype": "Float", "width": 100},
        {"label": _("可回售数量"), "fieldname": "restock_qty", "fieldtype": "Float", "width": 100},
        {"label": _("次品数量"), "fieldname": "defective_qty", "fieldtype": "Float", "width": 100},
        {"label": _("明细行数"), "fieldname": "line_count", "fieldtype": "Int", "width": 90},
    ]


def get_data(filters: dict[str, object]) -> list[dict[str, object]]:
    conditions = ["1 = 1"]
    params: dict[str, object] = {}

    if filters.get("date_from"):
        conditions.append("date(ticket.apply_time) >= %(date_from)s")
        params["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("date(ticket.apply_time) <= %(date_to)s")
        params["date_to"] = filters["date_to"]
    if filters.get("ticket_type"):
        conditions.append("coalesce(ticket.ticket_type, '') = %(ticket_type)s")
        params["ticket_type"] = filters["ticket_type"]
    if filters.get("ticket_status"):
        conditions.append("coalesce(ticket.ticket_status, '') = %(ticket_status)s")
        params["ticket_status"] = filters["ticket_status"]
    if filters.get("channel_store"):
        conditions.append("coalesce(ticket.channel_store, '') = %(channel_store)s")
        params["channel_store"] = filters["channel_store"]
    if filters.get("handler_user"):
        conditions.append("coalesce(ticket.handler_user, '') = %(handler_user)s")
        params["handler_user"] = filters["handler_user"]

    rows = frappe.db.sql(
        f"""
        select
            ticket.name as after_sales_ticket,
            ticket.ticket_no,
            ticket.apply_time,
            coalesce(ticket.ticket_type, '') as ticket_type,
            coalesce(ticket.ticket_status, '') as ticket_status,
            coalesce(ticket.priority, '') as priority,
            coalesce(ticket.channel, '') as channel,
            coalesce(ticket.channel_store, '') as channel_store,
            coalesce(ticket.external_order_id, '') as external_order_id,
            coalesce(ticket.sales_order, '') as sales_order,
            coalesce(ticket.customer, '') as customer,
            coalesce(ticket.return_reason, '') as return_reason,
            coalesce(ticket.return_disposition, '') as return_disposition,
            coalesce(ticket.refund_status, '') as refund_status,
            coalesce(ticket.refund_amount, 0) as refund_amount,
            coalesce(ticket.replacement_sales_order, '') as replacement_sales_order,
            coalesce(ticket.handler_user, '') as handler_user,
            count(item.name) as line_count,
            sum(coalesce(item.qty, 0)) as requested_qty,
            sum(coalesce(item.received_qty, 0)) as received_qty,
            sum(coalesce(item.restock_qty, 0)) as restock_qty,
            sum(coalesce(item.defective_qty, 0)) as defective_qty
        from `tabAfter Sales Ticket` ticket
        left join `tabAfter Sales Item` item on item.parent = ticket.name
        where {" and ".join(conditions)}
        group by
            ticket.name,
            ticket.ticket_no,
            ticket.apply_time,
            coalesce(ticket.ticket_type, ''),
            coalesce(ticket.ticket_status, ''),
            coalesce(ticket.priority, ''),
            coalesce(ticket.channel, ''),
            coalesce(ticket.channel_store, ''),
            coalesce(ticket.external_order_id, ''),
            coalesce(ticket.sales_order, ''),
            coalesce(ticket.customer, ''),
            coalesce(ticket.return_reason, ''),
            coalesce(ticket.return_disposition, ''),
            coalesce(ticket.refund_status, ''),
            coalesce(ticket.refund_amount, 0),
            coalesce(ticket.replacement_sales_order, ''),
            coalesce(ticket.handler_user, '')
        order by ticket.apply_time desc, ticket.modified desc
        """,
        params,
        as_dict=True,
    )

    data: list[dict[str, object]] = []
    for row in rows:
        data.append(
            {
                "after_sales_ticket": row.get("after_sales_ticket"),
                "ticket_no": row.get("ticket_no"),
                "apply_time": row.get("apply_time"),
                "ticket_type": row.get("ticket_type"),
                "ticket_status": row.get("ticket_status"),
                "priority": row.get("priority"),
                "channel": row.get("channel"),
                "channel_store": row.get("channel_store"),
                "external_order_id": row.get("external_order_id"),
                "sales_order": row.get("sales_order"),
                "customer": row.get("customer"),
                "return_reason": row.get("return_reason"),
                "return_disposition": row.get("return_disposition"),
                "refund_status": row.get("refund_status"),
                "refund_amount": round_float(row.get("refund_amount")),
                "replacement_sales_order": row.get("replacement_sales_order"),
                "handler_user": row.get("handler_user"),
                "line_count": row.get("line_count") or 0,
                "requested_qty": round_float(row.get("requested_qty"), 6),
                "received_qty": round_float(row.get("received_qty"), 6),
                "restock_qty": round_float(row.get("restock_qty"), 6),
                "defective_qty": round_float(row.get("defective_qty"), 6),
            }
        )
    return data


def get_summary(data: list[dict[str, object]]) -> list[dict[str, object]]:
    ticket_count = len(data)
    requested_qty = sum(flt(row.get("requested_qty")) for row in data)
    received_qty = sum(flt(row.get("received_qty")) for row in data)
    refund_amount = sum(flt(row.get("refund_amount")) for row in data)
    pending_refund_count = sum(1 for row in data if row.get("refund_status") == "待退款")
    return [
        make_summary_item(_("售后工单数"), ticket_count, indicator="Blue", datatype="Int"),
        make_summary_item(_("申请数量"), round_float(requested_qty, 6), indicator="Blue", datatype="Float"),
        make_summary_item(_("实收数量"), round_float(received_qty, 6), indicator="Green", datatype="Float"),
        make_summary_item(_("退款金额"), round_float(refund_amount), indicator="Orange", datatype="Currency"),
        make_summary_item(_("待退款工单"), pending_refund_count, indicator="Red", datatype="Int"),
    ]

