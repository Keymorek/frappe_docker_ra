import frappe


def sync_production_ticket(doc, method=None) -> None:
    if getattr(frappe.flags, "in_fashion_erp_bom_sync", False):
        return

    ticket_name = getattr(doc, "production_ticket", None)
    if not ticket_name or not frappe.db.exists("Production Ticket", ticket_name):
        return

    ticket = frappe.get_doc("Production Ticket", ticket_name)
    changed = False

    if ticket.bom_no != doc.name:
        ticket.bom_no = doc.name
        changed = True

    if not ticket.item_template and getattr(doc, "item", None):
        ticket.item_template = doc.item
        changed = True

    if changed:
        frappe.flags.in_fashion_erp_bom_sync = True
        try:
            ticket.save(ignore_permissions=True)
        finally:
            frappe.flags.in_fashion_erp_bom_sync = False
