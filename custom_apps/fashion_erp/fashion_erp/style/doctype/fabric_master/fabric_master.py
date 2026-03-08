import frappe
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    coerce_non_negative_float,
    coerce_non_negative_int,
    ensure_link_exists,
    normalize_business_code,
    normalize_text,
)


class FabricMaster(Document):
    def validate(self) -> None:
        self.fabric_id = normalize_business_code(self.fabric_id, "面料编号")
        self.fabric_name = normalize_text(self.fabric_name)
        self.fabric_category = normalize_text(self.fabric_category)
        self.fabric_sub_category = normalize_text(self.fabric_sub_category)
        self.main_composition = normalize_text(self.main_composition)
        self.supplier = normalize_text(self.supplier)
        self.linked_item = normalize_text(self.linked_item)
        self.supplier_name = normalize_text(self.supplier_name)
        self.supplier_code = normalize_text(self.supplier_code)

        if self.supplier:
            ensure_link_exists("Supplier", self.supplier)
            supplier_row = frappe.db.get_value(
                "Supplier",
                self.supplier,
                ["name", "supplier_name"],
                as_dict=True,
            ) or {}
            self.supplier_name = normalize_text(supplier_row.get("supplier_name")) or self.supplier
            self.supplier_code = normalize_text(supplier_row.get("name")) or self.supplier
        else:
            self.supplier_name = ""
            self.supplier_code = ""

        if self.linked_item:
            ensure_link_exists("Item", self.linked_item)

        self.weight_gsm = coerce_non_negative_float(self.weight_gsm, "克重(gsm)")
        self.thickness_grade = normalize_text(self.thickness_grade)
        self.drape = normalize_text(self.drape)
        self.firmness = normalize_text(self.firmness)
        self.elasticity = normalize_text(self.elasticity)
        self.breathability = normalize_text(self.breathability)
        self.hand_feel = normalize_text(self.hand_feel)
        self.surface_style = normalize_text(self.surface_style)
        self.texture = normalize_text(self.texture)
        self.weave_method = normalize_text(self.weave_method)
        self.dyeing_method = normalize_text(self.dyeing_method)
        self.finishing_process = normalize_text(self.finishing_process)
        self.shrinkage_rate = coerce_non_negative_float(self.shrinkage_rate, "缩水率")
        self.wrinkle_prone = coerce_checkbox(self.wrinkle_prone, default=0)
        self.printable = coerce_checkbox(self.printable, default=0)
        self.suitable_seasons = normalize_text(self.suitable_seasons)
        self.suitable_styles = normalize_text(self.suitable_styles)
        self.style_attributes = normalize_text(self.style_attributes)
        self.visual_effect = normalize_text(self.visual_effect)

        self.recommended_price_band = normalize_text(self.recommended_price_band)
        self.unit_price = coerce_non_negative_float(self.unit_price, "单价")
        self.moq = coerce_non_negative_float(self.moq, "MOQ")
        self.width_cm = coerce_non_negative_float(self.width_cm, "门幅(cm)")
        self.stock_status = normalize_text(self.stock_status)
        self.sample_lead_days = coerce_non_negative_int(self.sample_lead_days, "打样周期(天)")
        self.bulk_lead_days = coerce_non_negative_int(self.bulk_lead_days, "大货周期(天)")
        self.available_color_count = coerce_non_negative_int(
            self.available_color_count, "可选颜色数量"
        )
        self.standard_color_code = normalize_text(self.standard_color_code)
        self.customizable_colors = coerce_checkbox(self.customizable_colors, default=0)

        self.color_fastness = normalize_text(self.color_fastness)
        self.pilling_grade = normalize_text(self.pilling_grade)
        self.eco_certification = normalize_text(self.eco_certification)
        self.quality_grade = normalize_text(self.quality_grade)
        self.historical_styles = normalize_text(self.historical_styles)

        self.enabled = coerce_checkbox(self.enabled)
        self.remark = normalize_text(self.remark)
