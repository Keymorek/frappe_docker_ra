from fashion_erp.stock.services.stock_service import (
    prepare_return_metadata,
    validate_inventory_status_transition,
)


def validate_inventory_status_rules(doc, method=None) -> None:
    header_after_sales_ticket = getattr(doc, "after_sales_ticket", None)
    for row in getattr(doc, "items", []) or []:
        if not header_after_sales_ticket and getattr(row, "after_sales_ticket", None):
            header_after_sales_ticket = row.after_sales_ticket
            if hasattr(doc, "after_sales_ticket"):
                doc.after_sales_ticket = header_after_sales_ticket

        if header_after_sales_ticket and hasattr(row, "after_sales_ticket") and not getattr(row, "after_sales_ticket", None):
            row.after_sales_ticket = header_after_sales_ticket

        if not _row_has_inventory_status_context(row):
            continue

        prepare_return_metadata(row)
        validate_inventory_status_transition(
            getattr(row, "inventory_status_from", None),
            getattr(row, "inventory_status_to", None),
            row_label=_build_row_label(row),
        )


def _row_has_inventory_status_context(row) -> bool:
    return any(
        [
            getattr(row, "inventory_status_from", None),
            getattr(row, "inventory_status_to", None),
            getattr(row, "return_reason", None),
            getattr(row, "return_disposition", None),
        ]
    )


def _build_row_label(row) -> str:
    item_code = getattr(row, "item_code", None)
    row_index = getattr(row, "idx", None)
    if item_code and row_index:
        return f"row {row_index} ({item_code})"
    if item_code:
        return f"item {item_code}"
    if row_index:
        return f"row {row_index}"
    return "stock entry line"
