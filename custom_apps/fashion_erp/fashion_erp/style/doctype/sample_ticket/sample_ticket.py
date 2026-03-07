import frappe
from frappe.model.document import Document

from fashion_erp.style.services.sample_service import (
    autoname_sample_ticket,
    cancel_sample_ticket,
    confirm_sample_ticket,
    request_sample_revision,
    start_sample_ticket,
    submit_sample_ticket,
    submit_sample_ticket_for_review,
    sync_sample_ticket_number,
    validate_sample_ticket,
)


class SampleTicket(Document):
    def autoname(self) -> None:
        autoname_sample_ticket(self)

    def validate(self) -> None:
        validate_sample_ticket(self)

    def after_insert(self) -> None:
        sync_sample_ticket_number(self)

    @frappe.whitelist()
    def submit_ticket(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, submit_sample_ticket, note=note)

    @frappe.whitelist()
    def start_ticket(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, start_sample_ticket, note=note)

    @frappe.whitelist()
    def submit_for_review(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, submit_sample_ticket_for_review, note=note)

    @frappe.whitelist()
    def request_revision(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, request_sample_revision, note=note)

    @frappe.whitelist()
    def confirm_ticket(
        self,
        actual_cost: float | str | None = None,
        note: str | None = None,
    ) -> dict[str, object]:
        return _run_and_reload(
            self,
            confirm_sample_ticket,
            actual_cost=actual_cost,
            note=note,
        )

    @frappe.whitelist()
    def cancel_ticket(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, cancel_sample_ticket, note=note)


def _run_and_reload(doc: Document, action, **kwargs) -> dict[str, object]:
    payload = action(doc.name, **kwargs)
    doc.reload()
    return payload
