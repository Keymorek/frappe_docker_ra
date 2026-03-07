from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_int,
    normalize_business_code,
    normalize_text,
)


class ColorGroup(Document):
    def validate(self) -> None:
        self.color_group_code = normalize_business_code(self.color_group_code, "颜色组编码")
        self.color_group_name = normalize_text(self.color_group_name)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.enabled = coerce_checkbox(self.enabled)
        self.remark = normalize_text(self.remark)
