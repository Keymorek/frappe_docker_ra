import frappe


def sync_production_ticket(doc, method=None) -> None:
    if getattr(frappe.flags, "in_fashion_erp_work_order_sync", False):
        return

    ticket_name = getattr(doc, "production_ticket", None)
    if not ticket_name or not frappe.db.exists("Production Ticket", ticket_name):
        return

    ticket = frappe.get_doc("Production Ticket", ticket_name)
    changed = False

    if ticket.work_order != doc.name:
        ticket.work_order = doc.name
        changed = True

    if not ticket.bom_no and getattr(doc, "bom_no", None):
        ticket.bom_no = doc.bom_no
        changed = True

    if not ticket.item_template and getattr(doc, "production_item", None):
        ticket.item_template = doc.production_item
        changed = True

    if changed:
        frappe.flags.in_fashion_erp_work_order_sync = True
        try:
            ticket.save(ignore_permissions=True)
        finally:
            frappe.flags.in_fashion_erp_work_order_sync = False
