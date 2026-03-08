from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

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
        {"label": _("外包单"), "fieldname": "outsource_order", "fieldtype": "Link", "options": "Outsource Order", "width": 140},
        {"label": _("外包单号"), "fieldname": "order_no", "fieldtype": "Data", "width": 130},
        {"label": _("下单日期"), "fieldname": "order_date", "fieldtype": "Date", "width": 100},
        {"label": _("预计到货"), "fieldname": "expected_delivery_date", "fieldtype": "Date", "width": 100},
        {"label": _("单据状态"), "fieldname": "order_status", "fieldtype": "Data", "width": 100},
        {"label": _("外包工厂"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
        {"label": _("款号"), "fieldname": "style", "fieldtype": "Link", "options": "Style", "width": 130},
        {"label": _("款号名称"), "fieldname": "style_name", "fieldtype": "Data", "width": 150},
        {"label": _("下单数量"), "fieldname": "ordered_qty", "fieldtype": "Float", "width": 100},
        {"label": _("累计到货"), "fieldname": "received_qty", "fieldtype": "Float", "width": 100},
        {"label": _("未到货数量"), "fieldname": "open_qty", "fieldtype": "Float", "width": 100},
        {"label": _("到货进度%"), "fieldname": "received_percent", "fieldtype": "Percent", "width": 100},
        {"label": _("预计单件成本"), "fieldname": "unit_estimated_cost", "fieldtype": "Currency", "width": 110},
        {"label": _("预计总成本"), "fieldname": "total_estimated_cost", "fieldtype": "Currency", "width": 110},
        {"label": _("已到货估算成本"), "fieldname": "estimated_received_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("未到货估算成本"), "fieldname": "estimated_open_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("是否逾期"), "fieldname": "is_overdue", "fieldtype": "Check", "width": 80},
    ]


def get_data(filters: dict[str, object]) -> list[dict[str, object]]:
    conditions = ["1 = 1"]
    params: dict[str, object] = {}

    if filters.get("date_from"):
        conditions.append("order_date >= %(date_from)s")
        params["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("order_date <= %(date_to)s")
        params["date_to"] = filters["date_to"]
    if filters.get("supplier"):
        conditions.append("supplier = %(supplier)s")
        params["supplier"] = filters["supplier"]
    if filters.get("style"):
        conditions.append("style = %(style)s")
        params["style"] = filters["style"]
    if filters.get("order_status"):
        conditions.append("order_status = %(order_status)s")
        params["order_status"] = filters["order_status"]
    elif not is_checked(filters, "include_closed_orders", default=False):
        conditions.append("order_status not in ('已完成', '已取消')")

    rows = frappe.get_all(
        "Outsource Order",
        filters=conditions_to_filters(conditions, params),
        fields=[
            "name",
            "order_no",
            "order_date",
            "expected_delivery_date",
            "order_status",
            "supplier",
            "style",
            "style_name",
            "ordered_qty",
            "received_qty",
            "unit_estimated_cost",
            "total_estimated_cost",
        ],
        order_by="order_date desc, modified desc",
    )

    today = getdate(nowdate())
    data: list[dict[str, object]] = []
    for row in rows:
        ordered_qty = flt(row.get("ordered_qty"))
        received_qty = flt(row.get("received_qty"))
        open_qty = max(ordered_qty - received_qty, 0)
        unit_estimated_cost = flt(row.get("unit_estimated_cost"))
        received_percent = round((received_qty / ordered_qty) * 100, 2) if ordered_qty else 0
        expected_delivery_date = row.get("expected_delivery_date")
        is_overdue_row = 0
        if expected_delivery_date and row.get("order_status") not in ("已完成", "已取消"):
            is_overdue_row = 1 if getdate(expected_delivery_date) < today and open_qty > 0 else 0

        payload = {
            "outsource_order": row.get("name"),
            "order_no": row.get("order_no"),
            "order_date": row.get("order_date"),
            "expected_delivery_date": expected_delivery_date,
            "order_status": row.get("order_status"),
            "supplier": row.get("supplier"),
            "style": row.get("style"),
            "style_name": row.get("style_name"),
            "ordered_qty": round_float(ordered_qty, 6),
            "received_qty": round_float(received_qty, 6),
            "open_qty": round_float(open_qty, 6),
            "received_percent": received_percent,
            "unit_estimated_cost": round_float(unit_estimated_cost),
            "total_estimated_cost": round_float(row.get("total_estimated_cost")),
            "estimated_received_amount": round_float(received_qty * unit_estimated_cost),
            "estimated_open_amount": round_float(open_qty * unit_estimated_cost),
            "is_overdue": is_overdue_row,
        }
        if is_checked(filters, "overdue_only", default=False) and not payload["is_overdue"]:
            continue
        data.append(payload)
    return data


def get_summary(data: list[dict[str, object]]) -> list[dict[str, object]]:
    total_estimated_cost = sum(flt(row.get("total_estimated_cost")) for row in data)
    estimated_received_amount = sum(flt(row.get("estimated_received_amount")) for row in data)
    estimated_open_amount = sum(flt(row.get("estimated_open_amount")) for row in data)
    overdue_count = sum(1 for row in data if row.get("is_overdue"))
    avg_received_percent = round(
        sum(flt(row.get("received_percent")) for row in data) / len(data),
        2,
    ) if data else 0
    return [
        make_summary_item(_("外包单数"), len(data), indicator="Blue", datatype="Int"),
        make_summary_item(_("预计总成本"), round_float(total_estimated_cost), indicator="Blue", datatype="Currency"),
        make_summary_item(_("已到货估算成本"), round_float(estimated_received_amount), indicator="Green", datatype="Currency"),
        make_summary_item(_("未到货估算成本"), round_float(estimated_open_amount), indicator="Orange", datatype="Currency"),
        make_summary_item(_("平均到货进度%"), avg_received_percent, indicator="Blue", datatype="Percent"),
        make_summary_item(_("逾期外包单"), overdue_count, indicator="Red", datatype="Int"),
    ]


def conditions_to_filters(conditions: list[str], params: dict[str, object]) -> list[list[object]]:
    filters: list[list[object]] = []
    for key in ("date_from", "date_to", "supplier", "style", "order_status"):
        if key not in params:
            continue
        if key == "date_from":
            filters.append(["Outsource Order", "order_date", ">=", params[key]])
        elif key == "date_to":
            filters.append(["Outsource Order", "order_date", "<=", params[key]])
        else:
            fieldname = "order_status" if key == "order_status" else key
            filters.append(["Outsource Order", fieldname, "=", params[key]])
    if "order_status not in ('已完成', '已取消')" in conditions:
        filters.append(["Outsource Order", "order_status", "not in", ["已完成", "已取消"]])
    return filters

