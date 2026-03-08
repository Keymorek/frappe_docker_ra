import frappe
from frappe.model.document import Document

from fashion_erp.fashion_stock.services.after_sales_service import (
    approve_after_sales_refund,
    autoname_after_sales_ticket,
    cancel_after_sales_ticket,
    close_after_sales_ticket,
    create_replacement_sales_order,
    move_after_sales_ticket_to_waiting_return,
    prepare_replacement_sales_order,
    receive_after_sales_ticket,
    start_after_sales_inspection,
    sync_after_sales_ticket_number,
    apply_after_sales_decision,
    submit_after_sales_stock_entry,
    validate_after_sales_ticket,
    prepare_after_sales_stock_entry,
)


class AfterSalesTicket(Document):
    def autoname(self) -> None:
        autoname_after_sales_ticket(self)

    def validate(self) -> None:
        validate_after_sales_ticket(self)

    def after_insert(self) -> None:
        sync_after_sales_ticket_number(self)

    @frappe.whitelist()
    def move_to_waiting_return(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(
            self,
            move_after_sales_ticket_to_waiting_return,
            note=note,
        )

    @frappe.whitelist()
    def receive_ticket(
        self,
        warehouse: str | None = None,
        warehouse_location: str | None = None,
        logistics_company: str | None = None,
        tracking_no: str | None = None,
        received_at=None,
        note: str | None = None,
    ) -> dict[str, object]:
        return _run_and_reload(
            self,
            receive_after_sales_ticket,
            warehouse=warehouse,
            warehouse_location=warehouse_location,
            logistics_company=logistics_company,
            tracking_no=tracking_no,
            received_at=received_at,
            note=note,
        )

    @frappe.whitelist()
    def start_inspection(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(
            self,
            start_after_sales_inspection,
            note=note,
        )

    @frappe.whitelist()
    def apply_decision(
        self,
        return_disposition: str | None = None,
        refund_amount: float | str | None = None,
        note: str | None = None,
    ) -> dict[str, object]:
        return _run_and_reload(
            self,
            apply_after_sales_decision,
            return_disposition=return_disposition,
            refund_amount=refund_amount,
            note=note,
        )

    @frappe.whitelist()
    def approve_refund(
        self,
        refund_amount: float | str | None = None,
        note: str | None = None,
    ) -> dict[str, object]:
        return _run_and_reload(
            self,
            approve_after_sales_refund,
            refund_amount=refund_amount,
            note=note,
        )

    @frappe.whitelist()
    def prepare_replacement_order(
        self,
        company: str | None = None,
        delivery_date: str | None = None,
        set_warehouse: str | None = None,
        note: str | None = None,
    ) -> dict[str, object]:
        payload = prepare_replacement_sales_order(
            self.name,
            company=company,
            delivery_date=delivery_date,
            set_warehouse=set_warehouse,
            note=note,
        )
        self.reload()
        return payload

    @frappe.whitelist()
    def create_replacement_order(
        self,
        company: str | None = None,
        delivery_date: str | None = None,
        set_warehouse: str | None = None,
        note: str | None = None,
    ) -> dict[str, object]:
        payload = create_replacement_sales_order(
            self.name,
            company=company,
            delivery_date=delivery_date,
            set_warehouse=set_warehouse,
            note=note,
        )
        self.reload()
        return payload

    @frappe.whitelist()
    def prepare_return_stock_entry(
        self,
        entry_mode: str | None = None,
        company: str | None = None,
        purpose: str | None = None,
        source_warehouse: str | None = None,
        target_warehouse: str | None = None,
        remark: str | None = None,
    ) -> dict[str, object]:
        payload = prepare_after_sales_stock_entry(
            self.name,
            entry_mode=entry_mode,
            company=company,
            purpose=purpose,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
            remark=remark,
        )
        self.reload()
        return payload

    @frappe.whitelist()
    def submit_return_stock_entry(
        self,
        entry_mode: str | None = None,
        company: str | None = None,
        purpose: str | None = None,
        source_warehouse: str | None = None,
        target_warehouse: str | None = None,
        remark: str | None = None,
    ) -> dict[str, object]:
        payload = submit_after_sales_stock_entry(
            self.name,
            entry_mode=entry_mode,
            company=company,
            purpose=purpose,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
            remark=remark,
        )
        self.reload()
        return payload

    @frappe.whitelist()
    def close_ticket(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(
            self,
            close_after_sales_ticket,
            note=note,
        )

    @frappe.whitelist()
    def cancel_ticket(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(
            self,
            cancel_after_sales_ticket,
            note=note,
        )


def _run_and_reload(doc: Document, action, **kwargs) -> dict[str, object]:
    payload = action(doc.name, **kwargs)
    doc.reload()
    return payload
