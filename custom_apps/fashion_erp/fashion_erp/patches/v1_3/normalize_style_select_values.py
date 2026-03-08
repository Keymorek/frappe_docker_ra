import frappe

from fashion_erp.patches.v1_2.translate_select_values_to_zh import (
    STYLE_GENDER_MAP,
    STYLE_LAUNCH_STATUS_MAP,
    STYLE_SALES_STATUS_MAP,
    STYLE_SEASON_MAP,
)


STYLE_FIELD_MAPPINGS = {
    "season": STYLE_SEASON_MAP,
    "gender": STYLE_GENDER_MAP,
    "launch_status": STYLE_LAUNCH_STATUS_MAP,
    "sales_status": STYLE_SALES_STATUS_MAP,
}


def execute() -> None:
    if not frappe.db.exists("DocType", "Style"):
        return

    meta = frappe.get_meta("Style")
    for fieldname, mapping in STYLE_FIELD_MAPPINGS.items():
        if not meta.has_field(fieldname):
            continue
        _translate_style_field(fieldname, mapping)


def _translate_style_field(fieldname: str, mapping: dict[str, str]) -> None:
    for source_value, target_value in _expand_mapping(mapping).items():
        rows = frappe.get_all(
            "Style",
            filters={fieldname: source_value},
            pluck="name",
            limit_page_length=0,
        )
        for name in rows:
            frappe.db.set_value("Style", name, fieldname, target_value, update_modified=False)


def _expand_mapping(mapping: dict[str, str]) -> dict[str, str]:
    expanded: dict[str, str] = {}
    for source_value, target_value in mapping.items():
        for variant in {
            source_value,
            source_value.lower(),
            source_value.upper(),
            source_value.title(),
        }:
            expanded[variant] = target_value
    return expanded
