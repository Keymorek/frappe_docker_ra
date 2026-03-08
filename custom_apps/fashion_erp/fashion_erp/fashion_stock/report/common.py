from __future__ import annotations

from frappe.utils import cint, flt

from fashion_erp.style.services.style_service import normalize_text


def normalize_report_filters(filters: dict | None) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in (filters or {}).items():
        if isinstance(value, str):
            value = normalize_text(value)
        if value not in (None, ""):
            normalized[key] = value
    return normalized


def is_checked(filters: dict[str, object], fieldname: str, default: bool = False) -> bool:
    value = filters.get(fieldname)
    if value in (None, ""):
        return default
    return bool(cint(value))


def make_summary_item(
    label: str,
    value,
    *,
    indicator: str = "Blue",
    datatype: str | None = None,
) -> dict[str, object]:
    item = {
        "label": label,
        "value": value,
        "indicator": indicator,
    }
    if datatype:
        item["datatype"] = datatype
    return item


def round_float(value, precision: int = 2) -> float:
    return round(flt(value), precision)

