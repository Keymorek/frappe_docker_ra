app_name = "fashion_erp"
app_title = "时尚企业管理"
app_publisher = "Keymorek"
app_description = "面向女装电商与服装制造业务的行业扩展。"
app_email = ""
app_license = "Proprietary"
required_apps = ["erpnext"]
fixtures = ["Custom Field", "Client Script"]

after_install = "fashion_erp.install.after_install"
after_migrate = "fashion_erp.install.after_migrate"

doc_events = {
    "BOM": {
        "on_update": "fashion_erp.garment_mfg.events.bom.sync_production_ticket",
    },
    "Sales Order": {
        "on_update": "fashion_erp.stock.events.sales_order.sync_after_sales_replacement_order",
    },
    "Stock Entry": {
        "validate": "fashion_erp.stock.events.stock_entry.validate_inventory_status_rules",
    },
    "Work Order": {
        "on_update": "fashion_erp.garment_mfg.events.work_order.sync_production_ticket",
    }
}
