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
        {"label": _("到货单"), "fieldname": "name", "fieldtype": "Link", "options": "Outsource Receipt", "width": 140},
        {"label": _("到货单号"), "fieldname": "receipt_no", "fieldtype": "Data", "width": 130},
        {"label": _("到货日期"), "fieldname": "receipt_date", "fieldtype": "Date", "width": 100},
        {"label": _("单据状态"), "fieldname": "receipt_status", "fieldtype": "Data", "width": 100},
        {"label": _("关联外包单"), "fieldname": "outsource_order", "fieldtype": "Link", "options": "Outsource Order", "width": 140},
        {"label": _("外包工厂"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
        {"label": _("公司"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": _("款号"), "fieldname": "style", "fieldtype": "Link", "options": "Style", "width": 130},
        {"label": _("款号名称"), "fieldname": "style_name", "fieldtype": "Data", "width": 150},
        {"label": _("收货仓库"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": _("本单到货"), "fieldname": "total_received_qty", "fieldtype": "Float", "width": 100},
        {"label": _("异常行数"), "fieldname": "exception_row_count", "fieldtype": "Int", "width": 90},
        {"label": _("短装数量"), "fieldname": "total_shortage_qty", "fieldtype": "Float", "width": 90},
        {"label": _("错色数量"), "fieldname": "total_wrong_color_qty", "fieldtype": "Float", "width": 90},
        {"label": _("错码数量"), "fieldname": "total_wrong_size_qty", "fieldtype": "Float", "width": 90},
        {"label": _("次品数量"), "fieldname": "total_defective_qty", "fieldtype": "Float", "width": 90},
        {"label": _("待检入库凭证"), "fieldname": "qc_stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 140},
        {"label": _("质检落账凭证"), "fieldname": "final_stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 140},
        {"label": _("质检完成时间"), "fieldname": "qc_completed_at", "fieldtype": "Datetime", "width": 150},
        {"label": _("异常摘要"), "fieldname": "exception_summary", "fieldtype": "Small Text", "width": 220},
    ]


def get_data(filters: dict[str, object]) -> list[dict[str, object]]:
    receipt_filters = _build_filters(filters)
    rows = frappe.get_all(
        "Outsource Receipt",
        filters=receipt_filters,
        fields=[
            "name",
            "receipt_no",
            "receipt_date",
            "receipt_status",
            "outsource_order",
            "supplier",
            "company",
            "style",
            "style_name",
            "warehouse",
            "total_received_qty",
            "exception_row_count",
            "total_shortage_qty",
            "total_wrong_color_qty",
            "total_wrong_size_qty",
            "total_defective_qty",
            "qc_stock_entry",
            "final_stock_entry",
            "qc_completed_at",
            "exception_summary",
        ],
        order_by="receipt_date desc, modified desc",
    )

    data: list[dict[str, object]] = []
    for row in rows:
        data.append(
            {
                "name": row.get("name"),
                "receipt_no": row.get("receipt_no"),
                "receipt_date": row.get("receipt_date"),
                "receipt_status": row.get("receipt_status"),
                "outsource_order": row.get("outsource_order"),
                "supplier": row.get("supplier"),
                "company": row.get("company"),
                "style": row.get("style"),
                "style_name": row.get("style_name"),
                "warehouse": row.get("warehouse"),
                "total_received_qty": round_float(row.get("total_received_qty"), 6),
                "exception_row_count": row.get("exception_row_count") or 0,
                "total_shortage_qty": round_float(row.get("total_shortage_qty"), 6),
                "total_wrong_color_qty": round_float(row.get("total_wrong_color_qty"), 6),
                "total_wrong_size_qty": round_float(row.get("total_wrong_size_qty"), 6),
                "total_defective_qty": round_float(row.get("total_defective_qty"), 6),
                "qc_stock_entry": row.get("qc_stock_entry"),
                "final_stock_entry": row.get("final_stock_entry"),
                "qc_completed_at": row.get("qc_completed_at"),
                "exception_summary": row.get("exception_summary"),
            }
        )
    return data


def get_summary(data: list[dict[str, object]]) -> list[dict[str, object]]:
    receipt_count = len(data)
    exception_receipt_count = sum(1 for row in data if flt(row.get("exception_row_count")) > 0)
    total_received_qty = sum(flt(row.get("total_received_qty")) for row in data)
    total_shortage_qty = sum(flt(row.get("total_shortage_qty")) for row in data)
    total_wrong_color_qty = sum(flt(row.get("total_wrong_color_qty")) for row in data)
    total_wrong_size_qty = sum(flt(row.get("total_wrong_size_qty")) for row in data)
    return [
        make_summary_item(_("到货单数"), receipt_count, indicator="Blue", datatype="Int"),
        make_summary_item(_("异常到货单数"), exception_receipt_count, indicator="Orange", datatype="Int"),
        make_summary_item(_("累计到货"), round_float(total_received_qty, 6), indicator="Green", datatype="Float"),
        make_summary_item(_("累计短装"), round_float(total_shortage_qty, 6), indicator="Red", datatype="Float"),
        make_summary_item(_("累计错色"), round_float(total_wrong_color_qty, 6), indicator="Orange", datatype="Float"),
        make_summary_item(_("累计错码"), round_float(total_wrong_size_qty, 6), indicator="Orange", datatype="Float"),
    ]


def _build_filters(filters: dict[str, object]) -> list[list[object]]:
    receipt_filters: list[list[object]] = []
    if filters.get("date_from"):
        receipt_filters.append(["Outsource Receipt", "receipt_date", ">=", filters["date_from"]])
    if filters.get("date_to"):
        receipt_filters.append(["Outsource Receipt", "receipt_date", "<=", filters["date_to"]])
    if filters.get("supplier"):
        receipt_filters.append(["Outsource Receipt", "supplier", "=", filters["supplier"]])
    if filters.get("style"):
        receipt_filters.append(["Outsource Receipt", "style", "=", filters["style"]])
    if filters.get("receipt_status"):
        receipt_filters.append(["Outsource Receipt", "receipt_status", "=", filters["receipt_status"]])
    if filters.get("company"):
        receipt_filters.append(["Outsource Receipt", "company", "=", filters["company"]])
    return receipt_filters

