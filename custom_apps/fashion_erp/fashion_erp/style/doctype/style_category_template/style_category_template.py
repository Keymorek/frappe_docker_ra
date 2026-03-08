import frappe
from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    build_style_category_template_details,
    coerce_checkbox,
    coerce_non_negative_int,
    normalize_size_system_rule_text,
    normalize_text,
    guess_size_system_rule_for_category,
    parse_size_system_rule_text,
    serialize_size_system_rule_text,
    ensure_enabled_link,
)


class StyleCategoryTemplate(Document):
    def validate(self) -> None:
        self._sync_fields()

    def autoname(self) -> None:
        self._sync_fields()
        self.name = self.full_path

    def _sync_fields(self) -> None:
        self.source_platform = normalize_text(self.source_platform) or "抖音"
        self.external_text = normalize_text(self.external_text)
        details = build_style_category_template_details(
            self.category_level_1,
            self.category_level_2,
            self.category_level_3,
            self.category_level_4,
        )

        self.category_level_1 = details["category_level_1"]
        self.category_level_2 = details["category_level_2"]
        self.category_level_3 = details["category_level_3"]
        self.category_level_4 = details["category_level_4"]
        self.leaf_category_name = details["leaf_category_name"]
        self.full_path = details["full_path"]
        self.level_depth = details["level_depth"]
        self.default_size_system = normalize_text(self.default_size_system)
        self.allowed_size_systems = normalize_size_system_rule_text(self.allowed_size_systems)

        allowed_size_systems = parse_size_system_rule_text(self.allowed_size_systems)
        if not allowed_size_systems:
            guessed = guess_size_system_rule_for_category(details["full_path"])
            allowed_size_systems = guessed["allowed_size_systems"]
            if not self.default_size_system:
                self.default_size_system = guessed["default_size_system"]

        if self.default_size_system:
            ensure_enabled_link("Size System", self.default_size_system)
            if self.default_size_system not in allowed_size_systems:
                allowed_size_systems.insert(0, self.default_size_system)

        unique_allowed: list[str] = []
        for size_system in allowed_size_systems:
            ensure_enabled_link("Size System", size_system)
            if size_system not in unique_allowed:
                unique_allowed.append(size_system)

        if unique_allowed and not self.default_size_system:
            self.default_size_system = unique_allowed[0]

        self.allowed_size_systems = serialize_size_system_rule_text(unique_allowed)
        self.enabled = coerce_checkbox(self.enabled)
        self.sort_order = coerce_non_negative_int(self.sort_order, "排序")
        self.remark = normalize_text(self.remark)

        if not self.full_path:
            frappe.throw(_("类目全路径不能为空。"))
