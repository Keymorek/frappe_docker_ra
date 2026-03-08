import frappe

from fashion_erp.fashion_stock.services.sales_order_fulfillment_service import (
    sync_sales_order_fulfillment_status,
)
from fashion_erp.style.services.style_service import normalize_text


def sync_linked_sales_orders_after_sales_status(doc, method=None) -> None:
    sales_order_names = _collect_related_sales_orders(doc)
    existing_sales_orders = _get_existing_sales_orders(sales_order_names)
    for sales_order_name in sales_order_names:
        if sales_order_name not in existing_sales_orders:
            continue
        sales_order = frappe.get_doc("Sales Order", sales_order_name)
        if not sync_sales_order_fulfillment_status(sales_order):
            continue

        sales_order.save(ignore_permissions=True, ignore_version=True)


def _collect_related_sales_orders(doc) -> list[str]:
    sales_orders = set()

    direct_refs = [
        normalize_text(getattr(doc, "sales_order", None)),
        normalize_text(getattr(doc, "replacement_sales_order", None)),
    ]
    for sales_order_name in direct_refs:
        if sales_order_name:
            sales_orders.add(sales_order_name)

    for parent_order in _get_sales_order_item_parent_map(doc).values():
        if parent_order:
            sales_orders.add(parent_order)

    return sorted(sales_orders)


def _get_sales_order_item_parent_map(doc) -> dict[str, str]:
    item_refs: list[str] = []
    for row in list(getattr(doc, "items", None) or []):
        sales_order_item_ref = normalize_text(getattr(row, "sales_order_item_ref", None))
        if sales_order_item_ref:
            item_refs.append(sales_order_item_ref)

    if not item_refs:
        return {}

    rows = frappe.get_all(
        "Sales Order Item",
        filters={"name": ["in", sorted(set(item_refs))]},
        fields=["name", "parent"],
    )
    return {
        normalize_text(row.get("name")): normalize_text(row.get("parent"))
        for row in rows or []
        if normalize_text(row.get("name"))
    }


def _get_existing_sales_orders(sales_order_names: list[str]) -> set[str]:
    if not sales_order_names:
        return set()

    rows = frappe.get_all(
        "Sales Order",
        filters={"name": ["in", sales_order_names]},
        fields=["name"],
    )
    return {
        normalize_text(row.get("name"))
        for row in rows or []
        if normalize_text(row.get("name"))
    }
