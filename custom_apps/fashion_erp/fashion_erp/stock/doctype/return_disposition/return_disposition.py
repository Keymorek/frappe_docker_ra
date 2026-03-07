import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_int,
    ensure_enabled_link,
    normalize_business_code,
    normalize_text,
)


class ReturnDisposition(Document):
    def validate(self) -> None:
        self.disposition_code = normalize_business_code(
            self.disposition_code, "处理结果编码"
        )
        self.disposition_name = normalize_text(self.disposition_name)
        self.target_inventory_status = normalize_text(self.target_inventory_status)
        self.return_to_sellable = coerce_checkbox(self.return_to_sellable, default=0)
        self.enabled = coerce_checkbox(self.enabled)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.remark = normalize_text(self.remark)

        if not self.disposition_name:
            frappe.throw(_("处理结果名称不能为空。"))

        ensure_enabled_link("Inventory Status", self.target_inventory_status)

        if self.return_to_sellable and self.target_inventory_status != "SELLABLE":
            frappe.throw(
                _("只有目标库存状态为 SELLABLE 时，才允许勾选“回到可售”。")
            )
