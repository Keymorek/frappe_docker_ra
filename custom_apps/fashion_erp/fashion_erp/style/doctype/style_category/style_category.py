import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_int,
    normalize_text,
)


class StyleCategory(Document):
    def validate(self) -> None:
        self.category_name = normalize_text(self.category_name)
        self.enabled = coerce_checkbox(self.enabled)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.remark = normalize_text(self.remark)

        if not self.category_name:
            frappe.throw(_("款式大类名称不能为空。"))
