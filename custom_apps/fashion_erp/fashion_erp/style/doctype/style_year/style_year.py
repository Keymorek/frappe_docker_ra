import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_int,
    normalize_text,
)


class StyleYear(Document):
    def validate(self) -> None:
        self.year_name = normalize_text(self.year_name)
        if not self.year_name:
            frappe.throw(_("年份不能为空。"))
        if not self.year_name.isdigit():
            frappe.throw(_("年份必须为四位数字。"))

        year_value = int(self.year_name)
        if year_value < 2000 or year_value > 2100:
            frappe.throw(_("年份必须在 2000 到 2100 之间。"))

        self.year_name = str(year_value)
        self.enabled = coerce_checkbox(self.enabled)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.remark = normalize_text(self.remark)
