import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    ensure_link_exists,
    normalize_text,
)


class Color(Document):
    def validate(self) -> None:
        self.color_name = normalize_text(self.color_name)
        self.enabled = coerce_checkbox(self.enabled)
        self.remark = normalize_text(self.remark)
        ensure_link_exists("Color Group", self.color_group)

        if not self.color_name:
            frappe.throw(_("颜色名称不能为空。"))
