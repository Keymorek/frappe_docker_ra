import frappe

from fashion_erp.style.services.style_service import normalize_text


FALLBACK_STYLE_CATEGORY = "未分类"


def execute() -> None:
    _migrate_style_classification()
    _migrate_default_locations()


def _migrate_style_classification() -> None:
    if not frappe.db.exists("DocType", "Style"):
        return

    styles = frappe.get_all(
        "Style",
        fields=["name", "category", "sub_category"],
        limit_page_length=0,
        order_by="creation asc",
    )

    sub_category_categories: dict[str, set[str]] = {}
    normalized_rows: list[dict[str, str]] = []

    for row in styles:
        category = normalize_text(row.category)
        sub_category = normalize_text(row.sub_category)

        if sub_category and not category:
            category = FALLBACK_STYLE_CATEGORY

        if sub_category:
            sub_category_categories.setdefault(sub_category, set()).add(category)

        normalized_rows.append(
            {
                "name": row.name,
                "category": category,
                "sub_category": sub_category,
            }
        )

    sort_order = 10
    for category in sorted({row["category"] for row in normalized_rows if row["category"]}):
        _ensure_style_category(category, sort_order)
        sort_order += 10

    sub_category_sort_order = 10
    for row in normalized_rows:
        category = row["category"]
        sub_category = row["sub_category"]
        updates = {}

        if category != normalize_text(frappe.db.get_value("Style", row["name"], "category")):
            updates["category"] = category

        if sub_category:
            target_name = _get_target_sub_category_name(
                category, sub_category, sub_category_categories
            )
            _ensure_style_sub_category(target_name, category, sub_category_sort_order)
            sub_category_sort_order += 10
            if target_name != normalize_text(
                frappe.db.get_value("Style", row["name"], "sub_category")
            ):
                updates["sub_category"] = target_name
        else:
            current_sub_category = normalize_text(
                frappe.db.get_value("Style", row["name"], "sub_category")
            )
            if current_sub_category:
                updates["sub_category"] = ""

        if updates:
            frappe.db.set_value("Style", row["name"], updates, update_modified=False)


def _migrate_default_locations() -> None:
    if not frappe.db.exists("DocType", "Item"):
        return

    items = frappe.get_all(
        "Item",
        filters={"default_location": ["is", "set"]},
        fields=["name", "default_location"],
        limit_page_length=0,
        order_by="creation asc",
    )

    sort_order = 10
    for row in items:
        location_name = normalize_text(row.default_location)
        if not location_name:
            if row.default_location:
                frappe.db.set_value("Item", row.name, "default_location", "", update_modified=False)
            continue

        _ensure_warehouse_location(location_name, sort_order)
        sort_order += 10

        if location_name != row.default_location:
            frappe.db.set_value(
                "Item",
                row.name,
                "default_location",
                location_name,
                update_modified=False,
            )


def _get_target_sub_category_name(
    category: str,
    sub_category: str,
    sub_category_categories: dict[str, set[str]],
) -> str:
    categories = {value for value in sub_category_categories.get(sub_category, set()) if value}
    if len(categories) > 1 and category:
        return f"{category} / {sub_category}"
    return sub_category


def _ensure_style_category(category_name: str, sort_order: int) -> str:
    if frappe.db.exists("Style Category", category_name):
        return category_name

    doc = frappe.get_doc(
        {
            "doctype": "Style Category",
            "category_name": category_name,
            "enabled": 1,
            "sort_order": sort_order,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_style_sub_category(sub_category_name: str, category: str, sort_order: int) -> str:
    if frappe.db.exists("Style Sub Category", sub_category_name):
        existing_category = frappe.db.get_value(
            "Style Sub Category", sub_category_name, "category"
        )
        if not existing_category and category:
            frappe.db.set_value(
                "Style Sub Category",
                sub_category_name,
                "category",
                category,
                update_modified=False,
            )
        return sub_category_name

    doc = frappe.get_doc(
        {
            "doctype": "Style Sub Category",
            "sub_category_name": sub_category_name,
            "category": category or FALLBACK_STYLE_CATEGORY,
            "enabled": 1,
            "sort_order": sort_order,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_warehouse_location(location_name: str, sort_order: int) -> str:
    existing_name = frappe.db.get_value(
        "Warehouse Location",
        {"location_code": location_name},
        "name",
    )
    if existing_name:
        return existing_name

    if frappe.db.exists("Warehouse Location", location_name):
        return location_name

    doc = frappe.get_doc(
        {
            "doctype": "Warehouse Location",
            "location_code": location_name,
            "location_name": location_name,
            "location_type": "存储",
            "priority": 0,
            "enabled": 1,
            "sort_order": sort_order,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name
