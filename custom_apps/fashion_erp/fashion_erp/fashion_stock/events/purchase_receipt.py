from fashion_erp.fashion_stock.services.supply_service import validate_supply_purchase_receipt


def validate_supply_receipt(doc, _method=None) -> None:
    validate_supply_purchase_receipt(doc)
