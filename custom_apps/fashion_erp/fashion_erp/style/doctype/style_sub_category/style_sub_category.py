import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_int,
    ensure_enabled_link,
    normalize_text,
)


class StyleSubCategory(Document):
    def validate(self) -> None:
        self.sub_category_name = normalize_text(self.sub_category_name)
        self.category = normalize_text(self.category)
        self.enabled = coerce_checkbox(self.enabled)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.remark = normalize_text(self.remark)

        if not self.sub_category_name:
            frappe.throw(_("款式小类名称不能为空。"))

        ensure_enabled_link("Style Category", self.category)
