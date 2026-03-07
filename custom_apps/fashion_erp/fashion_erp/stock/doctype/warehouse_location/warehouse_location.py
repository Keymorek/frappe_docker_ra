import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_int,
    ensure_enabled_link,
    ensure_link_exists,
    normalize_text,
)
from fashion_erp.stock.services.stock_service import normalize_location_code, validate_location_type


class WarehouseLocation(Document):
    def validate(self) -> None:
        self.location_code = normalize_location_code(self.location_code)
        self.location_name = normalize_text(self.location_name)
        self.warehouse = normalize_text(self.warehouse)
        self.warehouse_zone = normalize_text(self.warehouse_zone)
        self.location_type = validate_location_type(self.location_type)
        self.priority = coerce_non_negative_int(self.priority, "优先级")
        self.rack_no = normalize_text(self.rack_no)
        self.level_no = normalize_text(self.level_no)
        self.bin_no = normalize_text(self.bin_no)
        self.enabled = coerce_checkbox(self.enabled)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.remark = normalize_text(self.remark)

        if not self.location_name:
            self.location_name = self.location_code

        if not self.location_name:
            frappe.throw(_("库位名称不能为空。"))

        ensure_link_exists("Warehouse", self.warehouse)
        ensure_enabled_link("Warehouse Zone", self.warehouse_zone)
