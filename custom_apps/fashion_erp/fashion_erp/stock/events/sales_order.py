import frappe


def sync_after_sales_replacement_order(doc, method=None) -> None:
    after_sales_ticket = getattr(doc, "after_sales_ticket", None)
    if not after_sales_ticket or not frappe.db.exists("After Sales Ticket", after_sales_ticket):
        return

    current_value = frappe.db.get_value(
        "After Sales Ticket",
        after_sales_ticket,
        "replacement_sales_order",
    )
    if current_value == doc.name:
        return

    ticket = frappe.get_doc("After Sales Ticket", after_sales_ticket)
    ticket.db_set("replacement_sales_order", doc.name, update_modified=False)
