from frappe.model.document import Document

from fashion_erp.style.services.style_service import sync_style_color_row


class StyleColor(Document):
    def validate(self) -> None:
        if self.color:
            sync_style_color_row(self, 0)
