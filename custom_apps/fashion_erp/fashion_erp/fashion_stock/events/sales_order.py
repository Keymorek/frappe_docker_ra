import frappe
from frappe import _

from fashion_erp.fashion_stock.services.after_sales_service import (
    AFTER_SALES_COMPLETED_REPLACEMENT_FULFILLMENT_STATUSES,
    AFTER_SALES_REPLACEMENT_TYPES,
    sync_after_sales_ticket_replacement_order,
)
from fashion_erp.fashion_stock.services.sales_order_fulfillment_service import (
    sync_linked_sales_orders_fulfillment_status as _sync_linked_sales_orders_fulfillment_status,
    sync_sales_order_fulfillment_status,
)
from fashion_erp.style.services.style_service import ensure_link_exists, normalize_text


def validate_sales_order_channel_context(doc, method=None) -> None:
    doc.channel_store = normalize_text(getattr(doc, "channel_store", None))
    doc.channel = normalize_text(getattr(doc, "channel", None))
    doc.external_order_id = normalize_text(getattr(doc, "external_order_id", None))
    doc.after_sales_ticket = normalize_text(getattr(doc, "after_sales_ticket", None))

    if doc.channel_store:
        ensure_link_exists("Channel Store", doc.channel_store)
        store_channel = normalize_text(frappe.db.get_value("Channel Store", doc.channel_store, "channel"))
        if store_channel and doc.channel and doc.channel != store_channel:
            frappe.throw(_("渠道店铺对应渠道为 {0}，不能手工填写为 {1}。").format(
                frappe.bold(store_channel),
                frappe.bold(doc.channel),
            ))
        if store_channel:
            doc.channel = store_channel

    if doc.external_order_id and not doc.channel_store:
        frappe.throw(_("填写外部订单号时必须先填写渠道店铺。"))

    _validate_external_order_uniqueness(doc)
    sync_sales_order_fulfillment_status(doc)


def sync_after_sales_replacement_order(doc, method=None) -> None:
    after_sales_ticket = normalize_text(getattr(doc, "after_sales_ticket", None))
    if not after_sales_ticket:
        return

    ticket_row = frappe.db.get_value(
        "After Sales Ticket",
        after_sales_ticket,
        ["replacement_sales_order", "replacement_fulfillment_status", "ticket_status", "ticket_type"],
        as_dict=True,
    ) or {}
    if not ticket_row:
        return

    next_replacement_sales_order = _get_next_replacement_sales_order_name(doc, method=method)
    next_replacement_fulfillment_status = _get_next_replacement_fulfillment_status(
        doc,
        method=method,
    )
    current_value = normalize_text(ticket_row.get("replacement_sales_order"))
    current_progress = normalize_text(ticket_row.get("replacement_fulfillment_status"))
    if (
        current_value == next_replacement_sales_order
        and current_progress == next_replacement_fulfillment_status
    ):
        return

    if _requires_full_after_sales_replacement_sync(
        ticket_row,
        next_replacement_sales_order=next_replacement_sales_order,
        next_replacement_fulfillment_status=next_replacement_fulfillment_status,
    ):
        sync_after_sales_ticket_replacement_order(
            after_sales_ticket,
            sales_order_name=normalize_text(getattr(doc, "name", None)),
            sales_order_doc=doc,
            operation=_map_sales_order_event_to_replacement_operation(method),
        )
        return

    if current_value != next_replacement_sales_order:
        frappe.db.set_value(
            "After Sales Ticket",
            after_sales_ticket,
            "replacement_sales_order",
            next_replacement_sales_order,
            update_modified=False,
        )
    if current_progress != next_replacement_fulfillment_status:
        frappe.db.set_value(
            "After Sales Ticket",
            after_sales_ticket,
            "replacement_fulfillment_status",
            next_replacement_fulfillment_status,
            update_modified=False,
        )


def sync_linked_sales_orders_fulfillment_status(doc, method=None) -> None:
    _sync_linked_sales_orders_fulfillment_status(doc)


def _validate_external_order_uniqueness(doc) -> None:
    if not doc.channel_store or not doc.external_order_id:
        return
    if doc.after_sales_ticket:
        return

    rows = frappe.get_all(
        "Sales Order",
        filters=[
            ["Sales Order", "channel_store", "=", doc.channel_store],
            ["Sales Order", "external_order_id", "=", doc.external_order_id],
            ["Sales Order", "docstatus", "<", 2],
        ],
        fields=["name", "after_sales_ticket"],
    )
    for row in rows or []:
        name = normalize_text(row.get("name"))
        if not name or name == normalize_text(getattr(doc, "name", None)):
            continue
        if normalize_text(row.get("after_sales_ticket")):
            continue
        frappe.throw(
            _("渠道店铺 {0} 下的外部订单号 {1} 已存在于销售订单 {2}。").format(
                frappe.bold(doc.channel_store),
                frappe.bold(doc.external_order_id),
                frappe.bold(name),
            )
        )


def _map_sales_order_event_to_replacement_operation(method: str | None) -> str | None:
    if method == "on_cancel":
        return "cancel"
    if method == "on_trash":
        return "trash"
    if method == "after_insert":
        return "create"
    return "update"


def _get_next_replacement_sales_order_name(doc, *, method: str | None = None) -> str:
    if method in ("on_cancel", "on_trash"):
        return ""
    if str(getattr(doc, "docstatus", 0)) == "2":
        return ""
    return normalize_text(getattr(doc, "name", None))


def _get_next_replacement_fulfillment_status(doc, *, method: str | None = None) -> str:
    if not _get_next_replacement_sales_order_name(doc, method=method):
        return ""

    fulfillment_status = normalize_text(getattr(doc, "fulfillment_status", None))
    if fulfillment_status:
        return fulfillment_status

    status = normalize_text(getattr(doc, "status", None))
    if status in ("Closed", "已关闭"):
        return "已关闭"
    if status in ("Completed", "已完成"):
        return "已完成"
    return "待配货"


def _requires_full_after_sales_replacement_sync(
    ticket_row,
    *,
    next_replacement_sales_order: str,
    next_replacement_fulfillment_status: str,
) -> bool:
    if normalize_text(ticket_row.get("ticket_type")) not in AFTER_SALES_REPLACEMENT_TYPES:
        return False

    current_ticket_status = normalize_text(ticket_row.get("ticket_status"))
    current_replacement_fulfillment_status = normalize_text(
        ticket_row.get("replacement_fulfillment_status")
    )
    if current_ticket_status == "已关闭":
        return True
    if not next_replacement_sales_order:
        return True
    if (
        next_replacement_fulfillment_status
        in AFTER_SALES_COMPLETED_REPLACEMENT_FULFILLMENT_STATUSES
    ):
        return True
    if (
        current_replacement_fulfillment_status
        in AFTER_SALES_COMPLETED_REPLACEMENT_FULFILLMENT_STATUSES
    ):
        return True
    return False
