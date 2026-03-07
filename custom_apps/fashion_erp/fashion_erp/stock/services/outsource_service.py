from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime, nowdate

from fashion_erp.stock.services.supply_service import (
    ITEM_USAGE_TYPE_ALIASES,
    ITEM_USAGE_TYPES,
    RAW_MATERIAL_ITEM_TYPES,
    SUPPLIER_ROLES,
)
from fashion_erp.style.services.style_service import (
    coerce_non_negative_float,
    coerce_non_negative_int,
    ensure_enabled_link,
    ensure_link_exists,
    normalize_select,
    normalize_text,
)


OUTSOURCE_ORDER_STATUSES = ("草稿", "已下单", "生产中", "已完成", "已取消")
OUTSOURCE_ORDER_STATUS_ALIASES = {
    "DRAFT": "草稿",
    "SUBMITTED": "已下单",
    "IN_PROGRESS": "生产中",
    "COMPLETED": "已完成",
    "CANCELLED": "已取消",
}
OUTSOURCE_LOG_ACTIONS = ("创建", "下单", "开工", "完成", "取消", "状态变更", "备注")
OUTSOURCE_LOG_ACTION_ALIASES = {
    "CREATE": "创建",
    "SUBMIT": "下单",
    "START": "开工",
    "COMPLETE": "完成",
    "CANCEL": "取消",
    "STATUS_CHANGE": "状态变更",
    "COMMENT": "备注",
}
OUTSOURCE_ALLOWED_SUPPLIER_ROLES = {"外包工厂", "综合供应商"}


def autoname_outsource_order(doc) -> None:
    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.order_no = doc.name
        return

    reference_dt = _normalize_date(getattr(doc, "order_date", None), use_today=True)
    prefix = f"{reference_dt.strftime('%Y%m%d')}WB"
    order_no = _make_daily_sequence("Outsource Order", prefix)
    doc.name = order_no
    doc.order_no = order_no


def validate_outsource_order(doc) -> None:
    doc.order_no = normalize_text(doc.order_no)
    doc.style = normalize_text(doc.style)
    doc.style_name = normalize_text(doc.style_name)
    doc.item_template = normalize_text(doc.item_template)
    doc.craft_sheet = normalize_text(doc.craft_sheet)
    doc.sample_ticket = normalize_text(doc.sample_ticket)
    doc.supplier = normalize_text(doc.supplier)
    doc.order_status = normalize_select(
        doc.order_status,
        "单据状态",
        OUTSOURCE_ORDER_STATUSES,
        default="草稿",
        alias_map=OUTSOURCE_ORDER_STATUS_ALIASES,
    )
    doc.order_date = _normalize_date(doc.order_date, use_today=True)
    doc.expected_delivery_date = _normalize_date(doc.expected_delivery_date)
    doc.color = normalize_text(doc.color)
    doc.color_name = normalize_text(doc.color_name)
    doc.color_code = normalize_text(doc.color_code)
    doc.ordered_qty = _coerce_positive_int(doc.ordered_qty, "下单数量")
    doc.received_qty = coerce_non_negative_int(doc.received_qty, "累计到货数量")
    doc.unit_estimated_cost = coerce_non_negative_float(doc.unit_estimated_cost, "预计单件成本")
    doc.total_estimated_cost = round(doc.ordered_qty * doc.unit_estimated_cost, 2)
    doc.supplier_order_no = normalize_text(doc.supplier_order_no)
    doc.receipt_warehouse = normalize_text(doc.receipt_warehouse)
    doc.remark = normalize_text(doc.remark)

    _validate_links(doc)
    _sync_from_style(doc)
    _sync_from_craft_sheet(doc)
    _sync_from_sample_ticket(doc)
    _sync_from_color(doc)
    _validate_supplier(doc)
    _normalize_materials(doc)
    _normalize_logs(doc)
    _append_system_logs(doc)
    _validate_dates(doc)

    if doc.received_qty > doc.ordered_qty:
        frappe.throw(_("累计到货数量不能大于下单数量。"))

    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.order_no = doc.name


def sync_outsource_order_number(doc) -> None:
    if doc.name and doc.order_no != doc.name:
        doc.db_set("order_no", doc.name, update_modified=False)
        doc.order_no = doc.name


def submit_outsource_order(order_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_outsource_order_doc(order_name)
    _ensure_outsource_order_mutable(doc)
    if doc.order_status != "草稿":
        frappe.throw(_("只有草稿状态的外包单才能下发。"))
    _ensure_submission_prerequisites(doc)

    previous_status = doc.order_status
    doc.order_status = "已下单"
    _append_log(
        doc,
        action_type="下单",
        from_status=previous_status,
        to_status=doc.order_status,
        note=normalize_text(note) or _("外包单已下发给工厂。"),
    )
    return _save_outsource_action(doc, _("外包单已下发。"))


def start_outsource_order(order_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_outsource_order_doc(order_name)
    _ensure_outsource_order_mutable(doc)
    if doc.order_status != "已下单":
        frappe.throw(_("只有已下单的外包单才能开始生产。"))

    previous_status = doc.order_status
    doc.order_status = "生产中"
    _append_log(
        doc,
        action_type="开工",
        from_status=previous_status,
        to_status=doc.order_status,
        note=normalize_text(note) or _("外包工厂已开始生产。"),
    )
    return _save_outsource_action(doc, _("外包单已进入生产中状态。"))


def complete_outsource_order(order_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_outsource_order_doc(order_name)
    _ensure_outsource_order_mutable(doc)
    if doc.order_status not in ("已下单", "生产中"):
        frappe.throw(_("只有已下单或生产中的外包单才能完成。"))

    previous_status = doc.order_status
    doc.order_status = "已完成"
    _append_log(
        doc,
        action_type="完成",
        from_status=previous_status,
        to_status=doc.order_status,
        note=normalize_text(note) or _("外包单已标记完成。"),
    )
    return _save_outsource_action(doc, _("外包单已完成。"))


def cancel_outsource_order(order_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_outsource_order_doc(order_name)
    if doc.order_status == "已取消":
        return _build_outsource_response(doc, _("外包单已取消。"))
    if doc.order_status == "已完成":
        frappe.throw(_("已完成的外包单不允许取消。"))

    previous_status = doc.order_status
    doc.order_status = "已取消"
    _append_log(
        doc,
        action_type="取消",
        from_status=previous_status,
        to_status=doc.order_status,
        note=normalize_text(note) or _("外包单已取消。"),
    )
    return _save_outsource_action(doc, _("外包单已取消。"))


def _validate_links(doc) -> None:
    if not doc.style:
        frappe.throw(_("款号不能为空。"))

    ensure_link_exists("Style", doc.style)
    ensure_link_exists("Item", doc.item_template)
    ensure_link_exists("Craft Sheet", doc.craft_sheet)
    ensure_link_exists("Sample Ticket", doc.sample_ticket)
    ensure_link_exists("Supplier", doc.supplier)
    ensure_link_exists("Warehouse", doc.receipt_warehouse)
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


def _sync_from_craft_sheet(doc) -> None:
    if not doc.craft_sheet:
        return

    sheet_row = frappe.db.get_value(
        "Craft Sheet",
        doc.craft_sheet,
        ["style", "style_name", "item_template", "sample_ticket", "color", "color_name", "color_code"],
        as_dict=True,
    ) or {}

    sheet_style = normalize_text(sheet_row.get("style"))
    if sheet_style and doc.style and doc.style != sheet_style:
        frappe.throw(_("外包单关联的工艺单与款号不一致。"))
    if sheet_style:
        doc.style = sheet_style

    if sheet_row.get("style_name"):
        doc.style_name = normalize_text(sheet_row.get("style_name"))
    if sheet_row.get("item_template") and not doc.item_template:
        doc.item_template = sheet_row.get("item_template")
    if sheet_row.get("sample_ticket"):
        doc.sample_ticket = normalize_text(sheet_row.get("sample_ticket"))

    sheet_color = normalize_text(sheet_row.get("color"))
    if sheet_color and doc.color and doc.color != sheet_color:
        frappe.throw(_("外包单颜色与工艺单颜色不一致。"))
    if sheet_color:
        doc.color = sheet_color
    if sheet_row.get("color_name"):
        doc.color_name = normalize_text(sheet_row.get("color_name"))
    if sheet_row.get("color_code"):
        doc.color_code = normalize_text(sheet_row.get("color_code"))


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
        frappe.throw(_("外包单关联的打样单与款号不一致。"))
    if sample_style:
        doc.style = sample_style
    if sample_row.get("style_name") and not doc.style_name:
        doc.style_name = normalize_text(sample_row.get("style_name"))
    if sample_row.get("item_template") and not doc.item_template:
        doc.item_template = sample_row.get("item_template")

    sample_color = normalize_text(sample_row.get("color"))
    if sample_color and doc.color and doc.color != sample_color:
        frappe.throw(_("外包单颜色与打样单颜色不一致。"))
    if sample_color and not doc.color:
        doc.color = sample_color
    if sample_row.get("color_name") and not doc.color_name:
        doc.color_name = normalize_text(sample_row.get("color_name"))
    if sample_row.get("color_code") and not doc.color_code:
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
    doc.color_name = normalize_text(color_row.get("color_name")) or doc.color

    color_group = normalize_text(color_row.get("color_group"))
    if not color_group:
        doc.color_code = ""
        return

    doc.color_code = normalize_text(
        frappe.db.get_value("Color Group", color_group, "color_group_code")
    )


def _validate_supplier(doc) -> None:
    if not doc.supplier:
        return

    supplier_role = normalize_select(
        frappe.db.get_value("Supplier", doc.supplier, "supplier_role"),
        "供应商角色",
        SUPPLIER_ROLES,
        default="综合供应商",
    )
    if supplier_role not in OUTSOURCE_ALLOWED_SUPPLIER_ROLES:
        frappe.throw(
            _("供应商 {0} 的角色 {1} 不适合作为外包工厂。").format(
                frappe.bold(doc.supplier),
                frappe.bold(supplier_role),
            )
        )


def _normalize_materials(doc) -> None:
    for row in doc.materials or []:
        row.item_code = normalize_text(getattr(row, "item_code", None))
        row.item_name = normalize_text(getattr(row, "item_name", None))
        row.item_usage_type = normalize_text(getattr(row, "item_usage_type", None))
        row.uom = normalize_text(getattr(row, "uom", None))
        row.planned_qty = coerce_non_negative_float(getattr(row, "planned_qty", None), "计划用量")
        row.prepared_qty = coerce_non_negative_float(getattr(row, "prepared_qty", None), "已备货数量")
        row.issued_qty_manual = coerce_non_negative_float(getattr(row, "issued_qty_manual", None), "人工登记已发数量")
        row.warehouse = normalize_text(getattr(row, "warehouse", None))
        row.default_location = normalize_text(getattr(row, "default_location", None))
        row.remark = normalize_text(getattr(row, "remark", None))

        if not row.item_code:
            frappe.throw(_("原辅料明细第 {0} 行缺少物料。").format(frappe.bold(row.idx)))

        ensure_link_exists("Item", row.item_code)
        item_values = frappe.db.get_value(
            "Item",
            row.item_code,
            ["item_name", "item_usage_type", "stock_uom", "supply_warehouse", "default_location"],
            as_dict=True,
        ) or {}
        row.item_name = normalize_text(item_values.get("item_name")) or row.item_name or row.item_code
        row.item_usage_type = normalize_select(
            item_values.get("item_usage_type"),
            "物料用途",
            ITEM_USAGE_TYPES,
            default="其他",
            alias_map=ITEM_USAGE_TYPE_ALIASES,
        )
        row.uom = normalize_text(item_values.get("stock_uom")) or row.uom
        row.warehouse = row.warehouse or normalize_text(item_values.get("supply_warehouse"))
        row.default_location = row.default_location or normalize_text(item_values.get("default_location"))

        if row.item_usage_type not in RAW_MATERIAL_ITEM_TYPES:
            frappe.throw(
                _("原辅料明细第 {0} 行只能引用面料或辅料。").format(
                    frappe.bold(row.idx)
                )
            )
        if row.planned_qty <= 0:
            frappe.throw(_("原辅料明细第 {0} 行的计划用量必须大于 0。").format(frappe.bold(row.idx)))
        if row.prepared_qty > row.planned_qty:
            frappe.throw(_("原辅料明细第 {0} 行的已备货数量不能大于计划用量。").format(frappe.bold(row.idx)))
        if row.issued_qty_manual > row.planned_qty:
            frappe.throw(_("原辅料明细第 {0} 行的人工登记已发数量不能大于计划用量。").format(frappe.bold(row.idx)))

        ensure_link_exists("Warehouse", row.warehouse)
        ensure_enabled_link("Warehouse Location", row.default_location)
        if row.default_location and row.warehouse:
            location_warehouse = normalize_text(
                frappe.db.get_value("Warehouse Location", row.default_location, "warehouse")
            )
            if location_warehouse and location_warehouse != row.warehouse:
                frappe.throw(
                    _("原辅料明细第 {0} 行的备货库位不属于备货仓库。").format(
                        frappe.bold(row.idx)
                    )
                )


def _normalize_logs(doc) -> None:
    for row in doc.logs or []:
        row.action_time = _normalize_datetime(getattr(row, "action_time", None), use_now=True)
        row.action_type = normalize_select(
            getattr(row, "action_type", None),
            "操作类型",
            OUTSOURCE_LOG_ACTIONS,
            default="备注",
            alias_map=OUTSOURCE_LOG_ACTION_ALIASES,
        )
        row.from_status = OUTSOURCE_ORDER_STATUS_ALIASES.get(
            normalize_text(getattr(row, "from_status", None)),
            normalize_text(getattr(row, "from_status", None)),
        )
        row.to_status = OUTSOURCE_ORDER_STATUS_ALIASES.get(
            normalize_text(getattr(row, "to_status", None)),
            normalize_text(getattr(row, "to_status", None)),
        )
        row.operator = normalize_text(getattr(row, "operator", None)) or frappe.session.user
        ensure_link_exists("User", row.operator)
        row.note = normalize_text(getattr(row, "note", None))


def _append_system_logs(doc) -> None:
    if getattr(doc.flags, "skip_outsource_order_system_log", False):
        return

    previous_status = ""
    before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
    if before:
        previous_status = normalize_text(getattr(before, "order_status", None))

    if doc.is_new() and not _has_action_log(doc, "创建"):
        _append_log(
            doc,
            action_type="创建",
            to_status=doc.order_status,
            note=_("创建外包单。"),
        )
    elif previous_status and previous_status != doc.order_status:
        _append_log(
            doc,
            action_type="状态变更",
            from_status=previous_status,
            to_status=doc.order_status,
            note=_("外包单状态已更新。"),
        )


def _validate_dates(doc) -> None:
    if doc.expected_delivery_date and doc.order_date and doc.expected_delivery_date < doc.order_date:
        frappe.throw(_("预计到货日期不能早于下单日期。"))


def _ensure_submission_prerequisites(doc) -> None:
    if not doc.craft_sheet:
        frappe.throw(_("下发外包单前必须先关联工艺单。"))

    craft_status = normalize_text(frappe.db.get_value("Craft Sheet", doc.craft_sheet, "sheet_status"))
    if craft_status != "已发布":
        frappe.throw(_("只有已发布的工艺单才能用于外包下单。"))

    if not doc.materials:
        frappe.throw(_("下发外包单前至少需要一条原辅料引用明细。"))


def _ensure_outsource_order_mutable(doc) -> None:
    if doc.order_status in ("已完成", "已取消"):
        frappe.throw(_("当前外包单状态不允许继续操作。"))


def _save_outsource_action(doc, message: str) -> dict[str, object]:
    doc.flags.skip_outsource_order_system_log = True
    try:
        doc.save(ignore_permissions=True)
    finally:
        doc.flags.skip_outsource_order_system_log = False
    return _build_outsource_response(doc, message)


def _build_outsource_response(doc, message: str) -> dict[str, object]:
    return {
        "ok": True,
        "name": doc.name,
        "order_no": doc.order_no or doc.name,
        "order_status": doc.order_status,
        "ordered_qty": cint(doc.ordered_qty),
        "received_qty": cint(doc.received_qty),
        "total_estimated_cost": float(doc.total_estimated_cost or 0),
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


def _get_outsource_order_doc(order_name: str):
    return frappe.get_doc("Outsource Order", order_name)


def _normalize_date(value, *, use_today: bool = False):
    if not value:
        return getdate(nowdate()) if use_today else None
    return getdate(value)


def _normalize_datetime(value, *, use_now: bool = False):
    if not value:
        return now_datetime() if use_now else None
    return get_datetime(value)


def _coerce_positive_int(value, field_label: str) -> int:
    number = coerce_non_negative_int(value, field_label)
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
