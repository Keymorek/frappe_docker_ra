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
    coerce_non_negative_float,
    ensure_enabled_link,
    ensure_link_exists,
    get_product_category_size_rule,
    get_selected_style_size_codes,
    get_style_category_template_details,
    get_size_range_summary,
    normalize_business_code,
    normalize_select,
    normalize_text,
    style_has_generated_variants,
    sync_style_color_row,
    sync_style_size_row,
)


class Style(Document):
    def validate(self) -> None:
        self._normalize_fields()
        self._sync_product_category_fields()
        self._sync_style_sizes()
        self._validate_links()
        self._validate_size_rules()
        self._sync_style_colors()
        self._validate_style_colors()

    def _normalize_fields(self) -> None:
        self.style_code = normalize_business_code(self.style_code, "款号编码")
        self.style_name = normalize_text(self.style_name)
        self.brand = normalize_text(self.brand)
        self.product_category = normalize_text(self.product_category)
        self.category = normalize_text(self.category)
        self.sub_category = normalize_text(self.sub_category)
        self.category_level_1 = normalize_text(self.category_level_1)
        self.category_level_2 = normalize_text(self.category_level_2)
        self.category_level_3 = normalize_text(self.category_level_3)
        self.category_level_4 = normalize_text(self.category_level_4)
        self.category_full_path = normalize_text(self.category_full_path)
        self.season = SEASON_ALIASES.get(normalize_text(self.season), normalize_text(self.season))
        self.year = normalize_text(str(self.year)) if self.year not in (None, "") else ""
        self.wave = normalize_text(self.wave)
        self.gender = normalize_select(
            self.gender,
            "性别定位",
            GENDER_OPTIONS,
            default="女装",
            alias_map=GENDER_ALIASES,
        )
        self.design_owner = normalize_text(self.design_owner)
        self.size_system = normalize_text(self.size_system)
        self.size_range_summary = normalize_text(self.size_range_summary)
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
        if not self.brand:
            frappe.throw(_("品牌不能为空。"))
        ensure_link_exists("Brand", self.brand)
        ensure_enabled_link("Style Category Template", self.product_category)
        ensure_link_exists("Item Group", self.item_group)
        ensure_enabled_link("Style Season", self.season)
        ensure_enabled_link("Style Year", self.year)
        ensure_enabled_link("Size System", self.size_system)
        ensure_enabled_link("Fabric Master", self.fabric_main)
        ensure_enabled_link("Fabric Master", self.fabric_lining)
        ensure_link_exists("Item", self.item_template)

    def _sync_product_category_fields(self) -> None:
        if not self.product_category:
            self.category_level_1 = ""
            self.category_level_2 = ""
            self.category_level_3 = ""
            self.category_level_4 = ""
            self.category_full_path = ""
            self.category = ""
            self.sub_category = ""
            return

        template_row = get_style_category_template_details(self.product_category)
        self.category_level_1 = normalize_text(template_row.get("category_level_1"))
        self.category_level_2 = normalize_text(template_row.get("category_level_2"))
        self.category_level_3 = normalize_text(template_row.get("category_level_3"))
        self.category_level_4 = normalize_text(template_row.get("category_level_4"))
        self.category_full_path = normalize_text(template_row.get("full_path"))
        self.category = ""
        self.sub_category = ""

        category_rule = get_product_category_size_rule(self.product_category)
        if not self.size_system and category_rule["default_size_system"]:
            self.size_system = category_rule["default_size_system"]

    def _sync_style_sizes(self) -> None:
        if not self.size_system:
            self.size_range_summary = ""
            return

        if not self.style_sizes:
            self.size_range_summary = ""
            return

        seen_size_codes = set()
        for row in self.style_sizes:
            sync_style_size_row(row, self.size_system)
            if row.size_code in seen_size_codes:
                frappe.throw(_("本款尺码{0}不能重复。").format(frappe.bold(row.size_code)))
            seen_size_codes.add(row.size_code)

        self.size_range_summary = get_size_range_summary(
            self.size_system,
            selected_size_codes=get_selected_style_size_codes(self),
        )

    def _validate_size_rules(self) -> None:
        category_rule = get_product_category_size_rule(self.product_category)
        allowed_size_systems = category_rule["allowed_size_systems"]
        if allowed_size_systems and self.size_system not in allowed_size_systems:
            frappe.throw(
                _("商品类目{0}不允许使用尺码体系{1}。").format(
                    frappe.bold(self.product_category),
                    frappe.bold(self.size_system),
                )
            )

        if not self.style_sizes:
            frappe.throw(_("至少需要选择一条本款尺码。"))

        if not self.name or not frappe.db.exists("Style", self.name):
            return

        existing_style = frappe.get_doc("Style", self.name)
        existing_size_system = normalize_text(getattr(existing_style, "size_system", None))
        existing_size_codes = get_selected_style_size_codes(existing_style)
        current_size_codes = get_selected_style_size_codes(self)

        if not style_has_generated_variants(self.name, template_item=self.item_template):
            return

        if existing_size_system and existing_size_system != self.size_system:
            frappe.throw(_("款号已经生成 SKU，不能直接修改尺码体系。请先处理已有 SKU，再重建尺码方案。"))
        if existing_size_codes != current_size_codes:
            frappe.throw(_("款号已经生成 SKU，不能直接修改本款尺码。请先处理已有 SKU，再重建尺码方案。"))

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
