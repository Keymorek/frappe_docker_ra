import frappe

from fashion_erp.fashion_stock.services.after_sales_service import (
    sync_after_sales_ticket_inventory_closure,
)
from fashion_erp.fashion_stock.services.stock_service import (
    prepare_return_metadata,
    validate_inventory_status_transition,
)
from fashion_erp.style.services.style_service import normalize_text


def validate_inventory_status_rules(doc, method=None) -> None:
    header_after_sales_ticket = getattr(doc, "after_sales_ticket", None)
    header_delivery_note = getattr(doc, "delivery_note", None)
    for row in getattr(doc, "items", []) or []:
        if not header_after_sales_ticket and getattr(row, "after_sales_ticket", None):
            header_after_sales_ticket = row.after_sales_ticket
            if hasattr(doc, "after_sales_ticket"):
                doc.after_sales_ticket = header_after_sales_ticket

        if header_after_sales_ticket and hasattr(row, "after_sales_ticket") and not getattr(row, "after_sales_ticket", None):
            row.after_sales_ticket = header_after_sales_ticket

        if not header_delivery_note and getattr(row, "delivery_note", None):
            header_delivery_note = row.delivery_note
            if hasattr(doc, "delivery_note"):
                doc.delivery_note = header_delivery_note

        if header_delivery_note and hasattr(row, "delivery_note") and not getattr(row, "delivery_note", None):
            row.delivery_note = header_delivery_note

        if not _row_has_inventory_status_context(row):
            continue

        prepare_return_metadata(row)
        validate_inventory_status_transition(
            getattr(row, "inventory_status_from", None),
            getattr(row, "inventory_status_to", None),
            row_label=_build_row_label(row),
        )


def _row_has_inventory_status_context(row) -> bool:
    return any(
        [
            getattr(row, "inventory_status_from", None),
            getattr(row, "inventory_status_to", None),
            getattr(row, "return_reason", None),
            getattr(row, "return_disposition", None),
        ]
    )


def _build_row_label(row) -> str:
    item_code = getattr(row, "item_code", None)
    row_index = getattr(row, "idx", None)
    if item_code and row_index:
        return f"row {row_index} ({item_code})"
    if item_code:
        return f"item {item_code}"
    if row_index:
        return f"row {row_index}"
    return "stock entry line"


def sync_linked_after_sales_ticket_inventory_closure(doc, method=None) -> None:
    ticket_names = _collect_after_sales_tickets(doc)
    existing_ticket_names = _get_existing_after_sales_tickets(ticket_names)
    operation = "cancel" if getattr(doc, "docstatus", None) == 2 or method == "on_cancel" else "submit"
    stock_entry_name = normalize_text(getattr(doc, "name", None))
    for ticket_name in ticket_names:
        if ticket_name not in existing_ticket_names:
            continue
        sync_after_sales_ticket_inventory_closure(
            ticket_name,
            stock_entry_name=stock_entry_name,
            operation=operation,
        )


def _collect_after_sales_tickets(doc) -> list[str]:
    ticket_names: set[str] = set()
    header_ticket = normalize_text(getattr(doc, "after_sales_ticket", None))
    if header_ticket:
        ticket_names.add(header_ticket)
    for row in getattr(doc, "items", []) or []:
        ticket_name = normalize_text(getattr(row, "after_sales_ticket", None))
        if ticket_name:
            ticket_names.add(ticket_name)
    return sorted(ticket_names)


def _get_existing_after_sales_tickets(ticket_names: list[str]) -> set[str]:
    if not ticket_names:
        return set()
    rows = frappe.get_all(
        "After Sales Ticket",
        filters={"name": ["in", ticket_names]},
        fields=["name"],
    )
    return {
        normalize_text(row.get("name"))
        for row in rows or []
        if normalize_text(row.get("name"))
    }
