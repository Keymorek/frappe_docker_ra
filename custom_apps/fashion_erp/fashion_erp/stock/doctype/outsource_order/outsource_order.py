import frappe
from frappe.model.document import Document

from fashion_erp.stock.services.outsource_service import (
    autoname_outsource_order,
    cancel_outsource_order,
    complete_outsource_order,
    start_outsource_order,
    submit_outsource_order,
    sync_outsource_order_number,
    validate_outsource_order,
)


class OutsourceOrder(Document):
    def autoname(self) -> None:
        autoname_outsource_order(self)

    def validate(self) -> None:
        validate_outsource_order(self)

    def after_insert(self) -> None:
        sync_outsource_order_number(self)

    @frappe.whitelist()
    def submit_order(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, submit_outsource_order, note=note)

    @frappe.whitelist()
    def start_order(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, start_outsource_order, note=note)

    @frappe.whitelist()
    def complete_order(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, complete_outsource_order, note=note)

    @frappe.whitelist()
    def cancel_order(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, cancel_outsource_order, note=note)


def _run_and_reload(doc: Document, action, **kwargs) -> dict[str, object]:
    payload = action(doc.name, **kwargs)
    doc.reload()
    return payload
