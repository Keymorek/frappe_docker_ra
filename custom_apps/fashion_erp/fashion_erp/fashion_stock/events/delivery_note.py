from fashion_erp.fashion_stock.services.delivery_note_fulfillment_service import (
    validate_delivery_note_fulfillment,
)
from fashion_erp.fashion_stock.services.sales_order_fulfillment_service import (
    sync_linked_sales_orders_fulfillment_status,
)


def validate_delivery_note_extensions(doc, method=None) -> None:
    validate_delivery_note_fulfillment(doc)


def sync_delivery_note_links(doc, method=None) -> None:
    sync_linked_sales_orders_fulfillment_status(doc)
