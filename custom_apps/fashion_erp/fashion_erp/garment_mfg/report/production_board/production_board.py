from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from fashion_erp.garment_mfg.services.production_service import (
    PRODUCTION_STAGE_INDEX,
    PRODUCTION_STAGE_OPTIONS,
)
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
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns() -> list[dict[str, object]]:
    return [
        {"label": _("生产卡"), "fieldname": "production_ticket", "fieldtype": "Link", "options": "Production Ticket", "width": 140},
        {"label": _("款号"), "fieldname": "style", "fieldtype": "Link", "options": "Style", "width": 130},
        {"label": _("颜色编码"), "fieldname": "color_code", "fieldtype": "Data", "width": 90},
        {"label": _("数量"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
        {"label": _("阶段"), "fieldname": "stage", "fieldtype": "Data", "width": 90},
        {"label": _("状态"), "fieldname": "status", "fieldtype": "Data", "width": 90},
        {"label": _("进度%"), "fieldname": "progress_percent", "fieldtype": "Percent", "width": 80},
        {"label": _("排期状态"), "fieldname": "schedule_status", "fieldtype": "Data", "width": 110},
        {"label": _("延期天数"), "fieldname": "delay_days", "fieldtype": "Int", "width": 80},
        {"label": _("计划开始"), "fieldname": "planned_start_date", "fieldtype": "Date", "width": 100},
        {"label": _("计划结束"), "fieldname": "planned_end_date", "fieldtype": "Date", "width": 100},
        {"label": _("实际开始"), "fieldname": "actual_start_date", "fieldtype": "Date", "width": 100},
        {"label": _("实际结束"), "fieldname": "actual_end_date", "fieldtype": "Date", "width": 100},
        {"label": _("日志数"), "fieldname": "stage_log_count", "fieldtype": "Int", "width": 80},
        {"label": _("最近日志阶段"), "fieldname": "last_log_stage", "fieldtype": "Data", "width": 110},
        {"label": _("最近日志时间"), "fieldname": "last_log_time", "fieldtype": "Datetime", "width": 150},
        {"label": _("最近产出"), "fieldname": "last_qty_out", "fieldtype": "Float", "width": 90},
        {"label": _("不良数量"), "fieldname": "defect_qty", "fieldtype": "Float", "width": 90},
        {"label": _("物料清单"), "fieldname": "bom_no", "fieldtype": "Link", "options": "BOM", "width": 140},
        {"label": _("生产工单"), "fieldname": "work_order", "fieldtype": "Link", "options": "Work Order", "width": 140},
        {"label": _("库存联动次数"), "fieldname": "stock_entry_count", "fieldtype": "Int", "width": 100},
        {"label": _("最近库存凭证"), "fieldname": "latest_stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 140},
        {"label": _("最近库存类型"), "fieldname": "latest_stock_entry_type", "fieldtype": "Data", "width": 120},
        {"label": _("供应商"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
    ]


def get_data(filters: dict[str, object]) -> list[dict[str, object]]:
    ticket_rows = frappe.get_all(
        "Production Ticket",
        filters=_build_ticket_filters(filters),
        fields=[
            "name",
            "style",
            "color_code",
            "qty",
            "stage",
            "status",
            "planned_start_date",
            "planned_end_date",
            "actual_start_date",
            "actual_end_date",
            "defect_qty",
            "bom_no",
            "work_order",
            "supplier",
        ],
        order_by="planned_end_date asc, modified desc",
    )

    ticket_names = [row.get("name") for row in ticket_rows if row.get("name")]
    stage_log_map = _get_stage_log_map(ticket_names)
    stock_entry_map = _get_stock_entry_map(ticket_names)
    today = getdate(nowdate())
    data: list[dict[str, object]] = []

    for row in ticket_rows:
        production_ticket = row.get("name")
        stage_log_meta = stage_log_map.get(production_ticket, {})
        stock_entry_meta = stock_entry_map.get(production_ticket, {})
        schedule_status = _build_schedule_status(row, today)
        delay_days = _build_delay_days(row, today)
        payload = {
            "production_ticket": production_ticket,
            "style": row.get("style"),
            "color_code": row.get("color_code"),
            "qty": round_float(row.get("qty"), 6),
            "stage": row.get("stage"),
            "status": row.get("status"),
            "progress_percent": _build_progress_percent(row.get("stage")),
            "schedule_status": schedule_status,
            "delay_days": delay_days,
            "planned_start_date": row.get("planned_start_date"),
            "planned_end_date": row.get("planned_end_date"),
            "actual_start_date": row.get("actual_start_date"),
            "actual_end_date": row.get("actual_end_date"),
            "stage_log_count": stage_log_meta.get("stage_log_count", 0),
            "last_log_stage": stage_log_meta.get("last_log_stage", ""),
            "last_log_time": stage_log_meta.get("last_log_time"),
            "last_qty_out": round_float(stage_log_meta.get("last_qty_out"), 6),
            "defect_qty": round_float(row.get("defect_qty"), 6),
            "bom_no": row.get("bom_no"),
            "work_order": row.get("work_order"),
            "stock_entry_count": stock_entry_meta.get("stock_entry_count", 0),
            "latest_stock_entry": stock_entry_meta.get("latest_stock_entry", ""),
            "latest_stock_entry_type": stock_entry_meta.get("latest_stock_entry_type", ""),
            "supplier": row.get("supplier"),
        }
        if is_checked(filters, "only_open", default=False) and payload["status"] in ("已完成", "已取消"):
            continue
        if is_checked(filters, "only_overdue", default=False) and payload["delay_days"] <= 0:
            continue
        data.append(payload)
    return data


def get_chart(data: list[dict[str, object]]) -> dict[str, object] | None:
    if not data:
        return None

    labels = list(PRODUCTION_STAGE_OPTIONS)
    values = [sum(1 for row in data if row.get("stage") == stage) for stage in labels]
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("生产卡数"),
                    "values": values,
                }
            ],
        },
        "type": "bar",
        "colors": ["#1F7A8C"],
    }


def get_summary(data: list[dict[str, object]]) -> list[dict[str, object]]:
    total_qty = sum(flt(row.get("qty")) for row in data)
    in_progress_count = sum(1 for row in data if row.get("status") == "进行中")
    delayed_count = sum(1 for row in data if cint(row.get("delay_days")) > 0)
    linked_bom_count = sum(1 for row in data if row.get("bom_no"))
    linked_work_order_count = sum(1 for row in data if row.get("work_order"))
    linked_stock_entry_count = sum(1 for row in data if cint(row.get("stock_entry_count")) > 0)
    return [
        make_summary_item(_("生产卡数"), len(data), indicator="Blue", datatype="Int"),
        make_summary_item(_("累计数量"), round_float(total_qty, 6), indicator="Blue", datatype="Float"),
        make_summary_item(_("进行中"), in_progress_count, indicator="Green", datatype="Int"),
        make_summary_item(_("延期卡数"), delayed_count, indicator="Red", datatype="Int"),
        make_summary_item(_("已建 BOM"), linked_bom_count, indicator="Blue", datatype="Int"),
        make_summary_item(_("已建工单"), linked_work_order_count, indicator="Blue", datatype="Int"),
        make_summary_item(_("已联动库存"), linked_stock_entry_count, indicator="Orange", datatype="Int"),
    ]


def _build_ticket_filters(filters: dict[str, object]) -> list[list[object]]:
    ticket_filters: list[list[object]] = []
    if filters.get("style"):
        ticket_filters.append(["Production Ticket", "style", "=", filters["style"]])
    if filters.get("supplier"):
        ticket_filters.append(["Production Ticket", "supplier", "=", filters["supplier"]])
    if filters.get("stage"):
        ticket_filters.append(["Production Ticket", "stage", "=", filters["stage"]])
    if filters.get("status"):
        ticket_filters.append(["Production Ticket", "status", "=", filters["status"]])
    if filters.get("planned_date_from"):
        ticket_filters.append(["Production Ticket", "planned_start_date", ">=", filters["planned_date_from"]])
    if filters.get("planned_date_to"):
        ticket_filters.append(["Production Ticket", "planned_end_date", "<=", filters["planned_date_to"]])
    return ticket_filters


def _get_stage_log_map(ticket_names: list[str]) -> dict[str, dict[str, object]]:
    if not ticket_names:
        return {}

    rows = frappe.get_all(
        "Production Stage Log",
        filters=[
            ["Production Stage Log", "parent", "in", ticket_names],
            ["Production Stage Log", "parenttype", "=", "Production Ticket"],
        ],
        fields=["parent", "stage", "qty_out", "log_time"],
        order_by="log_time desc, idx desc",
    )

    stage_log_map: dict[str, dict[str, object]] = {}
    for row in rows:
        ticket_name = row.get("parent")
        if not ticket_name:
            continue

        bucket = stage_log_map.setdefault(
            ticket_name,
            {
                "stage_log_count": 0,
                "last_log_stage": "",
                "last_log_time": None,
                "last_qty_out": 0,
                "_last_key": ("", ""),
            },
        )
        bucket["stage_log_count"] += 1
        log_key = (str(row.get("log_time") or ""), str(row.get("stage") or ""))
        if log_key >= bucket["_last_key"]:
            bucket["_last_key"] = log_key
            bucket["last_log_stage"] = row.get("stage") or ""
            bucket["last_log_time"] = row.get("log_time")
            bucket["last_qty_out"] = flt(row.get("qty_out"))

    for bucket in stage_log_map.values():
        bucket.pop("_last_key", None)
    return stage_log_map


def _get_stock_entry_map(ticket_names: list[str]) -> dict[str, dict[str, object]]:
    if not ticket_names:
        return {}

    detail_rows = frappe.get_all(
        "Stock Entry Detail",
        filters=[
            ["Stock Entry Detail", "production_ticket", "in", ticket_names],
            ["Stock Entry Detail", "parenttype", "=", "Stock Entry"],
        ],
        fields=["parent", "production_ticket"],
        order_by="modified desc, idx desc",
    )

    stock_entry_names = sorted({row.get("parent") for row in detail_rows if row.get("parent")})
    if not stock_entry_names:
        return {}

    stock_entries = frappe.get_all(
        "Stock Entry",
        filters=[["Stock Entry", "name", "in", stock_entry_names]],
        fields=["name", "stock_entry_type", "purpose", "posting_date", "posting_time", "docstatus"],
        order_by="posting_date desc, posting_time desc, modified desc",
    )
    stock_entry_map = {row.get("name"): row for row in stock_entries if row.get("name")}

    result: dict[str, dict[str, object]] = {}
    for row in detail_rows:
        ticket_name = row.get("production_ticket")
        stock_entry_name = row.get("parent")
        stock_entry = stock_entry_map.get(stock_entry_name)
        if not ticket_name or not stock_entry or cint(stock_entry.get("docstatus")) == 2:
            continue

        bucket = result.setdefault(
            ticket_name,
            {
                "stock_entry_count": 0,
                "latest_stock_entry": "",
                "latest_stock_entry_type": "",
                "_stock_entries": set(),
                "_latest_key": ("", "", ""),
            },
        )

        if stock_entry_name not in bucket["_stock_entries"]:
            bucket["_stock_entries"].add(stock_entry_name)
            bucket["stock_entry_count"] += 1

        stock_key = (
            str(stock_entry.get("posting_date") or ""),
            str(stock_entry.get("posting_time") or ""),
            str(stock_entry_name or ""),
        )
        if stock_key >= bucket["_latest_key"]:
            bucket["_latest_key"] = stock_key
            bucket["latest_stock_entry"] = stock_entry_name
            bucket["latest_stock_entry_type"] = (
                stock_entry.get("stock_entry_type") or stock_entry.get("purpose") or ""
            )

    for bucket in result.values():
        bucket.pop("_stock_entries", None)
        bucket.pop("_latest_key", None)
    return result


def _build_progress_percent(stage: str | None) -> float:
    max_stage_index = max(PRODUCTION_STAGE_INDEX.values()) or 1
    return round((PRODUCTION_STAGE_INDEX.get(stage or "计划", 0) / max_stage_index) * 100, 2)


def _build_schedule_status(row: dict[str, object], today) -> str:
    status = row.get("status")
    planned_end_date = _get_optional_date(row.get("planned_end_date"))
    if status == "已取消":
        return "已取消"
    if not planned_end_date:
        return "未排期"
    if status == "已完成":
        actual_end_date = _get_optional_date(row.get("actual_end_date")) or today
        return "已延期完成" if actual_end_date > planned_end_date else "按期完成"
    if today > planned_end_date:
        return "已逾期"
    if today == planned_end_date:
        return "今日到期"
    return "按计划"


def _build_delay_days(row: dict[str, object], today) -> int:
    planned_end_date = _get_optional_date(row.get("planned_end_date"))
    if not planned_end_date:
        return 0

    reference_date = today
    if row.get("status") == "已完成":
        reference_date = _get_optional_date(row.get("actual_end_date")) or today
    return max((reference_date - planned_end_date).days, 0)


def _get_optional_date(value):
    if not value:
        return None
    return getdate(value)
