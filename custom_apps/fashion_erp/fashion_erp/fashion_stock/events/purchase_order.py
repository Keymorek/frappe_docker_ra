from fashion_erp.fashion_stock.services.supply_service import validate_supply_purchase_order


def validate_supply_procurement(doc, _method=None) -> None:
    validate_supply_purchase_order(doc)
