import frappe
from frappe.model.document import Document

from fashion_erp.stock.services.outsource_receipt_service import (
    autoname_outsource_receipt,
    build_outsource_receipt_stock_entry_payload,
    cancel_outsource_receipt,
    confirm_outsource_receipt,
    mark_outsource_receipt_stocked,
    sync_outsource_receipt_number,
    validate_outsource_receipt,
)


class OutsourceReceipt(Document):
    def autoname(self) -> None:
        autoname_outsource_receipt(self)

    def validate(self) -> None:
        validate_outsource_receipt(self)

    def after_insert(self) -> None:
        sync_outsource_receipt_number(self)

    @frappe.whitelist()
    def confirm_receipt(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, confirm_outsource_receipt, note=note)

    @frappe.whitelist()
    def prepare_qc_stock_entry(self) -> dict[str, object]:
        return build_outsource_receipt_stock_entry_payload(self.name)

    @frappe.whitelist()
    def mark_stocked(
        self,
        stock_entry_ref: str | None = None,
        note: str | None = None,
    ) -> dict[str, object]:
        return _run_and_reload(
            self,
            mark_outsource_receipt_stocked,
            stock_entry_ref=stock_entry_ref,
            note=note,
        )

    @frappe.whitelist()
    def cancel_receipt(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, cancel_outsource_receipt, note=note)


def _run_and_reload(doc: Document, action, **kwargs) -> dict[str, object]:
    payload = action(doc.name, **kwargs)
    doc.reload()
    return payload
