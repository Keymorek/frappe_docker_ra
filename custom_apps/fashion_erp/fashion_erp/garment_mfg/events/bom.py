import frappe


def sync_production_ticket(doc, method=None) -> None:
    if getattr(frappe.flags, "in_fashion_erp_bom_sync", False):
        return

    ticket_name = getattr(doc, "production_ticket", None)
    if not ticket_name:
        return

    ticket_row = frappe.db.get_value(
        "Production Ticket",
        ticket_name,
        ["bom_no", "item_template"],
        as_dict=True,
    ) or {}
    if not ticket_row:
        return

    changed = bool(ticket_row.get("bom_no") != doc.name)
    if not changed and not ticket_row.get("item_template") and getattr(doc, "item", None):
        changed = True
    if not changed:
        return

    ticket = frappe.get_doc("Production Ticket", ticket_name)
    if ticket.bom_no != doc.name:
        ticket.bom_no = doc.name

    if not ticket.item_template and getattr(doc, "item", None):
        ticket.item_template = doc.item

    frappe.flags.in_fashion_erp_bom_sync = True
    try:
        ticket.save(ignore_permissions=True)
    finally:
        frappe.flags.in_fashion_erp_bom_sync = False
