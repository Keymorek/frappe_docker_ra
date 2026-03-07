from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    normalize_business_code,
    normalize_text,
)


class SizeSystem(Document):
    def validate(self) -> None:
        self.size_system_code = normalize_business_code(self.size_system_code, "尺码体系编码")
        self.size_system_name = normalize_text(self.size_system_name)
        self.applicable_products = normalize_text(self.applicable_products)
        self.enabled = coerce_checkbox(self.enabled)
        self.remark = normalize_text(self.remark)
