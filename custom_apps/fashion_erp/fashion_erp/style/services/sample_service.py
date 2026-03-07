from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, now_datetime, nowdate

from fashion_erp.style.services.style_service import (
    coerce_non_negative_float,
    ensure_enabled_link,
    ensure_link_exists,
    normalize_select,
    normalize_text,
)


SAMPLE_TICKET_TYPES = ("首样", "修改样", "确认样", "拍摄样", "产前样", "其他")
SAMPLE_TICKET_TYPE_ALIASES = {
    "FIRST_SAMPLE": "首样",
    "REVISION_SAMPLE": "修改样",
    "CONFIRM_SAMPLE": "确认样",
    "PHOTO_SAMPLE": "拍摄样",
    "PP_SAMPLE": "产前样",
    "OTHER": "其他",
}
SAMPLE_TICKET_STATUSES = ("新建", "已下发", "打样中", "待评审", "需返修", "已确认", "已取消")
SAMPLE_TICKET_STATUS_ALIASES = {
    "NEW": "新建",
    "ISSUED": "已下发",
    "IN_PROGRESS": "打样中",
    "IN_REVIEW": "待评审",
    "REVISION_REQUIRED": "需返修",
    "CONFIRMED": "已确认",
    "CANCELLED": "已取消",
}
SAMPLE_TICKET_PRIORITIES = ("低", "普通", "高", "紧急")
SAMPLE_TICKET_PRIORITY_ALIASES = {
    "Low": "低",
    "Normal": "普通",
    "High": "高",
    "Urgent": "紧急",
}
SAMPLE_TICKET_LOG_ACTIONS = (
    "创建",
    "下发",
    "开始打样",
    "提交评审",
    "要求返修",
    "确认样品",
    "取消",
    "状态变更",
    "备注",
)
SAMPLE_TICKET_LOG_ACTION_ALIASES = {
    "CREATE": "创建",
    "ISSUE": "下发",
    "START": "开始打样",
    "SUBMIT_REVIEW": "提交评审",
    "REQUEST_REVISION": "要求返修",
    "CONFIRM": "确认样品",
    "CANCEL": "取消",
    "STATUS_CHANGE": "状态变更",
    "COMMENT": "备注",
}


def autoname_sample_ticket(doc) -> None:
    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.ticket_no = doc.name
        return

    reference_dt = _normalize_date(getattr(doc, "requested_date", None), use_today=True)
    prefix = f"{reference_dt.strftime('%Y%m%d')}DY"
    ticket_no = _make_daily_sequence("Sample Ticket", prefix)
    doc.name = ticket_no
    doc.ticket_no = ticket_no


def validate_sample_ticket(doc) -> None:
    doc.ticket_no = normalize_text(doc.ticket_no)
    doc.sample_type = normalize_select(
        doc.sample_type,
        "打样类型",
        SAMPLE_TICKET_TYPES,
        default="首样",
        alias_map=SAMPLE_TICKET_TYPE_ALIASES,
    )
    doc.sample_status = normalize_select(
        doc.sample_status,
        "打样状态",
        SAMPLE_TICKET_STATUSES,
        default="新建",
        alias_map=SAMPLE_TICKET_STATUS_ALIASES,
    )
    doc.priority = normalize_select(
        doc.priority,
        "优先级",
        SAMPLE_TICKET_PRIORITIES,
        default="普通",
        alias_map=SAMPLE_TICKET_PRIORITY_ALIASES,
    )
    doc.style = normalize_text(doc.style)
    doc.style_name = normalize_text(doc.style_name)
    doc.item_template = normalize_text(doc.item_template)
    doc.color = normalize_text(doc.color)
    doc.color_name = normalize_text(doc.color_name)
    doc.color_code = normalize_text(doc.color_code)
    doc.requested_by = normalize_text(doc.requested_by) or frappe.session.user
    doc.handler_user = normalize_text(doc.handler_user) or doc.requested_by
    doc.supplier = normalize_text(doc.supplier)
    doc.requested_date = _normalize_date(doc.requested_date, use_today=True)
    doc.expected_finish_date = _normalize_date(doc.expected_finish_date)
    doc.finished_at = _normalize_datetime(doc.finished_at)
    doc.sample_qty = _coerce_positive_int(doc.sample_qty, "打样数量")
    doc.estimated_cost = coerce_non_negative_float(doc.estimated_cost, "预计成本")
    doc.actual_cost = coerce_non_negative_float(doc.actual_cost, "实际成本")
    doc.sample_note = normalize_text(doc.sample_note)
    doc.review_note = normalize_text(doc.review_note)

    _validate_links(doc)
    _sync_from_style(doc)
    _sync_from_color(doc)
    _normalize_logs(doc)
    _append_system_logs(doc)
    _validate_dates(doc)

    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.ticket_no = doc.name


def sync_sample_ticket_number(doc) -> None:
    if doc.name and doc.ticket_no != doc.name:
        doc.db_set("ticket_no", doc.name, update_modified=False)
        doc.ticket_no = doc.name


def submit_sample_ticket(ticket_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_sample_ticket_doc(ticket_name)
    _ensure_sample_ticket_mutable(doc)
    if doc.sample_status not in ("新建", "需返修"):
        frappe.throw(_("只有新建或需返修的打样单才能下发。"))

    previous_status = doc.sample_status
    doc.sample_status = "已下发"
    _append_log(
        doc,
        action_type="下发",
        from_status=previous_status,
        to_status=doc.sample_status,
        note=normalize_text(note) or _("打样任务已下发。"),
    )
    return _save_sample_action(doc, _("打样单已下发。"))


def start_sample_ticket(ticket_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_sample_ticket_doc(ticket_name)
    _ensure_sample_ticket_mutable(doc)
    if doc.sample_status != "已下发":
        frappe.throw(_("只有已下发的打样单才能开始打样。"))

    previous_status = doc.sample_status
    doc.sample_status = "打样中"
    _append_log(
        doc,
        action_type="开始打样",
        from_status=previous_status,
        to_status=doc.sample_status,
        note=normalize_text(note) or _("打样已开始。"),
    )
    return _save_sample_action(doc, _("打样单已进入打样中状态。"))


def submit_sample_ticket_for_review(
    ticket_name: str,
    *,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_sample_ticket_doc(ticket_name)
    _ensure_sample_ticket_mutable(doc)
    if doc.sample_status != "打样中":
        frappe.throw(_("只有打样中的单据才能提交评审。"))

    previous_status = doc.sample_status
    doc.sample_status = "待评审"
    _append_log(
        doc,
        action_type="提交评审",
        from_status=previous_status,
        to_status=doc.sample_status,
        note=normalize_text(note) or _("样品已提交评审。"),
    )
    return _save_sample_action(doc, _("打样单已提交评审。"))


def request_sample_revision(
    ticket_name: str,
    *,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_sample_ticket_doc(ticket_name)
    _ensure_sample_ticket_mutable(doc)
    if doc.sample_status != "待评审":
        frappe.throw(_("只有待评审的打样单才能要求返修。"))

    previous_status = doc.sample_status
    doc.sample_status = "需返修"
    if normalize_text(note):
        doc.review_note = normalize_text(note)
    _append_log(
        doc,
        action_type="要求返修",
        from_status=previous_status,
        to_status=doc.sample_status,
        note=normalize_text(note) or _("样品评审未通过，已要求返修。"),
    )
    return _save_sample_action(doc, _("打样单已转为需返修状态。"))


def confirm_sample_ticket(
    ticket_name: str,
    *,
    actual_cost: float | str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_sample_ticket_doc(ticket_name)
    _ensure_sample_ticket_mutable(doc)
    if doc.sample_status != "待评审":
        frappe.throw(_("只有待评审的打样单才能确认样品。"))

    if actual_cost not in (None, ""):
        doc.actual_cost = actual_cost

    previous_status = doc.sample_status
    doc.sample_status = "已确认"
    doc.finished_at = now_datetime()
    if normalize_text(note):
        doc.review_note = normalize_text(note)
    _append_log(
        doc,
        action_type="确认样品",
        from_status=previous_status,
        to_status=doc.sample_status,
        note=normalize_text(note) or _("样品已确认。"),
    )
    return _save_sample_action(doc, _("打样单已确认。"))


def cancel_sample_ticket(ticket_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_sample_ticket_doc(ticket_name)
    if doc.sample_status == "已取消":
        return _build_sample_response(doc, _("打样单已取消。"))
    if doc.sample_status == "已确认":
        frappe.throw(_("已确认的打样单不允许取消。"))

    previous_status = doc.sample_status
    doc.sample_status = "已取消"
    _append_log(
        doc,
        action_type="取消",
        from_status=previous_status,
        to_status=doc.sample_status,
        note=normalize_text(note) or _("打样单已取消。"),
    )
    return _save_sample_action(doc, _("打样单已取消。"))


def _validate_links(doc) -> None:
    if not doc.style:
        frappe.throw(_("款号不能为空。"))

    ensure_link_exists("Style", doc.style)
    ensure_link_exists("Item", doc.item_template)
    ensure_enabled_link("Color", doc.color)
    ensure_link_exists("Supplier", doc.supplier)
    ensure_link_exists("User", doc.requested_by)
    ensure_link_exists("User", doc.handler_user)


def _sync_from_style(doc) -> None:
    if not doc.style:
        return

    style_row = frappe.db.get_value(
        "Style",
        doc.style,
        ["style_name", "item_template"],
        as_dict=True,
    ) or {}
    doc.style_name = normalize_text(style_row.get("style_name")) or doc.style_name
    if not doc.item_template and style_row.get("item_template"):
        doc.item_template = style_row.get("item_template")

    if doc.color:
        return

    colors = frappe.get_all(
        "Style Color",
        filters={"parent": doc.style, "enabled": 1},
        fields=["color"],
        order_by="idx asc",
        limit=2,
    )
    if len(colors) == 1 and colors[0].get("color"):
        doc.color = colors[0]["color"]


def _sync_from_color(doc) -> None:
    if not doc.color:
        doc.color_name = ""
        doc.color_code = ""
        return

    color_row = frappe.db.get_value(
        "Color",
        doc.color,
        ["color_name", "color_group"],
        as_dict=True,
    ) or {}
    doc.color_name = normalize_text(color_row.get("color_name")) or doc.color

    color_group = normalize_text(color_row.get("color_group"))
    if not color_group:
        doc.color_code = ""
        return

    doc.color_code = normalize_text(
        frappe.db.get_value("Color Group", color_group, "color_group_code")
    )


def _validate_dates(doc) -> None:
    if doc.expected_finish_date and doc.requested_date and doc.expected_finish_date < doc.requested_date:
        frappe.throw(_("预计完成日期不能早于发起日期。"))

    if doc.finished_at and doc.requested_date and getdate(doc.finished_at) < doc.requested_date:
        frappe.throw(_("确认时间不能早于发起日期。"))


def _normalize_logs(doc) -> None:
    for row in doc.logs or []:
        row.action_time = _normalize_datetime(getattr(row, "action_time", None), use_now=True)
        row.action_type = normalize_select(
            getattr(row, "action_type", None),
            "操作类型",
            SAMPLE_TICKET_LOG_ACTIONS,
            default="备注",
            alias_map=SAMPLE_TICKET_LOG_ACTION_ALIASES,
        )
        row.from_status = SAMPLE_TICKET_STATUS_ALIASES.get(
            normalize_text(getattr(row, "from_status", None)),
            normalize_text(getattr(row, "from_status", None)),
        )
        row.to_status = SAMPLE_TICKET_STATUS_ALIASES.get(
            normalize_text(getattr(row, "to_status", None)),
            normalize_text(getattr(row, "to_status", None)),
        )
        row.operator = normalize_text(getattr(row, "operator", None)) or frappe.session.user
        ensure_link_exists("User", row.operator)
        row.note = normalize_text(getattr(row, "note", None))


def _append_system_logs(doc) -> None:
    if getattr(doc.flags, "skip_sample_ticket_system_log", False):
        return

    previous_status = ""
    before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
    if before:
        previous_status = normalize_text(getattr(before, "sample_status", None))

    if doc.is_new() and not _has_action_log(doc, "创建"):
        _append_log(
            doc,
            action_type="创建",
            to_status=doc.sample_status,
            note=_("创建打样单。"),
        )
    elif previous_status and previous_status != doc.sample_status:
        _append_log(
            doc,
            action_type="状态变更",
            from_status=previous_status,
            to_status=doc.sample_status,
            note=_("打样状态已更新。"),
        )


def _get_sample_ticket_doc(ticket_name: str):
    return frappe.get_doc("Sample Ticket", ticket_name)


def _ensure_sample_ticket_mutable(doc) -> None:
    if doc.sample_status in ("已确认", "已取消"):
        frappe.throw(_("当前打样单状态不允许继续操作。"))


def _save_sample_action(doc, message: str) -> dict[str, object]:
    doc.flags.skip_sample_ticket_system_log = True
    try:
        doc.save(ignore_permissions=True)
    finally:
        doc.flags.skip_sample_ticket_system_log = False
    return _build_sample_response(doc, message)


def _build_sample_response(doc, message: str) -> dict[str, object]:
    return {
        "ok": True,
        "name": doc.name,
        "ticket_no": doc.ticket_no or doc.name,
        "sample_status": doc.sample_status,
        "finished_at": str(doc.finished_at) if doc.finished_at else None,
        "message": message,
    }


def _append_log(
    doc,
    *,
    action_type: str,
    from_status: str = "",
    to_status: str = "",
    note: str = "",
) -> None:
    doc.append(
        "logs",
        {
            "action_time": now_datetime(),
            "action_type": action_type,
            "from_status": from_status,
            "to_status": to_status,
            "operator": frappe.session.user,
            "note": note,
        },
    )


def _has_action_log(doc, action_type: str) -> bool:
    return any(normalize_text(row.action_type) == action_type for row in (doc.logs or []))


def _normalize_date(value, *, use_today: bool = False):
    if not value:
        return getdate(nowdate()) if use_today else None
    return getdate(value)


def _normalize_datetime(value, *, use_now: bool = False):
    if not value:
        return now_datetime() if use_now else None
    return get_datetime(value)


def _coerce_positive_int(value, field_label: str) -> int:
    try:
        number = int(value if value not in (None, "") else 0)
    except (TypeError, ValueError):
        frappe.throw(_("{0}必须是整数。").format(field_label))
    if number <= 0:
        frappe.throw(_("{0}必须大于0。").format(field_label))
    return number


def _make_daily_sequence(doctype: str, prefix: str, digits: int = 4) -> str:
    last_name = frappe.db.sql(
        f"""
        select name
        from `tab{doctype}`
        where name like %s
        order by name desc
        limit 1
        """,
        (f"{prefix}%",),
    )
    last_value = last_name[0][0] if last_name else ""
    suffix = normalize_text(last_value)[len(prefix):]
    last_index = int(suffix) if suffix.isdigit() else 0
    return f"{prefix}{last_index + 1:0{digits}d}"


def _is_unsaved_name(value: str) -> bool:
    normalized = normalize_text(value)
    return not normalized or normalized.startswith("New ")
