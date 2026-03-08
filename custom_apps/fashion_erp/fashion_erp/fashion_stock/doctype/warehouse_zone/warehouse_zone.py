import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_int,
    normalize_business_code,
    normalize_text,
)


class WarehouseZone(Document):
    def validate(self) -> None:
        self.zone_code = normalize_business_code(self.zone_code, "仓区编码")
        self.zone_name = normalize_text(self.zone_name)
        self.purpose = normalize_text(self.purpose)
        self.enabled = coerce_checkbox(self.enabled)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.remark = normalize_text(self.remark)

        if not self.zone_name:
            frappe.throw(_("仓区名称不能为空。"))
