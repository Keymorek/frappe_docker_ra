import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_int,
    normalize_business_code,
    normalize_text,
)


class InventoryStatus(Document):
    def validate(self) -> None:
        self.status_code = normalize_business_code(self.status_code, "状态编码")
        self.status_name = normalize_text(self.status_name)
        self.is_sellable = coerce_checkbox(self.is_sellable, default=0)
        self.enabled = coerce_checkbox(self.enabled)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.remark = normalize_text(self.remark)

        if not self.status_name:
            frappe.throw(_("状态名称不能为空。"))
