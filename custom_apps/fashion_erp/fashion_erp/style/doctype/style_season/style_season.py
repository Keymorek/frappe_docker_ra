from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_int,
    normalize_business_code,
    normalize_text,
)


class StyleSeason(Document):
    def validate(self) -> None:
        self.season_name = normalize_text(self.season_name)
        self.season_code = normalize_business_code(self.season_code, "季节编码")
        self.enabled = coerce_checkbox(self.enabled)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.remark = normalize_text(self.remark)
