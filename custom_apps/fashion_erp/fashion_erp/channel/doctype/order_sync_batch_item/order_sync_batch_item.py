from frappe.model.document import Document


class OrderSyncBatchItem(Document):
    """Import rows are validated from the parent sync batch service."""
