from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime, nowdate

from fashion_erp.style.services.style_service import (
    coerce_non_negative_float,
    ensure_enabled_link,
    ensure_link_exists,
    normalize_select,
    normalize_text,
)


CRAFT_SHEET_STATUSES = ("草稿", "已发布", "已作废")
CRAFT_SHEET_STATUS_ALIASES = {
    "DRAFT": "草稿",
    "PUBLISHED": "已发布",
    "VOIDED": "已作废",
}
CRAFT_SHEET_LOG_ACTIONS = ("创建", "发布", "作废", "状态变更", "备注")
CRAFT_SHEET_LOG_ACTION_ALIASES = {
    "CREATE": "创建",
    "PUBLISH": "发布",
    "VOID": "作废",
    "STATUS_CHANGE": "状态变更",
    "COMMENT": "备注",
}
VERSION_PATTERN = re.compile(r"^V(\d+)$")


def autoname_craft_sheet(doc) -> None:
    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.sheet_no = doc.name
        return

    reference_dt = _normalize_date(getattr(doc, "effective_date", None), use_today=True)
    prefix = f"{reference_dt.strftime('%Y%m%d')}GY"
    sheet_no = _make_daily_sequence("Craft Sheet", prefix)
    doc.name = sheet_no
    doc.sheet_no = sheet_no


def validate_craft_sheet(doc) -> None:
    doc.sheet_no = normalize_text(doc.sheet_no)
    doc.style = normalize_text(doc.style)
    doc.style_name = normalize_text(doc.style_name)
    doc.item_template = normalize_text(doc.item_template)
    doc.sample_ticket = normalize_text(doc.sample_ticket)
    doc.version_no = _normalize_version_no(doc.version_no)
    doc.sheet_status = normalize_select(
        doc.sheet_status,
        "单据状态",
        CRAFT_SHEET_STATUSES,
        default="草稿",
        alias_map=CRAFT_SHEET_STATUS_ALIASES,
    )
    doc.prepared_by = normalize_text(doc.prepared_by) or frappe.session.user
    doc.effective_date = _normalize_date(doc.effective_date)
    doc.color = normalize_text(doc.color)
    doc.color_name = normalize_text(doc.color_name)
    doc.color_code = normalize_text(doc.color_code)
    doc.estimated_unit_cost = coerce_non_negative_float(doc.estimated_unit_cost, "预计单件成本")
    doc.fabric_note = normalize_text(doc.fabric_note)
    doc.trim_note = normalize_text(doc.trim_note)
    doc.size_note = normalize_text(doc.size_note)
    doc.workmanship_note = normalize_text(doc.workmanship_note)
    doc.packaging_note = normalize_text(doc.packaging_note)
    doc.qc_note = normalize_text(doc.qc_note)
    doc.reference_file = normalize_text(doc.reference_file)
    doc.remark = normalize_text(doc.remark)

    _validate_links(doc)
    _sync_from_style(doc)
    _sync_from_sample_ticket(doc)
    _sync_from_color(doc)
    _validate_unique_version(doc)
    _normalize_logs(doc)
    _append_system_logs(doc)

    doc.is_current_version = 1 if doc.sheet_status == "已发布" else 0

    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.sheet_no = doc.name


def sync_craft_sheet_number(doc) -> None:
    if doc.name and doc.sheet_no != doc.name:
        doc.db_set("sheet_no", doc.name, update_modified=False)
        doc.sheet_no = doc.name


def publish_craft_sheet(sheet_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_craft_sheet_doc(sheet_name)
    _ensure_craft_sheet_mutable(doc)
    if doc.sheet_status != "草稿":
        frappe.throw(_("只有草稿状态的工艺单才能发布。"))

    if doc.sample_ticket:
        sample_status = normalize_text(frappe.db.get_value("Sample Ticket", doc.sample_ticket, "sample_status"))
        if sample_status != "已确认":
            frappe.throw(_("关联打样单未确认前，不能发布工艺单。"))

    previous_status = doc.sheet_status
    doc.sheet_status = "已发布"
    doc.is_current_version = 1
    doc.effective_date = doc.effective_date or getdate(nowdate())
    _append_log(
        doc,
        action_type="发布",
        from_status=previous_status,
        to_status=doc.sheet_status,
        note=normalize_text(note) or _("工艺单已发布。"),
    )
    payload = _save_craft_sheet_action(doc, _("工艺单已发布。"))
    _set_current_version(doc.style, doc.name)
    return payload


def void_craft_sheet(sheet_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_craft_sheet_doc(sheet_name)
    if doc.sheet_status == "已作废":
        return _build_craft_sheet_response(doc, _("工艺单已作废。"))

    previous_status = doc.sheet_status
    doc.sheet_status = "已作废"
    doc.is_current_version = 0
    _append_log(
        doc,
        action_type="作废",
        from_status=previous_status,
        to_status=doc.sheet_status,
        note=normalize_text(note) or _("工艺单已作废。"),
    )
    payload = _save_craft_sheet_action(doc, _("工艺单已作废。"))
    _promote_latest_published_version(doc.style, exclude_name=doc.name)
    return payload


def build_next_craft_sheet_defaults(sheet_name: str) -> dict[str, object]:
    doc = _get_craft_sheet_doc(sheet_name)
    next_version = _get_next_version_no(doc.style)
    defaults = {
        "style": doc.style,
        "style_name": doc.style_name,
        "item_template": doc.item_template,
        "sample_ticket": doc.sample_ticket,
        "version_no": next_version,
        "color": doc.color,
        "color_name": doc.color_name,
        "color_code": doc.color_code,
        "estimated_unit_cost": doc.estimated_unit_cost,
        "fabric_note": doc.fabric_note,
        "trim_note": doc.trim_note,
        "size_note": doc.size_note,
        "workmanship_note": doc.workmanship_note,
        "packaging_note": doc.packaging_note,
        "qc_note": doc.qc_note,
        "remark": doc.remark,
    }
    return {
        "ok": True,
        "defaults": defaults,
    }


def _validate_links(doc) -> None:
    if not doc.style:
        frappe.throw(_("款号不能为空。"))

    ensure_link_exists("Style", doc.style)
    ensure_link_exists("Item", doc.item_template)
    ensure_link_exists("Sample Ticket", doc.sample_ticket)
    ensure_link_exists("User", doc.prepared_by)
    ensure_enabled_link("Color", doc.color)


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


def _sync_from_sample_ticket(doc) -> None:
    if not doc.sample_ticket:
        return

    sample_row = frappe.db.get_value(
        "Sample Ticket",
        doc.sample_ticket,
        ["style", "style_name", "item_template", "color", "color_name", "color_code"],
        as_dict=True,
    ) or {}
    sample_style = normalize_text(sample_row.get("style"))
    if sample_style and doc.style and doc.style != sample_style:
        frappe.throw(_("工艺单关联的打样单与款号不一致。"))
    if sample_style:
        doc.style = sample_style
    if sample_row.get("style_name"):
        doc.style_name = normalize_text(sample_row.get("style_name"))
    if sample_row.get("item_template") and not doc.item_template:
        doc.item_template = sample_row.get("item_template")

    sample_color = normalize_text(sample_row.get("color"))
    if sample_color and doc.color and doc.color != sample_color:
        frappe.throw(_("工艺单颜色与关联打样单颜色不一致。"))
    if sample_color:
        doc.color = sample_color
    if sample_row.get("color_name"):
        doc.color_name = normalize_text(sample_row.get("color_name"))
    if sample_row.get("color_code"):
        doc.color_code = normalize_text(sample_row.get("color_code"))


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
    doc.color_name = normalize_text(color_row.get("color_name")) or doc.color_name or doc.color

    color_group = normalize_text(color_row.get("color_group"))
    if not color_group:
        return

    group_code = normalize_text(frappe.db.get_value("Color Group", color_group, "color_group_code"))
    if group_code:
        doc.color_code = group_code


def _validate_unique_version(doc) -> None:
    existing = frappe.get_all(
        "Craft Sheet",
        filters={
            "style": doc.style,
            "version_no": doc.version_no,
            "name": ["!=", doc.name or ""],
        },
        pluck="name",
        limit=1,
    )
    if existing:
        frappe.throw(
            _("款号 {0} 已存在版本号 {1} 的工艺单。").format(
                frappe.bold(doc.style),
                frappe.bold(doc.version_no),
            )
        )


def _normalize_logs(doc) -> None:
    for row in doc.logs or []:
        row.action_time = _normalize_datetime(getattr(row, "action_time", None), use_now=True)
        row.action_type = normalize_select(
            getattr(row, "action_type", None),
            "操作类型",
            CRAFT_SHEET_LOG_ACTIONS,
            default="备注",
            alias_map=CRAFT_SHEET_LOG_ACTION_ALIASES,
        )
        row.from_status = CRAFT_SHEET_STATUS_ALIASES.get(
            normalize_text(getattr(row, "from_status", None)),
            normalize_text(getattr(row, "from_status", None)),
        )
        row.to_status = CRAFT_SHEET_STATUS_ALIASES.get(
            normalize_text(getattr(row, "to_status", None)),
            normalize_text(getattr(row, "to_status", None)),
        )
        row.operator = normalize_text(getattr(row, "operator", None)) or frappe.session.user
        ensure_link_exists("User", row.operator)
        row.note = normalize_text(getattr(row, "note", None))


def _append_system_logs(doc) -> None:
    if getattr(doc.flags, "skip_craft_sheet_system_log", False):
        return

    previous_status = ""
    before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
    if before:
        previous_status = normalize_text(getattr(before, "sheet_status", None))

    if doc.is_new() and not _has_action_log(doc, "创建"):
        _append_log(
            doc,
            action_type="创建",
            to_status=doc.sheet_status,
            note=_("创建工艺单。"),
        )
    elif previous_status and previous_status != doc.sheet_status:
        _append_log(
            doc,
            action_type="状态变更",
            from_status=previous_status,
            to_status=doc.sheet_status,
            note=_("工艺单状态已更新。"),
        )


def _ensure_craft_sheet_mutable(doc) -> None:
    if doc.sheet_status == "已作废":
        frappe.throw(_("已作废的工艺单不允许继续操作。"))


def _save_craft_sheet_action(doc, message: str) -> dict[str, object]:
    doc.flags.skip_craft_sheet_system_log = True
    try:
        doc.save(ignore_permissions=True)
    finally:
        doc.flags.skip_craft_sheet_system_log = False
    return _build_craft_sheet_response(doc, message)


def _build_craft_sheet_response(doc, message: str) -> dict[str, object]:
    return {
        "ok": True,
        "name": doc.name,
        "sheet_no": doc.sheet_no or doc.name,
        "sheet_status": doc.sheet_status,
        "version_no": doc.version_no,
        "is_current_version": cint(doc.is_current_version),
        "message": message,
    }


def _set_current_version(style_name: str, current_docname: str) -> None:
    if not style_name:
        return

    sheets = frappe.get_all(
        "Craft Sheet",
        filters={"style": style_name, "name": ["!=", current_docname]},
        fields=["name", "is_current_version"],
    )
    for row in sheets:
        if cint(row.is_current_version):
            frappe.db.set_value("Craft Sheet", row.name, "is_current_version", 0, update_modified=False)


def _promote_latest_published_version(style_name: str, *, exclude_name: str) -> None:
    if not style_name:
        return

    candidates = frappe.get_all(
        "Craft Sheet",
        filters={
            "style": style_name,
            "sheet_status": "已发布",
            "name": ["!=", exclude_name],
        },
        fields=["name", "version_no"],
    )
    if not candidates:
        return

    def sort_key(row):
        return _extract_version_index(row.version_no)

    latest = max(candidates, key=sort_key)
    frappe.db.set_value("Craft Sheet", latest.name, "is_current_version", 1, update_modified=False)


def _get_next_version_no(style_name: str) -> str:
    existing_versions = frappe.get_all(
        "Craft Sheet",
        filters={"style": style_name},
        pluck="version_no",
    )
    if not existing_versions:
        return "V1"
    next_index = max(_extract_version_index(value) for value in existing_versions) + 1
    return f"V{next_index}"


def _extract_version_index(value: str | None) -> int:
    normalized = _normalize_version_no(value)
    match = VERSION_PATTERN.fullmatch(normalized)
    return int(match.group(1)) if match else 1


def _normalize_version_no(value: str | None) -> str:
    normalized = normalize_text(value).upper() or "V1"
    if normalized.isdigit():
        normalized = f"V{normalized}"
    if not VERSION_PATTERN.fullmatch(normalized):
        frappe.throw(_("版本号格式必须为 V1、V2 这类形式。"))
    return normalized


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


def _get_craft_sheet_doc(sheet_name: str):
    return frappe.get_doc("Craft Sheet", sheet_name)


def _normalize_date(value, *, use_today: bool = False):
    if not value:
        return getdate(nowdate()) if use_today else None
    return getdate(value)


def _normalize_datetime(value, *, use_now: bool = False):
    if not value:
        return now_datetime() if use_now else None
    return get_datetime(value)


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
