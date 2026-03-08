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
from fashion_erp.fashion_stock.services.outsource_service import get_outsource_supply_summary


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
        {"label": _("单据状态"), "fieldname": "order_status", "fieldtype": "Data", "width": 100},
        {"label": _("下单日期"), "fieldname": "order_date", "fieldtype": "Date", "width": 100},
        {"label": _("预计到货"), "fieldname": "expected_delivery_date", "fieldtype": "Date", "width": 100},
        {"label": _("外包工厂"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
        {"label": _("款号"), "fieldname": "style", "fieldtype": "Link", "options": "Style", "width": 130},
        {"label": _("款号名称"), "fieldname": "style_name", "fieldtype": "Data", "width": 150},
        {"label": _("物料"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("物料名称"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
        {"label": _("物料用途"), "fieldname": "item_usage_type", "fieldtype": "Data", "width": 100},
        {"label": _("需求数量"), "fieldname": "required_qty", "fieldtype": "Float", "width": 100},
        {"label": _("已备货"), "fieldname": "prepared_qty", "fieldtype": "Float", "width": 90},
        {"label": _("人工已发"), "fieldname": "issued_qty", "fieldtype": "Float", "width": 90},
        {"label": _("现货"), "fieldname": "on_hand_qty", "fieldtype": "Float", "width": 90},
        {"label": _("在途"), "fieldname": "on_order_qty", "fieldtype": "Float", "width": 90},
        {"label": _("待备货"), "fieldname": "to_prepare_qty", "fieldtype": "Float", "width": 90},
        {"label": _("待发料"), "fieldname": "to_issue_qty", "fieldtype": "Float", "width": 90},
        {"label": _("待采购"), "fieldname": "to_purchase_qty", "fieldtype": "Float", "width": 90},
        {"label": _("供料状态"), "fieldname": "supply_status", "fieldtype": "Data", "width": 100},
        {"label": _("仓库范围"), "fieldname": "warehouse_scope", "fieldtype": "Data", "width": 160},
        {"label": _("库位"), "fieldname": "locations", "fieldtype": "Data", "width": 160},
    ]


def get_data(filters: dict[str, object]) -> list[dict[str, object]]:
    order_filters = _build_order_filters(filters)
    orders = frappe.get_all(
        "Outsource Order",
        filters=order_filters,
        fields=[
            "name",
            "order_no",
            "order_status",
            "order_date",
            "expected_delivery_date",
            "supplier",
            "style",
            "style_name",
        ],
        order_by="expected_delivery_date asc, order_date asc, modified asc",
    )

    data: list[dict[str, object]] = []
    for order in orders:
        supply_summary = get_outsource_supply_summary(order["name"])
        for row in supply_summary.get("rows", []):
            if filters.get("item_code") and row.get("item_code") != filters["item_code"]:
                continue
            if filters.get("supply_status") and row.get("status") != filters["supply_status"]:
                continue
            data.append(
                {
                    "outsource_order": order["name"],
                    "order_no": order.get("order_no"),
                    "order_status": order.get("order_status"),
                    "order_date": order.get("order_date"),
                    "expected_delivery_date": order.get("expected_delivery_date"),
                    "supplier": order.get("supplier"),
                    "style": order.get("style"),
                    "style_name": order.get("style_name"),
                    "item_code": row.get("item_code"),
                    "item_name": row.get("item_name"),
                    "item_usage_type": _guess_item_usage_type(row),
                    "required_qty": round_float(row.get("required_qty"), 6),
                    "prepared_qty": round_float(row.get("prepared_qty"), 6),
                    "issued_qty": round_float(row.get("issued_qty"), 6),
                    "on_hand_qty": round_float(row.get("on_hand_qty"), 6),
                    "on_order_qty": round_float(row.get("on_order_qty"), 6),
                    "to_prepare_qty": round_float(row.get("to_prepare_qty"), 6),
                    "to_issue_qty": round_float(row.get("to_issue_qty"), 6),
                    "to_purchase_qty": round_float(row.get("to_purchase_qty"), 6),
                    "supply_status": row.get("status"),
                    "warehouse_scope": row.get("warehouse_scope"),
                    "locations": row.get("locations"),
                }
            )
    return data


def get_summary(data: list[dict[str, object]]) -> list[dict[str, object]]:
    shortage_line_count = sum(1 for row in data if flt(row.get("to_purchase_qty")) > 0)
    total_required_qty = sum(flt(row.get("required_qty")) for row in data)
    total_on_hand_qty = sum(flt(row.get("on_hand_qty")) for row in data)
    total_on_order_qty = sum(flt(row.get("on_order_qty")) for row in data)
    total_to_purchase_qty = sum(flt(row.get("to_purchase_qty")) for row in data)
    return [
        make_summary_item(_("外包供料行数"), len(data), indicator="Blue", datatype="Int"),
        make_summary_item(_("需求数量"), round_float(total_required_qty, 6), indicator="Blue", datatype="Float"),
        make_summary_item(_("现货数量"), round_float(total_on_hand_qty, 6), indicator="Green", datatype="Float"),
        make_summary_item(_("在途数量"), round_float(total_on_order_qty, 6), indicator="Orange", datatype="Float"),
        make_summary_item(_("待采购数量"), round_float(total_to_purchase_qty, 6), indicator="Red", datatype="Float"),
        make_summary_item(_("缺料行数"), shortage_line_count, indicator="Red", datatype="Int"),
    ]


def _build_order_filters(filters: dict[str, object]) -> dict[str, object]:
    order_filters: dict[str, object] = {}
    if filters.get("supplier"):
        order_filters["supplier"] = filters["supplier"]
    if filters.get("style"):
        order_filters["style"] = filters["style"]
    if filters.get("order_status"):
        order_filters["order_status"] = filters["order_status"]
    elif not is_checked(filters, "include_closed_orders", default=False):
        order_filters["order_status"] = ["not in", ["已完成", "已取消"]]
    return order_filters


def _guess_item_usage_type(row: dict[str, object]) -> str:
    warehouse_scope = row.get("warehouse_scope") or ""
    if row.get("locations"):
        return _("原辅料")
    if warehouse_scope == _("全部仓库"):
        return _("原辅料")
    return _("原辅料")

