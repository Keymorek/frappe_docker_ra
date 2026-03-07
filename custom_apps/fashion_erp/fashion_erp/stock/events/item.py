from fashion_erp.stock.services.supply_service import validate_supply_item


def validate_supply_metadata(doc, _method=None) -> None:
    validate_supply_item(doc)
