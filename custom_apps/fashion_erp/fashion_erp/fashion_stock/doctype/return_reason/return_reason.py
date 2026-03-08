import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_int,
    normalize_business_code,
    normalize_text,
)


class ReturnReason(Document):
    def validate(self) -> None:
        self.reason_code = normalize_business_code(self.reason_code, "原因编码")
        self.reason_name = normalize_text(self.reason_name)
        self.enabled = coerce_checkbox(self.enabled)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.remark = normalize_text(self.remark)

        if not self.reason_name:
            frappe.throw(_("原因名称不能为空。"))
