import frappe


def sync_production_ticket(doc, method=None) -> None:
    if getattr(frappe.flags, "in_fashion_erp_work_order_sync", False):
        return

    ticket_name = getattr(doc, "production_ticket", None)
    if not ticket_name:
        return

    ticket_row = frappe.db.get_value(
        "Production Ticket",
        ticket_name,
        ["work_order", "bom_no", "item_template"],
        as_dict=True,
    ) or {}
    if not ticket_row:
        return

    changed = bool(ticket_row.get("work_order") != doc.name)
    if not changed and not ticket_row.get("bom_no") and getattr(doc, "bom_no", None):
        changed = True
    if not changed and not ticket_row.get("item_template") and getattr(doc, "production_item", None):
        changed = True
    if not changed:
        return

    ticket = frappe.get_doc("Production Ticket", ticket_name)
    if ticket.work_order != doc.name:
        ticket.work_order = doc.name

    if not ticket.bom_no and getattr(doc, "bom_no", None):
        ticket.bom_no = doc.bom_no

    if not ticket.item_template and getattr(doc, "production_item", None):
        ticket.item_template = doc.production_item

    frappe.flags.in_fashion_erp_work_order_sync = True
    try:
        ticket.save(ignore_permissions=True)
    finally:
        frappe.flags.in_fashion_erp_work_order_sync = False
