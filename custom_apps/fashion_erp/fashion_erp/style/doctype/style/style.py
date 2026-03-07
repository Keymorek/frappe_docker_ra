import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    GENDER_ALIASES,
    GENDER_OPTIONS,
    LAUNCH_STATUS_ALIASES,
    LAUNCH_STATUS_OPTIONS,
    SALES_STATUS_ALIASES,
    SALES_STATUS_OPTIONS,
    SEASON_ALIASES,
    SEASON_OPTIONS,
    coerce_non_negative_float,
    coerce_non_negative_int,
    ensure_enabled_link,
    ensure_link_exists,
    get_current_year,
    normalize_business_code,
    normalize_select,
    normalize_text,
    sync_style_color_row,
)


class Style(Document):
    def validate(self) -> None:
        self._normalize_fields()
        self._validate_links()
        self._sync_style_colors()
        self._validate_style_colors()

    def _normalize_fields(self) -> None:
        self.style_code = normalize_business_code(self.style_code, "款号编码")
        self.style_name = normalize_text(self.style_name)
        self.category = normalize_text(self.category)
        self.sub_category = normalize_text(self.sub_category)
        self.season = normalize_select(
            self.season,
            "季节",
            SEASON_OPTIONS,
            alias_map=SEASON_ALIASES,
        )
        self.year = coerce_non_negative_int(self.year, "年份", get_current_year())
        if self.year < 2000 or self.year > 2100:
            frappe.throw(_("年份必须在 2000 到 2100 之间。"))

        self.wave = normalize_text(self.wave)
        self.gender = normalize_select(
            self.gender,
            "性别定位",
            GENDER_OPTIONS,
            default="女装",
            alias_map=GENDER_ALIASES,
        )
        self.design_owner = normalize_text(self.design_owner)
        self.fabric_main = normalize_text(self.fabric_main)
        self.fabric_lining = normalize_text(self.fabric_lining)
        self.target_cost = coerce_non_negative_float(self.target_cost, "目标成本")
        self.tag_price = coerce_non_negative_float(self.tag_price, "吊牌价")
        self.launch_status = normalize_select(
            self.launch_status,
            "上市状态",
            LAUNCH_STATUS_OPTIONS,
            default="草稿",
            alias_map=LAUNCH_STATUS_ALIASES,
        )
        self.sales_status = normalize_select(
            self.sales_status,
            "销售状态",
            SALES_STATUS_OPTIONS,
            default="未开售",
            alias_map=SALES_STATUS_ALIASES,
        )
        self.description = normalize_text(self.description)

    def _validate_links(self) -> None:
        ensure_link_exists("Brand", self.brand)
        ensure_enabled_link("Style Category", self.category)
        ensure_enabled_link("Style Sub Category", self.sub_category)
        ensure_link_exists("Item Group", self.item_group)
        ensure_enabled_link("Size System", self.size_system)
        ensure_link_exists("Item", self.item_template)

        if self.sub_category:
            parent_category = frappe.db.get_value(
                "Style Sub Category", self.sub_category, "category"
            )
            if parent_category != self.category:
                frappe.throw(
                    _("小类{0}不属于大类{1}。").format(
                        frappe.bold(self.sub_category), frappe.bold(self.category)
                    )
                )

    def _sync_style_colors(self) -> None:
        if not self.colors:
            frappe.throw(_("至少需要一条款式颜色明细。"))

        for index, row in enumerate(self.colors, start=1):
            default_sort_order = index * 10
            sync_style_color_row(row, default_sort_order)

    def _validate_style_colors(self) -> None:
        seen_colors = set()
        enabled_rows = 0

        for row in self.colors:
            if row.color in seen_colors:
                frappe.throw(
                    _("款式颜色{0}不能重复。").format(
                        frappe.bold(row.color)
                    )
                )
            seen_colors.add(row.color)

            if row.enabled:
                enabled_rows += 1

        if enabled_rows <= 0:
            frappe.throw(_("至少需要一条启用的款式颜色。"))
