app_name = "fashion_erp"
app_title = "时尚企业管理"
app_logo_url = "/assets/fashion_erp/images/fashion-erp-logo.svg"
app_home = "/desk/fashion-erp"
app_publisher = "Keymorek"
app_description = "面向女装电商与服装制造业务的行业扩展。"
app_email = ""
app_license = "Proprietary"
required_apps = ["erpnext"]
fixtures = ["Custom Field", "Client Script"]

add_to_apps_screen = [
    {
        "has_permission": "fashion_erp.utils.has_app_permission",
        "name": "fashion_erp",
        "logo": "/assets/fashion_erp/images/fashion-erp-logo.svg",
        "title": "时尚企业管理",
        "route": "/desk/fashion-erp",
    }
]

after_install = "fashion_erp.install.after_install"
after_migrate = "fashion_erp.install.after_migrate"

doc_events = {
    "BOM": {
        "on_update": "fashion_erp.garment_mfg.events.bom.sync_production_ticket",
    },
    "After Sales Ticket": {
        "on_update": "fashion_erp.fashion_stock.events.after_sales_ticket.sync_linked_sales_orders_after_sales_status",
    },
    "Delivery Note": {
        "validate": "fashion_erp.fashion_stock.events.delivery_note.validate_delivery_note_extensions",
        "on_submit": "fashion_erp.fashion_stock.events.delivery_note.sync_delivery_note_links",
        "on_cancel": "fashion_erp.fashion_stock.events.delivery_note.sync_delivery_note_links",
    },
    "Item": {
        "validate": "fashion_erp.fashion_stock.events.item.validate_supply_metadata",
    },
    "Purchase Order": {
        "validate": "fashion_erp.fashion_stock.events.purchase_order.validate_supply_procurement",
    },
    "Purchase Receipt": {
        "validate": "fashion_erp.fashion_stock.events.purchase_receipt.validate_supply_receipt",
    },
    "Sales Order": {
        "validate": "fashion_erp.fashion_stock.events.sales_order.validate_sales_order_channel_context",
        "after_insert": "fashion_erp.fashion_stock.events.sales_order.sync_after_sales_replacement_order",
        "on_update": "fashion_erp.fashion_stock.events.sales_order.sync_after_sales_replacement_order",
        "on_cancel": "fashion_erp.fashion_stock.events.sales_order.sync_after_sales_replacement_order",
        "on_trash": "fashion_erp.fashion_stock.events.sales_order.sync_after_sales_replacement_order",
    },
    "Stock Entry": {
        "validate": "fashion_erp.fashion_stock.events.stock_entry.validate_inventory_status_rules",
        "on_submit": "fashion_erp.fashion_stock.events.stock_entry.sync_linked_after_sales_ticket_inventory_closure",
        "on_cancel": "fashion_erp.fashion_stock.events.stock_entry.sync_linked_after_sales_ticket_inventory_closure",
    },
    "Work Order": {
        "on_update": "fashion_erp.garment_mfg.events.work_order.sync_production_ticket",
    }
}
