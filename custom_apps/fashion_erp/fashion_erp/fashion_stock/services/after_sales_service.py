from __future__ import annotations

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import get_datetime, getdate, now_datetime, nowdate

from fashion_erp.style.services.style_service import (
    coerce_non_negative_float,
    ensure_enabled_link,
    ensure_link_exists,
    normalize_select,
    normalize_text,
)
from fashion_erp.fashion_stock.services.stock_service import (
    get_inventory_status_display,
    validate_inventory_status_transition,
)


AFTER_SALES_TICKET_TYPES = ("仅退款", "退货退款", "换货", "补发", "维修", "投诉")
AFTER_SALES_TICKET_TYPE_ALIASES = {
    "REFUND_ONLY": "仅退款",
    "RETURN_REFUND": "退货退款",
    "EXCHANGE": "换货",
    "RESEND": "补发",
    "REPAIR": "维修",
    "COMPLAINT": "投诉",
}
AFTER_SALES_TICKET_STATUSES = (
    "新建",
    "待退回",
    "已收货",
    "质检中",
    "待处理",
    "待退款",
    "待补发",
    "已关闭",
    "已取消",
)
AFTER_SALES_TICKET_STATUS_ALIASES = {
    "NEW": "新建",
    "WAITING_RETURN": "待退回",
    "RECEIVED": "已收货",
    "INSPECTING": "质检中",
    "PENDING_DECISION": "待处理",
    "WAITING_REFUND": "待退款",
    "WAITING_RESEND": "待补发",
    "CLOSED": "已关闭",
    "CANCELLED": "已取消",
}
AFTER_SALES_ITEM_ACTIONS = AFTER_SALES_TICKET_TYPES
AFTER_SALES_LOG_ACTIONS = (
    "创建",
    "状态变更",
    "收货",
    "质检",
    "退款",
    "补发",
    "关闭",
    "备注",
)
AFTER_SALES_LOG_ACTION_ALIASES = {
    "CREATE": "创建",
    "STATUS_CHANGE": "状态变更",
    "RECEIVE": "收货",
    "INSPECT": "质检",
    "REFUND": "退款",
    "RESEND": "补发",
    "CLOSE": "关闭",
    "COMMENT": "备注",
}
AFTER_SALES_PRIORITIES = ("低", "普通", "高", "紧急")
AFTER_SALES_PRIORITY_ALIASES = {
    "Low": "低",
    "Normal": "普通",
    "High": "高",
    "Urgent": "紧急",
}
REFUND_STATUS_OPTIONS = ("无需退款", "待退款", "已退款", "已驳回")
REFUND_STATUS_ALIASES = {
    "NOT_REQUIRED": "无需退款",
    "PENDING": "待退款",
    "DONE": "已退款",
    "REJECTED": "已驳回",
}
AFTER_SALES_INVENTORY_CLOSURE_OPTIONS = ("未回写", "待检已入账", "已最终处理")
AFTER_SALES_RETURN_REQUIRED_TYPES = ("退货退款", "换货", "维修")
AFTER_SALES_REPLACEMENT_TYPES = ("换货", "补发", "维修")
AFTER_SALES_REPLACEMENT_FULFILLMENT_OPTIONS = (
    "待配货",
    "履约中",
    "待发货",
    "部分发货",
    "已发货",
    "已完成",
    "售后中",
    "已关闭",
    "已取消",
)
AFTER_SALES_COMPLETED_REPLACEMENT_FULFILLMENT_STATUSES = {"已发货", "已完成", "已关闭"}
AFTER_SALES_STOCK_ENTRY_MODES = ("待检入库", "最终处理")
AFTER_SALES_STOCK_ENTRY_MODE_ALIASES = {
    "RECEIVE_PENDING": "待检入库",
    "FINAL_DISPOSITION": "最终处理",
}
AFTER_SALES_STOCK_ENTRY_PURPOSES = ("Material Receipt", "Material Transfer")
AFTER_SALES_STOCK_ENTRY_PURPOSE_ALIASES = {
    "物料入库": "Material Receipt",
    "物料转移": "Material Transfer",
}


def autoname_after_sales_ticket(doc) -> None:
    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.ticket_no = doc.name
        return

    reference_dt = getdate(getattr(doc, "apply_time", None) or now_datetime())
    prefix = f"{reference_dt.strftime('%Y%m%d')}TK."
    ticket_no = make_autoname(f"{prefix}####")
    doc.name = ticket_no
    doc.ticket_no = ticket_no


def validate_after_sales_ticket(doc) -> None:
    _reset_after_sales_validation_cache(doc)
    doc.ticket_no = normalize_text(doc.ticket_no)
    doc.ticket_type = normalize_select(
        doc.ticket_type,
        "工单类型",
        AFTER_SALES_TICKET_TYPES,
        default="退货退款",
        alias_map=AFTER_SALES_TICKET_TYPE_ALIASES,
    )
    doc.ticket_status = normalize_select(
        doc.ticket_status,
        "工单状态",
        AFTER_SALES_TICKET_STATUSES,
        default="新建",
        alias_map=AFTER_SALES_TICKET_STATUS_ALIASES,
    )
    doc.priority = normalize_select(
        doc.priority,
        "优先级",
        AFTER_SALES_PRIORITIES,
        default="普通",
        alias_map=AFTER_SALES_PRIORITY_ALIASES,
    )
    doc.channel = normalize_text(doc.channel)
    doc.external_order_id = normalize_text(doc.external_order_id)
    doc.buyer_name = normalize_text(doc.buyer_name)
    doc.mobile = normalize_text(doc.mobile)
    doc.apply_time = _normalize_datetime(doc.apply_time, use_now=True)
    doc.reason_detail = normalize_text(doc.reason_detail)
    doc.logistics_company = normalize_text(doc.logistics_company)
    doc.tracking_no = normalize_text(doc.tracking_no)
    doc.received_at = _normalize_datetime(doc.received_at)
    doc.refund_amount = coerce_non_negative_float(doc.refund_amount, "退款金额")
    doc.refund_status = normalize_select(
        doc.refund_status,
        "退款状态",
        REFUND_STATUS_OPTIONS,
        default="无需退款",
        alias_map=REFUND_STATUS_ALIASES,
    )
    doc.replacement_sales_order = normalize_text(doc.replacement_sales_order)
    doc.replacement_fulfillment_status = normalize_select(
        getattr(doc, "replacement_fulfillment_status", None),
        "补发履约状态",
        AFTER_SALES_REPLACEMENT_FULFILLMENT_OPTIONS,
        default="",
    )
    doc.inventory_closure_status = normalize_select(
        getattr(doc, "inventory_closure_status", None),
        "库存闭环状态",
        AFTER_SALES_INVENTORY_CLOSURE_OPTIONS,
        default="未回写",
    )
    doc.pending_return_stock_entry = normalize_text(
        getattr(doc, "pending_return_stock_entry", None)
    )
    doc.final_disposition_stock_entry = normalize_text(
        getattr(doc, "final_disposition_stock_entry", None)
    )
    doc.remark = normalize_text(doc.remark)
    doc.owner_user = normalize_text(doc.owner_user) or frappe.session.user
    doc.handler_user = normalize_text(doc.handler_user) or doc.owner_user

    _validate_items(doc)
    _validate_links(doc)
    _sync_from_sales_order(doc)
    _sync_location_context(doc)
    _sync_refund_status(doc)
    _normalize_logs(doc)
    _append_system_logs(doc)

    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.ticket_no = doc.name


def sync_after_sales_ticket_number(doc) -> None:
    if doc.name and doc.ticket_no != doc.name:
        doc.db_set("ticket_no", doc.name, update_modified=False)
        doc.ticket_no = doc.name


def move_after_sales_ticket_to_waiting_return(
    ticket_name: str,
    *,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    _ensure_after_sales_ticket_mutable(doc)
    if doc.ticket_type not in AFTER_SALES_RETURN_REQUIRED_TYPES:
        frappe.throw(_("当前工单类型无需进入待退回状态。"))
    if doc.ticket_status != "新建":
        frappe.throw(_("只有新建的售后工单才能转入待退回状态。"))

    previous_status = doc.ticket_status
    doc.ticket_status = "待退回"
    _append_log(
        doc,
        action_type="状态变更",
        from_status=previous_status,
        to_status=doc.ticket_status,
        note=normalize_text(note) or _("等待客户寄回商品。"),
    )
    return _save_after_sales_action(
        doc,
        _("售后工单已进入待退回状态。"),
    )


def receive_after_sales_ticket(
    ticket_name: str,
    *,
    warehouse: str | None = None,
    warehouse_location: str | None = None,
    logistics_company: str | None = None,
    tracking_no: str | None = None,
    received_at=None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    _ensure_after_sales_ticket_mutable(doc)
    if doc.ticket_status not in ("新建", "待退回"):
        frappe.throw(_("只有新建或待退回状态的售后工单才能执行收货。"))

    doc.warehouse = normalize_text(warehouse) or doc.warehouse
    doc.warehouse_location = normalize_text(warehouse_location) or doc.warehouse_location
    doc.logistics_company = normalize_text(logistics_company) or doc.logistics_company
    doc.tracking_no = normalize_text(tracking_no) or doc.tracking_no
    doc.received_at = _normalize_datetime(received_at, use_now=True)

    for row in doc.items or []:
        if row.received_qty <= 0:
            row.received_qty = row.qty

    previous_status = doc.ticket_status
    doc.ticket_status = "已收货"
    _append_log(
        doc,
        action_type="收货",
        from_status=previous_status,
        to_status=doc.ticket_status,
        note=normalize_text(note) or _("退回商品已收货。"),
    )
    return _save_after_sales_action(
        doc,
        _("售后工单已标记为已收货。"),
    )


def start_after_sales_inspection(
    ticket_name: str,
    *,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    _ensure_after_sales_ticket_mutable(doc)
    if doc.ticket_status != "已收货":
        frappe.throw(_("只有已收货的售后工单才能进入质检。"))
    if not any((row.received_qty or 0) > 0 for row in (doc.items or [])):
        frappe.throw(_("开始质检前必须先填写实收数量。"))

    previous_status = doc.ticket_status
    doc.ticket_status = "质检中"
    _append_log(
        doc,
        action_type="质检",
        from_status=previous_status,
        to_status=doc.ticket_status,
        note=normalize_text(note) or _("开始质检。"),
    )
    return _save_after_sales_action(
        doc,
        _("售后工单已进入质检中状态。"),
    )


def apply_after_sales_decision(
    ticket_name: str,
    *,
    return_disposition: str | None = None,
    refund_amount: float | str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    _ensure_after_sales_ticket_mutable(doc)
    if doc.ticket_status not in ("新建", "已收货", "质检中", "待处理"):
        frappe.throw(_("当前工单状态不允许执行处理结论。"))

    if doc.ticket_type in AFTER_SALES_RETURN_REQUIRED_TYPES and not any(
        (row.received_qty or 0) > 0 for row in (doc.items or [])
    ):
        frappe.throw(_("当前工单类型在处理前必须先填写实收数量。"))

    disposition = normalize_text(return_disposition) or doc.return_disposition
    if disposition:
        doc.return_disposition = disposition
        for row in doc.items or []:
            if row.received_qty > 0 and not row.return_disposition:
                row.return_disposition = disposition

    if refund_amount not in (None, ""):
        doc.refund_amount = refund_amount

    previous_status = doc.ticket_status
    next_status = _determine_after_sales_decision_status(doc)
    doc.ticket_status = next_status
    _append_log(
        doc,
        action_type="状态变更",
        from_status=previous_status,
        to_status=next_status,
        note=normalize_text(note) or _("已应用处理结论。"),
    )
    return _save_after_sales_action(
        doc,
        _("售后处理结论已应用。"),
    )


def approve_after_sales_refund(
    ticket_name: str,
    *,
    refund_amount: float | str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    _ensure_after_sales_ticket_mutable(doc)
    if doc.ticket_status != "待退款":
        frappe.throw(_("只有待退款的售后工单才能确认退款。"))

    if refund_amount not in (None, ""):
        doc.refund_amount = refund_amount

    doc.refund_amount = coerce_non_negative_float(doc.refund_amount, "退款金额")
    if doc.refund_amount <= 0:
        frappe.throw(_("确认退款前，退款金额必须大于 0。"))

    previous_status = doc.ticket_status
    doc.refund_status = "已退款"
    if _after_sales_inventory_writeback_required(doc) and not _has_after_sales_final_inventory_writeback(doc):
        doc.ticket_status = "待处理"
        message = _("退款已完成，待最终处理库存回写后再关闭售后工单。")
    else:
        doc.ticket_status = "已关闭"
        message = _("退款已完成，售后工单已关闭。")
    _append_log(
        doc,
        action_type="退款",
        from_status=previous_status,
        to_status=doc.ticket_status,
        note=normalize_text(note) or _("退款已完成。"),
    )
    return _save_after_sales_action(
        doc,
        message,
    )


def prepare_replacement_sales_order(
    ticket_name: str,
    *,
    company: str | None = None,
    delivery_date: str | None = None,
    set_warehouse: str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    _ensure_after_sales_ticket_mutable(doc)
    if doc.ticket_type not in AFTER_SALES_REPLACEMENT_TYPES:
        frappe.throw(_("当前工单类型无需生成补发订单。"))
    if doc.ticket_status not in ("待补发", "待处理"):
        frappe.throw(_("只有处理结论明确后，才能生成补发订单。"))

    payload = _build_replacement_sales_order_payload(
        doc,
        company=normalize_text(company),
        delivery_date=normalize_text(delivery_date),
        set_warehouse=normalize_text(set_warehouse),
        note=normalize_text(note),
    )
    return {
        "ok": True,
        "payload": payload,
        "message": _("补发销售订单草稿已生成。"),
    }


def create_replacement_sales_order(
    ticket_name: str,
    *,
    company: str | None = None,
    delivery_date: str | None = None,
    set_warehouse: str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    _ensure_after_sales_ticket_mutable(doc)
    existing_replacement_order = normalize_text(getattr(doc, "replacement_sales_order", None))
    if existing_replacement_order and frappe.db.exists("Sales Order", existing_replacement_order):
        frappe.throw(
            _("当前售后工单已存在补发销售订单 {0}。").format(frappe.bold(existing_replacement_order))
        )
    if existing_replacement_order:
        doc.replacement_sales_order = ""
        doc.replacement_fulfillment_status = ""

    payload = _build_replacement_sales_order_payload(
        doc,
        company=normalize_text(company),
        delivery_date=normalize_text(delivery_date),
        set_warehouse=normalize_text(set_warehouse),
        note=normalize_text(note),
    )
    sales_order = frappe.get_doc(payload).insert(ignore_permissions=True)
    snapshot = sync_after_sales_ticket_replacement_order(
        ticket_name,
        sales_order_name=normalize_text(getattr(sales_order, "name", None)),
        sales_order_doc=sales_order,
        operation="create",
    )
    return {
        "ok": True,
        "sales_order": normalize_text(getattr(sales_order, "name", None)),
        "replacement_sales_order": snapshot.get("replacement_sales_order") or normalize_text(
            getattr(sales_order, "name", None)
        ),
        "replacement_fulfillment_status": snapshot.get("replacement_fulfillment_status") or _get_replacement_order_fulfillment_status(
            doc,
            sales_order_name=normalize_text(getattr(sales_order, "name", None)),
            sales_order_doc=sales_order,
        ),
        "ticket_status": snapshot.get("ticket_status") or getattr(doc, "ticket_status", None),
        "message": _("补发销售订单 {0} 已创建。").format(
            frappe.bold(normalize_text(getattr(sales_order, "name", None)) or _("未命名销售订单"))
        ),
    }


def prepare_after_sales_stock_entry(
    ticket_name: str,
    *,
    entry_mode: str | None = None,
    company: str | None = None,
    purpose: str | None = None,
    source_warehouse: str | None = None,
    target_warehouse: str | None = None,
    remark: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    if doc.ticket_status in ("已关闭", "已取消"):
        frappe.throw(_("已关闭或已取消的售后工单不能再生成库存凭证。"))

    mode = normalize_select(
        entry_mode,
        "库存凭证模式",
        AFTER_SALES_STOCK_ENTRY_MODES,
        default=_get_default_after_sales_stock_entry_mode(doc),
        alias_map=AFTER_SALES_STOCK_ENTRY_MODE_ALIASES,
    )
    purpose = normalize_select(
        purpose,
        "库存凭证用途",
        AFTER_SALES_STOCK_ENTRY_PURPOSES,
        default="Material Receipt",
        alias_map=AFTER_SALES_STOCK_ENTRY_PURPOSE_ALIASES,
    )
    company = normalize_text(company) or _get_after_sales_company(doc)
    if not company:
        frappe.throw(_("生成库存凭证前必须先确定公司。"))
    ensure_link_exists("Company", company)

    source_warehouse = normalize_text(source_warehouse)
    target_warehouse = normalize_text(target_warehouse) or doc.warehouse
    ensure_link_exists("Warehouse", source_warehouse)
    ensure_link_exists("Warehouse", target_warehouse)
    _validate_after_sales_stock_entry_warehouses(
        purpose,
        source_warehouse=source_warehouse,
        target_warehouse=target_warehouse,
    )

    items = _build_after_sales_stock_entry_items(
        doc,
        entry_mode=mode,
        purpose=purpose,
        source_warehouse=source_warehouse,
        target_warehouse=target_warehouse,
    )
    if not items:
        frappe.throw(_("当前没有可用于生成库存凭证的售后明细。"))

    payload = _build_after_sales_stock_entry_payload(
        doc,
        company=company,
        purpose=purpose,
        source_warehouse=source_warehouse,
        target_warehouse=target_warehouse,
        remark=normalize_text(remark),
        entry_mode=mode,
        items=items,
    )
    return {
        "ok": True,
        "payload": payload,
        "message": _("售后库存凭证草稿已生成。"),
    }


def submit_after_sales_stock_entry(
    ticket_name: str,
    *,
    entry_mode: str | None = None,
    company: str | None = None,
    purpose: str | None = None,
    source_warehouse: str | None = None,
    target_warehouse: str | None = None,
    remark: str | None = None,
) -> dict[str, object]:
    prepared = prepare_after_sales_stock_entry(
        ticket_name,
        entry_mode=entry_mode,
        company=company,
        purpose=purpose,
        source_warehouse=source_warehouse,
        target_warehouse=target_warehouse,
        remark=remark,
    )
    payload = prepared.get("payload") or {}
    stock_entry = frappe.get_doc(payload)
    stock_entry.insert(ignore_permissions=True)
    if not hasattr(stock_entry, "submit"):
        frappe.throw(_("库存凭证创建成功，但当前对象不支持提交流程。"))
    stock_entry.submit()
    snapshot = sync_after_sales_ticket_inventory_closure(
        ticket_name,
        stock_entry_name=getattr(stock_entry, "name", None),
        operation="submit",
    )
    return {
        "ok": True,
        "stock_entry": getattr(stock_entry, "name", None),
        "inventory_closure_status": snapshot.get("inventory_closure_status"),
        "pending_return_stock_entry": snapshot.get("pending_return_stock_entry"),
        "final_disposition_stock_entry": snapshot.get("final_disposition_stock_entry"),
        "message": _("售后库存凭证已提交。"),
    }


def get_after_sales_inventory_closure_summary(ticket_name: str) -> dict[str, object]:
    if not ticket_name:
        return {
            "inventory_closure_status": "未回写",
            "pending_return_stock_entry": "",
            "final_disposition_stock_entry": "",
        }

    detail_rows = frappe.get_all(
        "Stock Entry Detail",
        filters={"after_sales_ticket": ticket_name},
        fields=["parent", "inventory_status_from", "inventory_status_to"],
        order_by="modified desc, idx desc",
    )
    entry_names = sorted({normalize_text(row.get("parent")) for row in detail_rows or [] if normalize_text(row.get("parent"))})
    if not entry_names:
        return {
            "inventory_closure_status": "未回写",
            "pending_return_stock_entry": "",
            "final_disposition_stock_entry": "",
        }

    stock_entries = frappe.get_all(
        "Stock Entry",
        filters={"name": ["in", entry_names]},
        fields=["name", "posting_date", "posting_time", "docstatus"],
    )
    stock_entry_map = {
        normalize_text(row.get("name")): row
        for row in stock_entries or []
        if normalize_text(row.get("name")) and row.get("docstatus") == 1
    }

    pending_entries: dict[str, dict[str, object]] = {}
    final_entries: dict[str, dict[str, object]] = {}
    for row in detail_rows or []:
        parent = normalize_text(row.get("parent"))
        stock_entry = stock_entry_map.get(parent)
        if not stock_entry:
            continue

        inventory_status_from = normalize_text(row.get("inventory_status_from")).upper()
        inventory_status_to = normalize_text(row.get("inventory_status_to")).upper()
        if not inventory_status_from and inventory_status_to == "RETURN_PENDING":
            pending_entries[parent] = stock_entry
        elif inventory_status_from == "RETURN_PENDING" and inventory_status_to and inventory_status_to != "RETURN_PENDING":
            final_entries[parent] = stock_entry

    pending_return_stock_entry = _pick_latest_after_sales_stock_entry_name(pending_entries.values())
    final_disposition_stock_entry = _pick_latest_after_sales_stock_entry_name(final_entries.values())
    inventory_closure_status = "未回写"
    if final_disposition_stock_entry:
        inventory_closure_status = "已最终处理"
    elif pending_return_stock_entry:
        inventory_closure_status = "待检已入账"

    return {
        "inventory_closure_status": inventory_closure_status,
        "pending_return_stock_entry": pending_return_stock_entry,
        "final_disposition_stock_entry": final_disposition_stock_entry,
    }


def sync_after_sales_ticket_inventory_closure(
    ticket_name: str,
    *,
    stock_entry_name: str | None = None,
    operation: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    previous_status = normalize_text(getattr(doc, "ticket_status", None))
    previous_pending = normalize_text(getattr(doc, "pending_return_stock_entry", None))
    previous_final = normalize_text(getattr(doc, "final_disposition_stock_entry", None))
    previous_inventory_closure_status = normalize_text(
        getattr(doc, "inventory_closure_status", None)
    ) or "未回写"

    snapshot = get_after_sales_inventory_closure_summary(ticket_name)
    field_changes = {
        "inventory_closure_status": snapshot.get("inventory_closure_status") or "未回写",
        "pending_return_stock_entry": snapshot.get("pending_return_stock_entry") or "",
        "final_disposition_stock_entry": snapshot.get("final_disposition_stock_entry") or "",
    }
    changed = False
    for fieldname, value in field_changes.items():
        if normalize_text(getattr(doc, fieldname, None)) == normalize_text(value):
            continue
        setattr(doc, fieldname, value)
        changed = True

    status_changed = False
    if (
        previous_status == "已关闭"
        and doc.ticket_status != "已取消"
        and _after_sales_inventory_writeback_required(doc)
        and field_changes["inventory_closure_status"] != "已最终处理"
    ):
        doc.ticket_status = "待处理"
        status_changed = True

    if not changed and not status_changed:
        snapshot["ticket_status"] = getattr(doc, "ticket_status", None)
        return snapshot

    if status_changed:
        _append_log(
            doc,
            action_type="状态变更",
            from_status=previous_status,
            to_status=doc.ticket_status,
            note=_build_after_sales_inventory_reopen_note(
                stock_entry_name=stock_entry_name,
                previous_pending=previous_pending,
                previous_final=previous_final,
            ),
        )
    elif operation and stock_entry_name:
        log_payload = _build_after_sales_inventory_log_payload(
            stock_entry_name=stock_entry_name,
            operation=operation,
            previous_pending=previous_pending,
            previous_final=previous_final,
            current_pending=field_changes["pending_return_stock_entry"],
            current_final=field_changes["final_disposition_stock_entry"],
            previous_inventory_closure_status=previous_inventory_closure_status,
            current_inventory_closure_status=field_changes["inventory_closure_status"],
        )
        if log_payload:
            _append_log(doc, **log_payload)

    doc.flags.skip_after_sales_system_log = True
    try:
        doc.save(ignore_permissions=True, ignore_version=True)
    finally:
        doc.flags.skip_after_sales_system_log = False

    snapshot["ticket_status"] = doc.ticket_status
    return snapshot


def sync_after_sales_ticket_replacement_order(
    ticket_name: str,
    *,
    sales_order_name: str | None = None,
    sales_order_doc=None,
    operation: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    previous_status = normalize_text(getattr(doc, "ticket_status", None))
    previous_replacement_sales_order = normalize_text(
        getattr(doc, "replacement_sales_order", None)
    )
    previous_replacement_fulfillment_status = normalize_text(
        getattr(doc, "replacement_fulfillment_status", None)
    )

    next_replacement_sales_order = normalize_text(sales_order_name)
    next_replacement_fulfillment_status = _get_replacement_order_fulfillment_status(
        doc,
        sales_order_name=next_replacement_sales_order,
        sales_order_doc=sales_order_doc,
        operation=operation,
    )
    if not next_replacement_fulfillment_status:
        next_replacement_sales_order = ""

    changed = False
    for fieldname, value in {
        "replacement_sales_order": next_replacement_sales_order,
        "replacement_fulfillment_status": next_replacement_fulfillment_status,
    }.items():
        if normalize_text(getattr(doc, fieldname, None)) == normalize_text(value):
            continue
        setattr(doc, fieldname, value)
        changed = True

    next_status = previous_status
    log_action_type = ""
    log_note = ""
    if doc.ticket_type in AFTER_SALES_REPLACEMENT_TYPES and previous_status != "已取消":
        next_status, log_action_type, log_note = _resolve_after_sales_replacement_ticket_status(
            doc,
            previous_status=previous_status,
            previous_replacement_sales_order=previous_replacement_sales_order,
            next_replacement_sales_order=next_replacement_sales_order,
            next_replacement_fulfillment_status=next_replacement_fulfillment_status,
        )

    status_changed = next_status != previous_status
    if status_changed:
        doc.ticket_status = next_status

    appended_log = False
    if (
        operation == "create"
        and next_replacement_sales_order
        and not _has_after_sales_replacement_creation_log(doc, next_replacement_sales_order)
    ):
        _append_log(
            doc,
            action_type="补发",
            from_status=previous_status if status_changed else "",
            to_status=next_status if status_changed else "",
            note=_("补发销售订单 {0} 已创建。").format(next_replacement_sales_order),
        )
        appended_log = True
    elif status_changed:
        _append_log(
            doc,
            action_type=log_action_type or ("关闭" if next_status == "已关闭" else "状态变更"),
            from_status=previous_status,
            to_status=next_status,
            note=log_note or _("补发流程已更新。"),
        )
        appended_log = True
    elif (
        operation in ("cancel", "trash")
        and previous_replacement_sales_order
        and not next_replacement_sales_order
    ):
        _append_log(
            doc,
            action_type="补发",
            note=_("补发销售订单 {0} 已取消或失效。").format(previous_replacement_sales_order),
        )
        appended_log = True

    if not changed and not status_changed and not appended_log:
        return {
            "replacement_sales_order": previous_replacement_sales_order,
            "replacement_fulfillment_status": previous_replacement_fulfillment_status,
            "ticket_status": previous_status,
        }

    doc.flags.skip_after_sales_system_log = True
    try:
        doc.save(ignore_permissions=True, ignore_version=True)
    finally:
        doc.flags.skip_after_sales_system_log = False

    return {
        "replacement_sales_order": doc.replacement_sales_order,
        "replacement_fulfillment_status": doc.replacement_fulfillment_status,
        "ticket_status": doc.ticket_status,
    }


def close_after_sales_ticket(
    ticket_name: str,
    *,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    _ensure_after_sales_ticket_mutable(doc)

    if doc.ticket_status == "待退款" and doc.refund_status != "已退款":
        frappe.throw(_("关闭售后工单前必须先完成退款。"))
    if doc.ticket_type in AFTER_SALES_REPLACEMENT_TYPES:
        if not doc.replacement_sales_order:
            frappe.throw(_("关闭售后工单前必须先生成补发销售订单。"))
        if not _has_after_sales_completed_replacement_order(doc):
            frappe.throw(_("关闭售后工单前必须先完成补发销售订单履约。"))
    if doc.ticket_status in ("新建", "待退回", "已收货", "质检中"):
        frappe.throw(_("处理未完成前不能关闭售后工单。"))
    if _after_sales_inventory_writeback_required(doc) and not _has_after_sales_final_inventory_writeback(doc):
        frappe.throw(_("关闭售后工单前必须先完成最终处理库存回写。"))

    previous_status = doc.ticket_status
    doc.ticket_status = "已关闭"
    _append_log(
        doc,
        action_type="关闭",
        from_status=previous_status,
        to_status=doc.ticket_status,
        note=normalize_text(note) or _("售后工单已关闭。"),
    )
    return _save_after_sales_action(
        doc,
        _("售后工单已关闭。"),
    )


def cancel_after_sales_ticket(
    ticket_name: str,
    *,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_after_sales_ticket_doc(ticket_name)
    _ensure_after_sales_ticket_mutable(doc)

    previous_status = doc.ticket_status
    doc.ticket_status = "已取消"
    _append_log(
        doc,
        action_type="状态变更",
        from_status=previous_status,
        to_status=doc.ticket_status,
        note=normalize_text(note) or _("售后工单已取消。"),
    )
    return _save_after_sales_action(
        doc,
        _("售后工单已取消。"),
    )


def _validate_links(doc) -> None:
    ensure_link_exists("Sales Order", doc.sales_order)
    ensure_link_exists("Sales Invoice", doc.sales_invoice)
    ensure_link_exists("Delivery Note", doc.delivery_note)
    ensure_link_exists("Customer", doc.customer)
    ensure_link_exists("Channel Store", doc.channel_store)
    ensure_link_exists("Warehouse", doc.warehouse)
    ensure_enabled_link("Warehouse Location", doc.warehouse_location)
    ensure_enabled_link("Return Reason", doc.return_reason)
    ensure_enabled_link("Return Disposition", doc.return_disposition)
    ensure_link_exists("Sales Order", doc.replacement_sales_order)
    ensure_link_exists("Stock Entry", getattr(doc, "pending_return_stock_entry", None))
    ensure_link_exists("Stock Entry", getattr(doc, "final_disposition_stock_entry", None))
    ensure_link_exists("User", doc.owner_user)
    ensure_link_exists("User", doc.handler_user)


def _sync_from_sales_order(doc) -> None:
    if doc.sales_order:
        sales_order = _get_cached_sales_order_header(doc, doc.sales_order)
        if sales_order:
            doc.customer = normalize_text(sales_order.get("customer"))
            doc.buyer_name = normalize_text(doc.buyer_name or sales_order.get("customer_name"))
            doc.channel = normalize_text(sales_order.get("channel"))
            doc.channel_store = normalize_text(sales_order.get("channel_store"))
            doc.external_order_id = normalize_text(sales_order.get("external_order_id"))

    if not doc.customer and doc.sales_invoice:
        doc.customer = _get_cached_sales_invoice_customer(doc, doc.sales_invoice)

    if not doc.customer and doc.delivery_note:
        doc.customer = _get_cached_delivery_note_customer(doc, doc.delivery_note)

    if doc.channel_store:
        store_channel = _get_cached_channel_store_channel(doc, doc.channel_store)
        if store_channel:
            doc.channel = store_channel


def _sync_location_context(doc) -> None:
    if not doc.warehouse_location:
        return

    location_warehouse = _get_cached_warehouse_location(doc, doc.warehouse_location)
    if location_warehouse and not doc.warehouse:
        doc.warehouse = location_warehouse
    elif doc.warehouse and location_warehouse and doc.warehouse != location_warehouse:
        frappe.throw(
            _(
                "仓库库位 {0} 属于仓库 {1}，而不是 {2}。"
            ).format(
                frappe.bold(doc.warehouse_location),
                frappe.bold(location_warehouse),
                frappe.bold(doc.warehouse),
            )
        )


def _sync_refund_status(doc) -> None:
    if doc.refund_amount > 0 and doc.refund_status == "无需退款":
        doc.refund_status = "待退款"


def _validate_items(doc) -> None:
    if not doc.items:
        frappe.throw(_("至少需要一条售后明细。"))

    for row in doc.items:
        _sync_item_links(doc, row)
        _normalize_item_row(doc, row)


def _sync_item_links(doc, row) -> None:
    row.sales_order_item_ref = normalize_text(getattr(row, "sales_order_item_ref", None))
    row.delivery_note_item_ref = normalize_text(getattr(row, "delivery_note_item_ref", None))

    if row.sales_order_item_ref:
        sales_order_item = _get_cached_sales_order_item(doc, row.sales_order_item_ref)
        if not sales_order_item:
            frappe.throw(
                _("销售订单明细 {0} 不存在。").format(
                    frappe.bold(row.sales_order_item_ref)
                )
            )
        if doc.sales_order and sales_order_item.parent != doc.sales_order:
            frappe.throw(
                _(
                    "销售订单明细 {0} 不属于销售订单 {1}。"
                ).format(frappe.bold(row.sales_order_item_ref), frappe.bold(doc.sales_order))
            )
        if not doc.sales_order:
            doc.sales_order = sales_order_item.parent

        row.item_code = normalize_text(getattr(row, "item_code", None) or sales_order_item.item_code)
        row.style = normalize_text(getattr(row, "style", None) or sales_order_item.style)
        row.color_code = normalize_text(
            getattr(row, "color_code", None) or sales_order_item.color_code
        )
        row.size_code = normalize_text(
            getattr(row, "size_code", None) or sales_order_item.size_code
        )

    if row.delivery_note_item_ref:
        delivery_note_item = _get_cached_delivery_note_item(doc, row.delivery_note_item_ref)
        if not delivery_note_item:
            frappe.throw(
                _("发货单明细 {0} 不存在。").format(
                    frappe.bold(row.delivery_note_item_ref)
                )
            )
        if doc.delivery_note and delivery_note_item.parent != doc.delivery_note:
            frappe.throw(
                _(
                    "发货单明细 {0} 不属于发货单 {1}。"
                ).format(frappe.bold(row.delivery_note_item_ref), frappe.bold(doc.delivery_note))
            )
        if not doc.delivery_note:
            doc.delivery_note = delivery_note_item.parent
        if not doc.sales_order and delivery_note_item.against_sales_order:
            doc.sales_order = delivery_note_item.against_sales_order
        row.item_code = normalize_text(getattr(row, "item_code", None) or delivery_note_item.item_code)


def _normalize_item_row(doc, row) -> None:
    row.item_code = normalize_text(getattr(row, "item_code", None))
    if not row.item_code:
        frappe.throw(_("售后明细第 {0} 行的物料编码不能为空。").format(row.idx))
    ensure_link_exists("Item", row.item_code)

    item_meta = _get_cached_item_meta(doc, row.item_code)
    row.style = normalize_text(getattr(row, "style", None) or item_meta.get("style"))
    row.color_code = normalize_text(
        getattr(row, "color_code", None) or item_meta.get("color_code")
    ).upper()
    row.size_code = normalize_text(
        getattr(row, "size_code", None) or item_meta.get("size_code")
    ).upper()

    ensure_link_exists("Style", row.style)

    default_action = doc.ticket_type if doc.ticket_type in AFTER_SALES_ITEM_ACTIONS else None
    row.requested_action = normalize_select(
        getattr(row, "requested_action", None),
        "申请动作",
        AFTER_SALES_ITEM_ACTIONS,
        default=default_action,
        alias_map=AFTER_SALES_TICKET_TYPE_ALIASES,
    )
    row.qty = coerce_non_negative_float(getattr(row, "qty", None), "申请数量")
    row.received_qty = coerce_non_negative_float(
        getattr(row, "received_qty", None),
        "实收数量",
    )
    row.restock_qty = coerce_non_negative_float(
        getattr(row, "restock_qty", None),
        "可回售数量",
    )
    row.defective_qty = coerce_non_negative_float(
        getattr(row, "defective_qty", None),
        "次品数量",
    )
    row.inspection_note = normalize_text(getattr(row, "inspection_note", None))
    row.return_reason = normalize_text(
        getattr(row, "return_reason", None) or doc.return_reason
    )
    row.return_disposition = normalize_text(
        getattr(row, "return_disposition", None) or doc.return_disposition
    )
    row.inventory_status_from = normalize_text(
        getattr(row, "inventory_status_from", None)
    ).upper()
    row.inventory_status_to = normalize_text(
        getattr(row, "inventory_status_to", None)
    ).upper()

    if row.qty <= 0:
        frappe.throw(_("售后明细第 {0} 行的申请数量必须大于 0。").format(row.idx))

    if row.received_qty > row.qty:
        frappe.throw(
            _("售后明细第 {0} 行的实收数量不能超过申请数量。").format(row.idx)
        )

    if row.received_qty > 0 and (row.restock_qty + row.defective_qty) > row.received_qty:
        frappe.throw(
            _(
                "售后明细第 {0} 行的可回售数量与次品数量之和不能超过实收数量。"
            ).format(row.idx)
        )

    ensure_enabled_link("Return Reason", row.return_reason)
    if row.return_disposition:
        ensure_enabled_link("Return Disposition", row.return_disposition)
        target_status = _get_cached_return_disposition_target_status(doc, row.return_disposition)
        if not row.inventory_status_to:
            row.inventory_status_to = target_status
        elif row.inventory_status_to != target_status:
            frappe.throw(
                _(
                    "售后明细第 {2} 行的退货处理结果 {0} 要求目标库存状态必须为 {1}。"
                ).format(
                    frappe.bold(row.return_disposition),
                    frappe.bold(get_inventory_status_display(target_status)),
                    row.idx,
                )
            )

    if row.inventory_status_to and not row.inventory_status_from and (
        row.return_reason or row.return_disposition
    ):
        row.inventory_status_from = "RETURN_PENDING"

    if row.inventory_status_from or row.inventory_status_to:
        validate_inventory_status_transition(
            row.inventory_status_from,
            row.inventory_status_to,
            row_label=f"售后明细第 {row.idx} 行",
        )


def _normalize_logs(doc) -> None:
    for row in doc.logs or []:
        row.action_time = _normalize_datetime(getattr(row, "action_time", None), use_now=True)
        row.action_type = normalize_select(
            getattr(row, "action_type", None),
            "操作类型",
            AFTER_SALES_LOG_ACTIONS,
            default="备注",
            alias_map=AFTER_SALES_LOG_ACTION_ALIASES,
        )
        row.from_status = AFTER_SALES_TICKET_STATUS_ALIASES.get(
            normalize_text(getattr(row, "from_status", None)),
            normalize_text(getattr(row, "from_status", None)),
        )
        row.to_status = AFTER_SALES_TICKET_STATUS_ALIASES.get(
            normalize_text(getattr(row, "to_status", None)),
            normalize_text(getattr(row, "to_status", None)),
        )
        row.operator = normalize_text(getattr(row, "operator", None)) or frappe.session.user
        row.note = normalize_text(getattr(row, "note", None))
        ensure_link_exists("User", row.operator)


def _append_system_logs(doc) -> None:
    if getattr(doc.flags, "skip_after_sales_system_log", False):
        return

    if doc.is_new():
        if not _has_action_log(doc, "创建"):
            _append_log(
                doc,
                action_type="创建",
                to_status=doc.ticket_status,
                note=_("售后工单已创建。"),
            )
        return

    current_db_status = normalize_text(
        frappe.db.get_value("After Sales Ticket", doc.name, "ticket_status")
    )
    previous_status = AFTER_SALES_TICKET_STATUS_ALIASES.get(current_db_status, current_db_status)
    if previous_status and previous_status != doc.ticket_status:
        _append_log(
            doc,
            action_type="状态变更",
            from_status=previous_status,
            to_status=doc.ticket_status,
            note=_("售后工单状态已更新。"),
        )


def _get_after_sales_ticket_doc(ticket_name: str):
    if not ticket_name:
        frappe.throw(_("售后工单不能为空。"))
    return frappe.get_doc("After Sales Ticket", ticket_name)


def _ensure_after_sales_ticket_mutable(doc) -> None:
    if doc.ticket_status == "已关闭":
        frappe.throw(_("已关闭的售后工单不能修改。"))
    if doc.ticket_status == "已取消":
        frappe.throw(_("已取消的售后工单不能修改。"))


def _determine_after_sales_decision_status(doc) -> str:
    if doc.ticket_type in ("仅退款", "退货退款"):
        return "待退款"
    if doc.ticket_type in AFTER_SALES_REPLACEMENT_TYPES:
        return "待补发"
    return "待处理"


def _save_after_sales_action(doc, message: str) -> dict[str, object]:
    doc.flags.skip_after_sales_system_log = True
    try:
        doc.save(ignore_permissions=True)
    finally:
        doc.flags.skip_after_sales_system_log = False
    return _build_after_sales_response(doc, message)


def _build_after_sales_response(doc, message: str) -> dict[str, object]:
    return {
        "ok": True,
        "name": doc.name,
        "ticket_no": doc.ticket_no or doc.name,
        "ticket_status": doc.ticket_status,
        "refund_status": doc.refund_status,
        "refund_amount": doc.refund_amount,
        "replacement_sales_order": doc.replacement_sales_order,
        "replacement_fulfillment_status": getattr(doc, "replacement_fulfillment_status", None),
        "received_at": str(doc.received_at) if doc.received_at else None,
        "message": message,
    }


def _build_replacement_sales_order_payload(
    doc,
    *,
    company: str | None,
    delivery_date: str | None,
    set_warehouse: str | None,
    note: str | None,
) -> dict[str, object]:
    customer = normalize_text(doc.customer)
    if not customer:
        frappe.throw(_("生成补发销售订单前必须先确定客户。"))
    ensure_link_exists("Customer", customer)

    company = company or _get_after_sales_company(doc)
    if not company:
        frappe.throw(_("生成补发销售订单前必须先确定公司。"))
    ensure_link_exists("Company", company)
    ensure_link_exists("Warehouse", set_warehouse)

    items = _build_replacement_sales_order_items(doc, set_warehouse=set_warehouse)
    if not items:
        frappe.throw(_("生成补发销售订单前，至少需要一条补发明细。"))

    payload = {
        "doctype": "Sales Order",
        "company": company,
        "customer": customer,
        "transaction_date": nowdate(),
        "delivery_date": delivery_date or _get_after_sales_delivery_date(doc),
        "channel": doc.channel,
        "channel_store": doc.channel_store,
        "set_warehouse": set_warehouse or doc.warehouse,
        "external_order_id": doc.external_order_id,
        "after_sales_ticket": doc.name,
        "remarks": note or _("由售后工单 {0} 自动生成。").format(doc.name),
        "items": items,
    }
    return _filter_doc_payload("Sales Order", payload, items=items)


def _build_replacement_sales_order_items(
    doc,
    *,
    set_warehouse: str | None,
) -> list[dict[str, object]]:
    items = []
    for row in doc.items or []:
        if row.requested_action not in AFTER_SALES_REPLACEMENT_TYPES:
            continue

        qty = row.received_qty or row.qty
        qty = coerce_non_negative_float(qty, "补发数量")
        if qty <= 0:
            continue

        source_row = None
        if row.sales_order_item_ref:
            source_row = _get_cached_sales_order_item(doc, row.sales_order_item_ref)

        item_payload = {
            "doctype": "Sales Order Item",
            "item_code": row.item_code,
            "qty": qty,
            "rate": (source_row or {}).get("rate"),
            "uom": (source_row or {}).get("uom"),
            "delivery_date": (source_row or {}).get("delivery_date"),
            "warehouse": set_warehouse or (source_row or {}).get("warehouse") or doc.warehouse,
            "style": row.style,
            "color_code": row.color_code,
            "size_code": row.size_code,
        }
        items.append(_filter_doc_payload("Sales Order Item", item_payload))

    return items


def _get_default_after_sales_stock_entry_mode(doc) -> str:
    if doc.ticket_status in ("待退款", "待补发", "待处理"):
        return "最终处理"
    return "待检入库"


def _validate_after_sales_stock_entry_warehouses(
    purpose: str,
    *,
    source_warehouse: str | None,
    target_warehouse: str | None,
) -> None:
    if purpose == "Material Receipt":
        if not target_warehouse:
            frappe.throw(_("物料入库时，目标仓库不能为空。"))
        return

    if purpose == "Material Transfer":
        if not source_warehouse:
            frappe.throw(_("物料转移时，来源仓库不能为空。"))
        if not target_warehouse:
            frappe.throw(_("物料转移时，目标仓库不能为空。"))
        if source_warehouse == target_warehouse:
            frappe.throw(_("物料转移时，来源仓库和目标仓库不能相同。"))


def _build_after_sales_stock_entry_items(
    doc,
    *,
    entry_mode: str,
    purpose: str,
    source_warehouse: str | None,
    target_warehouse: str | None,
) -> list[dict[str, object]]:
    items = []
    for row in doc.items or []:
        row_items = _build_after_sales_stock_entry_row_items(
            doc,
            row,
            entry_mode=entry_mode,
            purpose=purpose,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
        )
        items.extend(row_items)
    return items


def _build_after_sales_stock_entry_row_items(
    doc,
    row,
    *,
    entry_mode: str,
    purpose: str,
    source_warehouse: str | None,
    target_warehouse: str | None,
) -> list[dict[str, object]]:
    if entry_mode == "待检入库":
        qty = coerce_non_negative_float(row.received_qty, "实收数量")
        if qty <= 0:
            return []
        return [
            _build_after_sales_stock_entry_row_payload(
                doc,
                row,
                qty=qty,
                purpose=purpose,
                source_warehouse=source_warehouse,
                target_warehouse=target_warehouse,
                inventory_status_from="",
                inventory_status_to="RETURN_PENDING",
                return_reason=row.return_reason or doc.return_reason,
                return_disposition="",
            )
        ]

    target_status = _get_after_sales_target_inventory_status(doc, row)
    return_reason = normalize_text(row.return_reason or doc.return_reason)
    if not return_reason:
        frappe.throw(
            _("生成最终处理库存凭证前，售后明细第 {0} 行必须填写退货原因。").format(row.idx)
        )
    qty = _get_after_sales_final_entry_qty(row, target_status)
    if qty <= 0:
        return []

    return [
        _build_after_sales_stock_entry_row_payload(
            doc,
            row,
            qty=qty,
            purpose=purpose,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
            inventory_status_from="RETURN_PENDING",
            inventory_status_to=target_status,
            return_reason=return_reason,
            return_disposition=row.return_disposition or doc.return_disposition,
        )
    ]


def _get_after_sales_target_inventory_status(doc, row) -> str:
    target_status = normalize_text(row.inventory_status_to).upper()
    if target_status:
        return target_status

    disposition = normalize_text(row.return_disposition or doc.return_disposition)
    if disposition:
        ensure_enabled_link("Return Disposition", disposition)
        target_status = normalize_text(
            frappe.db.get_value("Return Disposition", disposition, "target_inventory_status")
        ).upper()
    if not target_status:
        frappe.throw(
            _("生成最终处理库存凭证前，售后明细第 {0} 行必须填写退货处理结果或目标库存状态。").format(row.idx)
        )
    return target_status


def _get_after_sales_final_entry_qty(row, target_status: str) -> float:
    restock_qty = coerce_non_negative_float(row.restock_qty, "可回售数量")
    defective_qty = coerce_non_negative_float(row.defective_qty, "次品数量")
    received_qty = coerce_non_negative_float(row.received_qty, "实收数量")

    if restock_qty > 0 and defective_qty > 0:
        frappe.throw(
            _(
                "售后明细第 {0} 行同时填写了可回售数量和次品数量，请拆分明细或手工创建库存凭证。"
            ).format(row.idx)
        )

    if target_status == "SELLABLE" and restock_qty > 0:
        return restock_qty

    if target_status == "DEFECTIVE" and defective_qty > 0:
        return defective_qty

    if target_status != "SELLABLE" and defective_qty > 0:
        return defective_qty

    if restock_qty > 0 and target_status != "DEFECTIVE":
        return restock_qty

    return received_qty


def _build_after_sales_stock_entry_row_payload(
    doc,
    row,
    *,
    qty: float,
    purpose: str,
    source_warehouse: str | None,
    target_warehouse: str | None,
    inventory_status_from: str,
    inventory_status_to: str,
    return_reason: str,
    return_disposition: str,
) -> dict[str, object]:
    item_data = _get_item_basic_data(row.item_code)
    payload = {
        "doctype": "Stock Entry Detail",
        "item_code": row.item_code,
        "qty": qty,
        "transfer_qty": qty,
        "basic_qty": qty,
        "item_name": item_data.get("item_name"),
        "uom": item_data.get("stock_uom"),
        "stock_uom": item_data.get("stock_uom"),
        "s_warehouse": source_warehouse if purpose == "Material Transfer" else "",
        "t_warehouse": target_warehouse,
        "style": row.style,
        "color_code": row.color_code,
        "size_code": row.size_code,
        "inventory_status_from": inventory_status_from,
        "inventory_status_to": inventory_status_to,
        "return_reason": return_reason,
        "return_disposition": return_disposition,
        "after_sales_ticket": doc.name,
    }
    return _filter_doc_payload("Stock Entry Detail", payload)


def _build_after_sales_stock_entry_payload(
    doc,
    *,
    company: str,
    purpose: str,
    source_warehouse: str | None,
    target_warehouse: str | None,
    remark: str,
    entry_mode: str,
    items: list[dict[str, object]],
) -> dict[str, object]:
    stock_entry_type = _get_cached_after_sales_stock_entry_type(doc, purpose)
    mode_label = "最终处理" if entry_mode == "最终处理" else "待检入库"
    payload = {
        "doctype": "Stock Entry",
        "purpose": purpose,
        "stock_entry_type": stock_entry_type,
        "company": company,
        "after_sales_ticket": doc.name,
        "from_warehouse": source_warehouse,
        "to_warehouse": target_warehouse,
        "remarks": remark or _("由售后工单 {0} 自动生成（{1}）。").format(doc.name, mode_label),
        "items": items,
    }
    return _filter_doc_payload("Stock Entry", payload, items=items)


def _get_after_sales_company(doc) -> str | None:
    if doc.sales_order:
        company = normalize_text(_get_cached_sales_order_header(doc, doc.sales_order).get("company"))
        if company:
            return company

    return _get_cached_after_sales_default_company(doc) or None


def _after_sales_inventory_writeback_required(doc) -> bool:
    for row in getattr(doc, "items", None) or []:
        if coerce_non_negative_float(getattr(row, "received_qty", None), "实收数量") > 0:
            return True
    return False


def _has_after_sales_completed_replacement_order(doc) -> bool:
    return (
        _get_replacement_order_fulfillment_status(doc)
        in AFTER_SALES_COMPLETED_REPLACEMENT_FULFILLMENT_STATUSES
    )


def _has_after_sales_final_inventory_writeback(doc) -> bool:
    if not getattr(doc, "name", None):
        return False
    snapshot = get_after_sales_inventory_closure_summary(doc.name)
    return snapshot.get("inventory_closure_status") == "已最终处理"


def _get_after_sales_delivery_date(doc) -> str:
    if doc.sales_order:
        delivery_date = _get_cached_sales_order_header(doc, doc.sales_order).get("delivery_date")
        if delivery_date:
            return str(getdate(delivery_date))
    return nowdate()


def _filter_doc_payload(
    doctype: str,
    payload: dict[str, object],
    *,
    items: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    meta = frappe.get_meta(doctype)
    filtered = {"doctype": doctype}
    for fieldname, value in payload.items():
        if fieldname == "doctype":
            continue
        if fieldname == "items":
            if meta.has_field("items") and items is not None:
                filtered["items"] = items
            continue
        if value in (None, ""):
            continue
        if meta.has_field(fieldname):
            filtered[fieldname] = value
    return filtered


def _pick_latest_after_sales_stock_entry_name(rows) -> str:
    latest_name = ""
    latest_key = ("", "", "")
    for row in rows or []:
        stock_entry_name = normalize_text(row.get("name"))
        if not stock_entry_name:
            continue
        current_key = (
            str(row.get("posting_date") or ""),
            str(row.get("posting_time") or ""),
            stock_entry_name,
        )
        if current_key >= latest_key:
            latest_key = current_key
            latest_name = stock_entry_name
    return latest_name


def _resolve_after_sales_replacement_ticket_status(
    doc,
    *,
    previous_status: str,
    previous_replacement_sales_order: str,
    next_replacement_sales_order: str,
    next_replacement_fulfillment_status: str,
) -> tuple[str, str, str]:
    if not next_replacement_sales_order:
        next_status = "待补发"
        if previous_status == "已关闭":
            return (
                next_status,
                "状态变更",
                _("补发销售订单 {0} 已取消或失效，工单重新回到待补发。").format(
                    previous_replacement_sales_order
                ),
            )
        return next_status, "", ""

    if (
        next_replacement_fulfillment_status
        in AFTER_SALES_COMPLETED_REPLACEMENT_FULFILLMENT_STATUSES
    ):
        if _after_sales_inventory_writeback_required(doc) and not _has_after_sales_final_inventory_writeback(doc):
            return (
                "待处理",
                "状态变更",
                _("补发销售订单 {0} 已完成，待最终处理库存回写后再关闭售后工单。").format(
                    next_replacement_sales_order
                ),
            )
        return (
            "已关闭",
            "关闭",
            _("补发销售订单 {0} 已完成，售后工单已自动关闭。").format(
                next_replacement_sales_order
            ),
        )

    if previous_status == "已关闭":
        return (
            "待补发",
            "状态变更",
            _("补发销售订单 {0} 已重新回到履约中，工单重新回到待补发。").format(
                next_replacement_sales_order
            ),
        )
    return "待补发", "", ""


def _build_after_sales_inventory_log_payload(
    *,
    stock_entry_name: str,
    operation: str,
    previous_pending: str,
    previous_final: str,
    current_pending: str,
    current_final: str,
    previous_inventory_closure_status: str,
    current_inventory_closure_status: str,
) -> dict[str, object] | None:
    entry_kind = _resolve_after_sales_stock_entry_kind(
        stock_entry_name=stock_entry_name,
        previous_pending=previous_pending,
        previous_final=previous_final,
        current_pending=current_pending,
        current_final=current_final,
    )
    if operation == "submit":
        if entry_kind == "final" and previous_inventory_closure_status != current_inventory_closure_status:
            return {
                "action_type": "质检",
                "note": _("售后最终处理凭证 {0} 已提交。").format(stock_entry_name),
            }
        if entry_kind == "pending" and previous_inventory_closure_status == "未回写":
            return {
                "action_type": "收货",
                "note": _("售后待检入库凭证 {0} 已提交。").format(stock_entry_name),
            }
        return None

    if operation == "cancel":
        if entry_kind == "final":
            return {
                "action_type": "备注",
                "note": _("售后最终处理凭证 {0} 已撤销。").format(stock_entry_name),
            }
        if entry_kind == "pending":
            return {
                "action_type": "备注",
                "note": _("售后待检入库凭证 {0} 已撤销。").format(stock_entry_name),
            }
        return {
            "action_type": "备注",
            "note": _("售后库存凭证 {0} 已撤销。").format(stock_entry_name),
        }

    return None


def _build_after_sales_inventory_reopen_note(
    *,
    stock_entry_name: str | None,
    previous_pending: str,
    previous_final: str,
) -> str:
    if stock_entry_name:
        entry_kind = _resolve_after_sales_stock_entry_kind(
            stock_entry_name=stock_entry_name,
            previous_pending=previous_pending,
            previous_final=previous_final,
            current_pending="",
            current_final="",
        )
        if entry_kind == "final":
            return _("售后最终处理凭证 {0} 已撤销，工单重新回到待处理。").format(stock_entry_name)
        if entry_kind == "pending":
            return _("售后待检入库凭证 {0} 已撤销，工单重新回到待处理。").format(stock_entry_name)
    return _("售后库存回写状态已回退，工单重新回到待处理。")


def _resolve_after_sales_stock_entry_kind(
    *,
    stock_entry_name: str,
    previous_pending: str,
    previous_final: str,
    current_pending: str,
    current_final: str,
) -> str | None:
    if stock_entry_name in {normalize_text(previous_final), normalize_text(current_final)}:
        return "final"
    if stock_entry_name in {normalize_text(previous_pending), normalize_text(current_pending)}:
        return "pending"
    return None


def _get_replacement_order_fulfillment_status(
    doc,
    *,
    sales_order_name: str | None = None,
    sales_order_doc=None,
    operation: str | None = None,
) -> str:
    snapshot = _get_cached_replacement_sales_order_snapshot(
        doc,
        sales_order_name=sales_order_name,
        sales_order_doc=sales_order_doc,
        operation=operation,
    )
    if not snapshot:
        return ""

    if str(snapshot.get("docstatus")) == "2":
        return ""

    fulfillment_status = normalize_select(
        snapshot.get("fulfillment_status"),
        "补发履约状态",
        AFTER_SALES_REPLACEMENT_FULFILLMENT_OPTIONS,
        default="",
    )
    if fulfillment_status:
        return fulfillment_status

    status = normalize_text(snapshot.get("status"))
    if status in ("Closed", "已关闭"):
        return "已关闭"
    if status in ("Completed", "已完成"):
        return "已完成"
    return "待配货"


def _has_after_sales_replacement_creation_log(doc, sales_order_name: str) -> bool:
    expected_note = _("补发销售订单 {0} 已创建。").format(sales_order_name)
    for row in getattr(doc, "logs", None) or []:
        if normalize_text(getattr(row, "action_type", None)) != "补发":
            continue
        if normalize_text(getattr(row, "note", None)) == expected_note:
            return True
    return False


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


def _reset_after_sales_validation_cache(doc) -> None:
    cache = {
        "sales_order_items": {},
        "delivery_note_items": {},
        "item_meta": {},
        "return_disposition_targets": {},
        "sales_orders": {},
        "sales_invoice_customers": {},
        "delivery_note_customers": {},
        "channel_store_channels": {},
        "warehouse_locations": {},
        "default_company": "",
        "default_company_loaded": False,
        "stock_entry_types": {},
        "replacement_sales_orders": {},
    }
    flags = getattr(doc, "flags", None)
    if flags is not None:
        flags.after_sales_validation_cache = cache
        return
    doc._after_sales_validation_cache = cache


def _get_after_sales_validation_cache(doc) -> dict[str, dict[str, object]]:
    flags = getattr(doc, "flags", None)
    if flags is not None:
        cache = getattr(flags, "after_sales_validation_cache", None)
        if isinstance(cache, dict):
            return cache
    else:
        cache = getattr(doc, "_after_sales_validation_cache", None)
        if isinstance(cache, dict):
            return cache

    _reset_after_sales_validation_cache(doc)
    return _get_after_sales_validation_cache(doc)


def _get_cached_sales_order_item(doc, sales_order_item_ref: str):
    cache = _get_after_sales_validation_cache(doc)["sales_order_items"]
    if sales_order_item_ref not in cache:
        cache[sales_order_item_ref] = frappe.db.get_value(
            "Sales Order Item",
            sales_order_item_ref,
            [
                "parent",
                "item_code",
                "style",
                "color_code",
                "size_code",
                "rate",
                "uom",
                "warehouse",
                "delivery_date",
            ],
            as_dict=True,
        )
    return cache[sales_order_item_ref]


def _get_cached_delivery_note_item(doc, delivery_note_item_ref: str):
    cache = _get_after_sales_validation_cache(doc)["delivery_note_items"]
    if delivery_note_item_ref not in cache:
        cache[delivery_note_item_ref] = frappe.db.get_value(
            "Delivery Note Item",
            delivery_note_item_ref,
            ["parent", "item_code", "against_sales_order"],
            as_dict=True,
        )
    return cache[delivery_note_item_ref]


def _get_cached_item_meta(doc, item_code: str):
    cache = _get_after_sales_validation_cache(doc)["item_meta"]
    if item_code not in cache:
        cache[item_code] = frappe.db.get_value(
            "Item",
            item_code,
            ["style", "color_code", "size_code"],
            as_dict=True,
        ) or {}
    return cache[item_code]


def _get_cached_return_disposition_target_status(doc, return_disposition: str) -> str:
    cache = _get_after_sales_validation_cache(doc)["return_disposition_targets"]
    if return_disposition not in cache:
        cache[return_disposition] = normalize_text(
            frappe.db.get_value(
                "Return Disposition",
                return_disposition,
                "target_inventory_status",
            )
        ).upper()
    return cache[return_disposition]


def _get_cached_after_sales_default_company(doc) -> str:
    cache = _get_after_sales_validation_cache(doc)
    if cache.get("default_company_loaded"):
        return normalize_text(cache.get("default_company"))

    defaults = [
        frappe.defaults.get_user_default("Company"),
        frappe.defaults.get_global_default("company"),
        frappe.defaults.get_global_default("Company"),
    ]
    company = ""
    for candidate in defaults:
        normalized_company = normalize_text(candidate)
        if normalized_company and frappe.db.exists("Company", normalized_company):
            company = normalized_company
            break

    cache["default_company"] = company
    cache["default_company_loaded"] = True
    return company


def _get_cached_after_sales_stock_entry_type(doc, purpose: str) -> str | None:
    normalized_purpose = normalize_text(purpose)
    if not normalized_purpose:
        return None

    cache = _get_after_sales_validation_cache(doc)["stock_entry_types"]
    if normalized_purpose not in cache:
        cache[normalized_purpose] = (
            normalized_purpose if frappe.db.exists("Stock Entry Type", normalized_purpose) else None
        )
    return cache[normalized_purpose]


def _get_cached_sales_order_header(doc, sales_order_name: str):
    cache = _get_after_sales_validation_cache(doc)["sales_orders"]
    normalized_name = normalize_text(sales_order_name)
    if not normalized_name:
        return {}
    if normalized_name not in cache:
        cache[normalized_name] = frappe.db.get_value(
            "Sales Order",
            normalized_name,
            [
                "customer",
                "customer_name",
                "channel",
                "channel_store",
                "external_order_id",
                "company",
                "delivery_date",
            ],
            as_dict=True,
        ) or {}
    return cache[normalized_name]


def _get_cached_replacement_sales_order_snapshot(
    doc,
    *,
    sales_order_name: str | None = None,
    sales_order_doc=None,
    operation: str | None = None,
):
    normalized_name = normalize_text(sales_order_name) or normalize_text(
        getattr(doc, "replacement_sales_order", None)
    )
    if not normalized_name:
        return {}

    if operation in ("cancel", "trash"):
        return {}

    if (
        sales_order_doc is not None
        and normalize_text(getattr(sales_order_doc, "name", None)) == normalized_name
    ):
        return {
            "name": normalized_name,
            "docstatus": getattr(sales_order_doc, "docstatus", 0),
            "status": normalize_text(getattr(sales_order_doc, "status", None)),
            "fulfillment_status": normalize_text(getattr(sales_order_doc, "fulfillment_status", None)),
        }

    cache = _get_after_sales_validation_cache(doc)["replacement_sales_orders"]
    if normalized_name not in cache:
        cache[normalized_name] = frappe.db.get_value(
            "Sales Order",
            normalized_name,
            ["docstatus", "status", "fulfillment_status"],
            as_dict=True,
        ) or {}
    snapshot = cache.get(normalized_name) or {}
    if not snapshot:
        return {}
    snapshot = dict(snapshot)
    snapshot["name"] = normalized_name
    return snapshot


def _get_cached_sales_invoice_customer(doc, sales_invoice_name: str) -> str:
    cache = _get_after_sales_validation_cache(doc)["sales_invoice_customers"]
    normalized_name = normalize_text(sales_invoice_name)
    if not normalized_name:
        return ""
    if normalized_name not in cache:
        cache[normalized_name] = normalize_text(
            frappe.db.get_value("Sales Invoice", normalized_name, "customer")
        )
    return cache[normalized_name]


def _get_cached_delivery_note_customer(doc, delivery_note_name: str) -> str:
    cache = _get_after_sales_validation_cache(doc)["delivery_note_customers"]
    normalized_name = normalize_text(delivery_note_name)
    if not normalized_name:
        return ""
    if normalized_name not in cache:
        cache[normalized_name] = normalize_text(
            frappe.db.get_value("Delivery Note", normalized_name, "customer")
        )
    return cache[normalized_name]


def _get_cached_channel_store_channel(doc, channel_store_name: str) -> str:
    cache = _get_after_sales_validation_cache(doc)["channel_store_channels"]
    normalized_name = normalize_text(channel_store_name)
    if not normalized_name:
        return ""
    if normalized_name not in cache:
        cache[normalized_name] = normalize_text(
            frappe.db.get_value("Channel Store", normalized_name, "channel")
        )
    return cache[normalized_name]


def _get_cached_warehouse_location(doc, warehouse_location_name: str) -> str:
    cache = _get_after_sales_validation_cache(doc)["warehouse_locations"]
    normalized_name = normalize_text(warehouse_location_name)
    if not normalized_name:
        return ""
    if normalized_name not in cache:
        cache[normalized_name] = normalize_text(
            frappe.db.get_value("Warehouse Location", normalized_name, "warehouse")
        )
    return cache[normalized_name]


def _normalize_datetime(value, *, use_now: bool = False):
    if not value:
        return now_datetime() if use_now else None
    return get_datetime(value)


def _is_unsaved_name(value: str) -> bool:
    normalized = normalize_text(value)
    return not normalized or normalized.startswith("New ")
