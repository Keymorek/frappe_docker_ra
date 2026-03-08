from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime, nowdate

from fashion_erp.style.services.style_service import ensure_link_exists, normalize_text


MANUAL_ITEM_FULFILLMENT_STATUSES = {
    "待处理",
    "已锁库存",
    "拣货中",
    "已拣货",
    "打包中",
    "待发货",
    "售后中",
    "已签收",
    "已关闭",
    "已取消",
}
IN_PROGRESS_ITEM_FULFILLMENT_STATUSES = {"已锁库存", "拣货中", "已拣货", "打包中", "待发货"}
SHIPPED_ITEM_FULFILLMENT_STATUSES = {"部分发货", "已发货", "已签收", "已关闭"}
COMPLETED_SALES_ORDER_STATUSES = {"Completed", "已完成"}
CLOSED_SALES_ORDER_STATUSES = {"Closed", "已关闭"}
CANCELLED_SALES_ORDER_STATUSES = {"Cancelled", "已取消"}

ALLOCATION_SOURCE_STATUSES = {"待处理"}
PICK_SOURCE_STATUSES = {"待处理", "已锁库存", "拣货中"}
PACK_SOURCE_STATUSES = {"已拣货", "打包中"}
DELIVERY_SOURCE_STATUSES = {"待发货", "部分发货"}
ACTIVE_AFTER_SALES_TICKET_STATUSES = {"新建", "待退回", "已收货", "质检中", "待处理", "待退款", "待补发"}


def sync_sales_order_fulfillment_status(doc) -> bool:
    changed = False
    after_sales_context = _get_sales_order_after_sales_context(doc)

    for row in list(getattr(doc, "items", None) or []):
        next_status = _get_sales_order_item_fulfillment_status(
            doc,
            row,
            after_sales_context=after_sales_context,
        )
        if normalize_text(getattr(row, "fulfillment_status", None)) != next_status:
            row.fulfillment_status = next_status
            changed = True

    next_order_status = _get_sales_order_fulfillment_status(
        doc,
        after_sales_context=after_sales_context,
    )
    if normalize_text(getattr(doc, "fulfillment_status", None)) != next_order_status:
        doc.fulfillment_status = next_order_status
        changed = True

    return changed


def sync_linked_sales_orders_fulfillment_status(doc) -> None:
    for sales_order_name in _collect_delivery_note_sales_orders(doc):
        if not frappe.db.exists("Sales Order", sales_order_name):
            continue

        sales_order = frappe.get_doc("Sales Order", sales_order_name)
        if not sync_sales_order_fulfillment_status(sales_order):
            continue

        sales_order.save(ignore_permissions=True, ignore_version=True)


@frappe.whitelist()
def allocate_sales_order(
    order_name: str,
    item_names: list[str] | str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    return _apply_sales_order_row_action(
        order_name,
        action_label="配货",
        target_status="已锁库存",
        allowed_statuses=ALLOCATION_SOURCE_STATUSES,
        item_names=item_names,
        note=note,
    )


@frappe.whitelist()
def pick_sales_order(
    order_name: str,
    item_names: list[str] | str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    return _apply_sales_order_row_action(
        order_name,
        action_label="拣货",
        target_status="已拣货",
        allowed_statuses=PICK_SOURCE_STATUSES,
        item_names=item_names,
        note=note,
    )


@frappe.whitelist()
def pack_sales_order(
    order_name: str,
    item_names: list[str] | str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    return _apply_sales_order_row_action(
        order_name,
        action_label="打包",
        target_status="待发货",
        allowed_statuses=PACK_SOURCE_STATUSES,
        item_names=item_names,
        note=note,
    )


@frappe.whitelist()
def prepare_sales_order_delivery_note(
    order_name: str,
    item_names: list[str] | str | None = None,
    posting_date=None,
    posting_time=None,
    set_warehouse: str | None = None,
    company: str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_sales_order_doc(order_name)
    sync_sales_order_fulfillment_status(doc)
    _ensure_sales_order_actionable(doc, action_label="发货")

    item_name_set = _normalize_item_name_set(item_names)
    rows = _get_actionable_rows(
        doc,
        item_name_set=item_name_set,
        allowed_statuses=DELIVERY_SOURCE_STATUSES,
    )
    if not rows:
        frappe.throw(_("销售订单 {0} 当前没有待发货明细。").format(frappe.bold(doc.name)))

    delivery_note = frappe.get_doc(
        _build_delivery_note_payload(
            doc,
            rows,
            posting_date=posting_date,
            posting_time=posting_time,
            set_warehouse=set_warehouse,
            company=company,
            note=note,
        )
    )
    delivery_note.insert(ignore_permissions=True)

    return {
        "ok": True,
        "sales_order": doc.name,
        "fulfillment_status": normalize_text(getattr(doc, "fulfillment_status", None)),
        "delivery_note": normalize_text(getattr(delivery_note, "name", None)),
        "row_count": len(rows),
        "item_names": [normalize_text(getattr(row, "name", None)) for row in rows if normalize_text(getattr(row, "name", None))],
        "message": _("已生成发货单草稿 {0}。").format(
            frappe.bold(normalize_text(getattr(delivery_note, "name", None)) or _("未命名发货单"))
        ),
    }


def _apply_sales_order_row_action(
    order_name: str,
    *,
    action_label: str,
    target_status: str,
    allowed_statuses: set[str],
    item_names: list[str] | str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_sales_order_doc(order_name)
    sync_sales_order_fulfillment_status(doc)
    _ensure_sales_order_actionable(doc, action_label=action_label)

    item_name_set = _normalize_item_name_set(item_names)
    rows = _get_actionable_rows(
        doc,
        item_name_set=item_name_set,
        allowed_statuses=allowed_statuses,
    )
    if not rows:
        frappe.throw(_("销售订单 {0} 当前没有可执行{1}的明细。").format(
            frappe.bold(doc.name),
            frappe.bold(action_label),
        ))

    for row in rows:
        _resolve_row_warehouse(doc, row, action_label=action_label)
        row.fulfillment_status = target_status

    sync_sales_order_fulfillment_status(doc)
    doc.save(ignore_permissions=True)

    message = _("销售订单 {0} 已完成{1}，影响 {2} 条明细。").format(
        frappe.bold(doc.name),
        frappe.bold(action_label),
        len(rows),
    )
    if normalize_text(note):
        message = _("{0} 备注：{1}").format(message, normalize_text(note))

    return {
        "ok": True,
        "sales_order": doc.name,
        "action": action_label,
        "fulfillment_status": normalize_text(getattr(doc, "fulfillment_status", None)),
        "affected_rows": len(rows),
        "items": [
            {
                "name": normalize_text(getattr(row, "name", None)),
                "item_code": normalize_text(getattr(row, "item_code", None)),
                "fulfillment_status": normalize_text(getattr(row, "fulfillment_status", None)),
                "pending_qty": _get_pending_qty(row),
            }
            for row in rows
        ],
        "message": message,
    }


def _build_delivery_note_payload(
    doc,
    rows,
    *,
    posting_date=None,
    posting_time=None,
    set_warehouse: str | None = None,
    company: str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    customer = normalize_text(getattr(doc, "customer", None))
    if not customer:
        frappe.throw(_("生成发货单前必须先填写客户。"))
    ensure_link_exists("Customer", customer)

    company = normalize_text(company) or normalize_text(getattr(doc, "company", None))
    if not company:
        frappe.throw(_("生成发货单前必须先填写公司。"))
    ensure_link_exists("Company", company)

    warehouse = normalize_text(set_warehouse) or normalize_text(getattr(doc, "set_warehouse", None))
    if warehouse:
        ensure_link_exists("Warehouse", warehouse)

    items = [_build_delivery_note_item_payload(doc, row, default_warehouse=warehouse) for row in rows]
    payload = {
        "doctype": "Delivery Note",
        "customer": customer,
        "company": company,
        "posting_date": _normalize_date(posting_date, use_today=True),
        "posting_time": _normalize_time(posting_time),
        "set_warehouse": warehouse,
        "remarks": normalize_text(note) or _("由销售订单 {0} 的履约动作自动生成。").format(doc.name),
        "items": items,
    }
    return _filter_doc_payload("Delivery Note", payload, items=items)


def _build_delivery_note_item_payload(doc, row, *, default_warehouse: str) -> dict[str, object]:
    warehouse = _resolve_row_warehouse(doc, row, action_label="发货", fallback_warehouse=default_warehouse)
    pending_qty = _get_pending_qty(row)
    if pending_qty <= 0:
        frappe.throw(_("销售订单明细 {0} 没有可发货数量。").format(
            frappe.bold(normalize_text(getattr(row, "item_code", None)) or normalize_text(getattr(row, "name", None))),
        ))

    payload = {
        "doctype": "Delivery Note Item",
        "against_sales_order": doc.name,
        "so_detail": normalize_text(getattr(row, "name", None)),
        "item_code": normalize_text(getattr(row, "item_code", None)),
        "qty": pending_qty,
        "rate": flt(getattr(row, "rate", 0)),
        "warehouse": warehouse,
        "description": normalize_text(getattr(row, "description", None)),
        "uom": normalize_text(getattr(row, "uom", None)),
    }
    return _filter_doc_payload("Delivery Note Item", payload)


def _get_actionable_rows(doc, *, item_name_set: set[str], allowed_statuses: set[str]):
    rows = []
    for row in list(getattr(doc, "items", None) or []):
        row_name = normalize_text(getattr(row, "name", None))
        if item_name_set and row_name not in item_name_set:
            continue

        current_status = normalize_text(getattr(row, "fulfillment_status", None))
        if current_status not in allowed_statuses:
            continue
        if _get_pending_qty(row) <= 0:
            continue
        rows.append(row)
    return rows


def _resolve_row_warehouse(doc, row, *, action_label: str, fallback_warehouse: str = "") -> str:
    warehouse = (
        normalize_text(getattr(row, "warehouse", None))
        or normalize_text(fallback_warehouse)
        or normalize_text(getattr(doc, "set_warehouse", None))
    )
    if not warehouse:
        frappe.throw(
            _("销售订单 {0} 的明细 {1} 缺少仓库，不能执行{2}。").format(
                frappe.bold(doc.name),
                frappe.bold(normalize_text(getattr(row, "item_code", None)) or normalize_text(getattr(row, "name", None))),
                frappe.bold(action_label),
            )
        )
    ensure_link_exists("Warehouse", warehouse)
    return warehouse


def _ensure_sales_order_actionable(doc, *, action_label: str) -> None:
    if _is_sales_order_cancelled(doc):
        frappe.throw(_("已取消的销售订单不能执行{0}。").format(frappe.bold(action_label)))
    if normalize_text(getattr(doc, "fulfillment_status", None)) in ("已完成", "已关闭"):
        frappe.throw(_("已完成或已关闭的销售订单不能执行{0}。").format(frappe.bold(action_label)))


def _get_sales_order_doc(order_name: str):
    order_name = normalize_text(order_name)
    if not order_name:
        frappe.throw(_("销售订单不能为空。"))
    return frappe.get_doc("Sales Order", order_name)


def _normalize_item_name_set(item_names: list[str] | str | None) -> set[str]:
    if item_names in (None, "", []):
        return set()
    if isinstance(item_names, (list, tuple, set)):
        return {normalize_text(value) for value in item_names if normalize_text(value)}

    normalized = normalize_text(item_names)
    if not normalized:
        return set()
    if normalized.startswith("["):
        try:
            values = json.loads(normalized)
        except json.JSONDecodeError:
            values = []
        return {normalize_text(value) for value in values if normalize_text(value)}
    if "," in normalized:
        return {normalize_text(value) for value in normalized.split(",") if normalize_text(value)}
    return {normalized}


def _get_pending_qty(row) -> float:
    qty = max(flt(getattr(row, "qty", 0)), 0)
    delivered_qty = max(flt(getattr(row, "delivered_qty", 0)), 0)
    return max(round(qty - min(delivered_qty, qty), 6), 0)


def _get_sales_order_item_fulfillment_status(doc, row, *, after_sales_context: dict[str, object] | None = None) -> str:
    current_status = normalize_text(getattr(row, "fulfillment_status", None))
    if _is_sales_order_cancelled(doc) or current_status == "已取消":
        return "已取消"

    qty = max(flt(getattr(row, "qty", 0)), 0)
    delivered_qty = max(flt(getattr(row, "delivered_qty", 0)), 0)
    if qty > 0:
        delivered_qty = min(delivered_qty, qty)

    if qty > 0 and delivered_qty >= qty:
        if current_status in ("已签收", "已关闭"):
            base_status = current_status
        else:
            base_status = "已发货"
    elif delivered_qty > 0:
        base_status = "部分发货"
    elif current_status in MANUAL_ITEM_FULFILLMENT_STATUSES:
        base_status = current_status
    else:
        base_status = "待处理"

    overlay_status = ""
    if after_sales_context:
        item_statuses = after_sales_context.get("item_statuses") or {}
        overlay_status = normalize_text(item_statuses.get(normalize_text(getattr(row, "name", None))))
    if overlay_status:
        return overlay_status

    return base_status


def _get_sales_order_fulfillment_status(doc, *, after_sales_context: dict[str, object] | None = None) -> str:
    if _is_sales_order_cancelled(doc):
        return "已取消"
    if _is_sales_order_closed(doc):
        return "已关闭"
    if after_sales_context and after_sales_context.get("has_active_ticket"):
        return "售后中"

    item_statuses = [
        normalize_text(getattr(row, "fulfillment_status", None))
        for row in list(getattr(doc, "items", None) or [])
        if normalize_text(getattr(row, "fulfillment_status", None))
    ]
    if not item_statuses:
        return "待配货"

    active_statuses = [status for status in item_statuses if status != "已取消"]
    if not active_statuses:
        return "已取消"
    if "售后中" in active_statuses:
        return "售后中"

    status_set = set(active_statuses)
    if status_set <= {"已关闭"}:
        return "已关闭"
    if _is_sales_order_completed(doc) and status_set <= {"已发货", "已签收", "已关闭"}:
        return "已完成"
    if status_set <= {"已签收", "已关闭"}:
        return "已完成"
    if status_set <= {"已发货", "已签收", "已关闭"}:
        return "已发货"
    if "部分发货" in status_set or any(status in SHIPPED_ITEM_FULFILLMENT_STATUSES for status in active_statuses):
        return "部分发货"
    if status_set == {"待发货"}:
        return "待发货"
    if any(status in IN_PROGRESS_ITEM_FULFILLMENT_STATUSES for status in active_statuses):
        return "履约中"
    return "待配货"


def _collect_delivery_note_sales_orders(doc) -> list[str]:
    sales_orders = set()
    for row in list(getattr(doc, "items", None) or []):
        sales_order_name = normalize_text(getattr(row, "against_sales_order", None))
        if not sales_order_name:
            sales_order_name = normalize_text(getattr(row, "sales_order", None))
        if sales_order_name:
            sales_orders.add(sales_order_name)
    return sorted(sales_orders)


def _get_sales_order_after_sales_context(doc) -> dict[str, object]:
    sales_order_name = normalize_text(getattr(doc, "name", None))
    if not sales_order_name:
        return {"has_active_ticket": False, "item_statuses": {}}

    tickets = frappe.get_all(
        "After Sales Ticket",
        filters=[["After Sales Ticket", "sales_order", "=", sales_order_name]],
        fields=["name", "ticket_status"],
    )
    if not tickets:
        return {"has_active_ticket": False, "item_statuses": {}}

    item_statuses: dict[str, str] = {}
    has_active_ticket = False
    overlay_priority = {"": 0, "已关闭": 1, "售后中": 2}
    ticket_overlay_status: dict[str, str] = {}

    for ticket_row in tickets or []:
        ticket_name = normalize_text(ticket_row.get("name"))
        ticket_status = normalize_text(ticket_row.get("ticket_status"))
        overlay_status = _map_after_sales_ticket_to_item_status(ticket_status)
        if overlay_status == "售后中":
            has_active_ticket = True
        if not ticket_name or not overlay_status:
            continue
        ticket_overlay_status[ticket_name] = overlay_status

    for item_row in _get_after_sales_ticket_item_rows(ticket_overlay_status):
        ticket_name = normalize_text(item_row.get("parent"))
        sales_order_item_ref = normalize_text(item_row.get("sales_order_item_ref"))
        overlay_status = ticket_overlay_status.get(ticket_name, "")
        if not sales_order_item_ref or not overlay_status:
            continue
        current_overlay = item_statuses.get(sales_order_item_ref, "")
        if overlay_priority.get(overlay_status, 0) >= overlay_priority.get(current_overlay, 0):
            item_statuses[sales_order_item_ref] = overlay_status

    return {
        "has_active_ticket": has_active_ticket,
        "item_statuses": item_statuses,
    }


def _get_after_sales_ticket_item_rows(ticket_overlay_status: dict[str, str]) -> list[dict[str, object]]:
    ticket_names = [name for name in ticket_overlay_status if normalize_text(name)]
    if not ticket_names:
        return []

    return frappe.get_all(
        "After Sales Item",
        filters={"parent": ["in", ticket_names]},
        fields=["parent", "sales_order_item_ref"],
    )


def _map_after_sales_ticket_to_item_status(ticket_status: str) -> str:
    normalized_status = normalize_text(ticket_status)
    if normalized_status in ACTIVE_AFTER_SALES_TICKET_STATUSES:
        return "售后中"
    if normalized_status == "已关闭":
        return "已关闭"
    return ""


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


def _normalize_date(value, *, use_today: bool = False) -> str:
    if value in (None, ""):
        return nowdate() if use_today else ""
    return str(getdate(value))


def _normalize_time(value) -> str:
    if value in (None, ""):
        return now_datetime().strftime("%H:%M:%S")
    normalized = normalize_text(value)
    if normalized.count(":") in (1, 2) and "T" not in normalized and " " not in normalized and len(normalized) <= 8:
        parts = normalized.split(":")
        if len(parts) == 2:
            return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
        return ":".join(part.zfill(2) for part in parts)
    dt_value = get_datetime(value)
    return dt_value.strftime("%H:%M:%S")


def _is_sales_order_cancelled(doc) -> bool:
    if cint(getattr(doc, "docstatus", 0)) == 2:
        return True
    return normalize_text(getattr(doc, "status", None)) in CANCELLED_SALES_ORDER_STATUSES


def _is_sales_order_completed(doc) -> bool:
    return normalize_text(getattr(doc, "status", None)) in COMPLETED_SALES_ORDER_STATUSES


def _is_sales_order_closed(doc) -> bool:
    return normalize_text(getattr(doc, "status", None)) in CLOSED_SALES_ORDER_STATUSES
