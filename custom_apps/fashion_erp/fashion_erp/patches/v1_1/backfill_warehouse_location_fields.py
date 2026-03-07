import frappe

from fashion_erp.style.services.style_service import normalize_text


def execute() -> None:
    if not frappe.db.exists("DocType", "Warehouse Location"):
        return

    locations = frappe.get_all(
        "Warehouse Location",
        fields=[
            "name",
            "location_code",
            "location_name",
            "location_type",
            "priority",
            "sort_order",
        ],
        limit_page_length=0,
        order_by="creation asc",
    )

    for row in locations:
        updates = {}
        location_code = normalize_text(row.location_code) or row.name
        location_name = normalize_text(row.location_name) or location_code

        if row.location_code != location_code:
            updates["location_code"] = location_code
        if row.location_name != location_name:
            updates["location_name"] = location_name
        if normalize_text(row.location_type) not in ("PICK", "STORAGE", "BUFFER", "拣货", "存储", "缓冲"):
            updates["location_type"] = "存储"
        if row.priority in (None, ""):
            updates["priority"] = 0
        if row.sort_order in (None, ""):
            updates["sort_order"] = 0

        if updates:
            frappe.db.set_value("Warehouse Location", row.name, updates, update_modified=False)
