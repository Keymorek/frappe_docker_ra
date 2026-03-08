import frappe


INDEX_NAME = "idx_sales_order_channel_store_external_order_id"
TARGET_FIELDS = ("channel_store", "external_order_id")


def execute() -> None:
    if not frappe.db.exists("DocType", "Sales Order"):
        return

    meta = frappe.get_meta("Sales Order")
    if not meta.has_field(TARGET_FIELDS[0]) or not meta.has_field(TARGET_FIELDS[1]):
        return

    rows = frappe.db.sql("SHOW INDEX FROM `tabSales Order`", as_dict=True)
    if _has_target_index(rows, INDEX_NAME, TARGET_FIELDS):
        return

    frappe.db.sql(
        """
        ALTER TABLE `tabSales Order`
        ADD INDEX `idx_sales_order_channel_store_external_order_id`
        (`channel_store`, `external_order_id`)
        """
    )


def _has_target_index(rows, index_name: str, fields: tuple[str, ...]) -> bool:
    grouped: dict[str, dict[int, str]] = {}
    for row in rows or []:
        key_name = str(row.get("Key_name") or "")
        seq = int(row.get("Seq_in_index") or 0)
        column_name = str(row.get("Column_name") or "")
        if not key_name or not seq or not column_name:
            continue
        grouped.setdefault(key_name, {})[seq] = column_name

    for key_name, columns in grouped.items():
        ordered = tuple(columns[index] for index in sorted(columns))
        if key_name == index_name and ordered == fields:
            return True
    return False
