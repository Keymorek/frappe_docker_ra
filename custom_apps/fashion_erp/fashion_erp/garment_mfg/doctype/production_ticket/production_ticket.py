import frappe
from frappe.model.document import Document

from fashion_erp.garment_mfg.services.production_service import (
    add_stage_log_to_ticket,
    advance_production_ticket_stage,
    complete_production_ticket,
    hold_production_ticket,
    prepare_bom_from_ticket,
    prepare_work_order_from_ticket,
    prepare_stock_entry_from_ticket,
    resume_production_ticket,
    sync_linked_bom,
    sync_linked_work_order,
    start_production_ticket,
    validate_production_ticket,
)


class ProductionTicket(Document):
    def validate(self) -> None:
        validate_production_ticket(self)

    def on_update(self) -> None:
        if self.bom_no and not getattr(frappe.flags, "in_fashion_erp_bom_sync", False):
            sync_linked_bom(self.name)
        if self.work_order and not getattr(frappe.flags, "in_fashion_erp_work_order_sync", False):
            sync_linked_work_order(self.name)

    @frappe.whitelist()
    def start_ticket(self) -> dict[str, object]:
        return _run_and_reload(self, start_production_ticket)

    @frappe.whitelist()
    def next_stage(self) -> dict[str, object]:
        return _run_and_reload(self, advance_production_ticket_stage)

    @frappe.whitelist()
    def hold_ticket(self) -> dict[str, object]:
        return _run_and_reload(self, hold_production_ticket)

    @frappe.whitelist()
    def resume_ticket(self) -> dict[str, object]:
        return _run_and_reload(self, resume_production_ticket)

    @frappe.whitelist()
    def complete_ticket(self) -> dict[str, object]:
        return _run_and_reload(self, complete_production_ticket)

    @frappe.whitelist()
    def sync_bom(self) -> dict[str, object]:
        payload = sync_linked_bom(self.name)
        self.reload()
        return payload

    @frappe.whitelist()
    def sync_work_order(self) -> dict[str, object]:
        payload = sync_linked_work_order(self.name)
        self.reload()
        return payload

    @frappe.whitelist()
    def prepare_bom(
        self,
        company: str | None = None,
        item_code: str | None = None,
        source_bom: str | None = None,
        quantity: float | str | None = None,
        is_active: int | str | None = 1,
        is_default: int | str | None = 0,
        description: str | None = None,
    ) -> dict[str, object]:
        payload = prepare_bom_from_ticket(
            self.name,
            company=company,
            item_code=item_code,
            source_bom=source_bom,
            quantity=quantity,
            is_active=is_active,
            is_default=is_default,
            description=description,
        )
        self.reload()
        return payload

    @frappe.whitelist()
    def prepare_work_order(
        self,
        company: str | None = None,
        production_item: str | None = None,
        bom_no: str | None = None,
        qty: float | str | None = None,
        source_warehouse: str | None = None,
        wip_warehouse: str | None = None,
        fg_warehouse: str | None = None,
        description: str | None = None,
    ) -> dict[str, object]:
        payload = prepare_work_order_from_ticket(
            self.name,
            company=company,
            production_item=production_item,
            bom_no=bom_no,
            qty=qty,
            source_warehouse=source_warehouse,
            wip_warehouse=wip_warehouse,
            fg_warehouse=fg_warehouse,
            description=description,
        )
        self.reload()
        return payload

    @frappe.whitelist()
    def prepare_stock_entry(
        self,
        purpose: str | None = None,
        item_code: str | None = None,
        qty: float | str | None = None,
        source_warehouse: str | None = None,
        target_warehouse: str | None = None,
        remark: str | None = None,
    ) -> dict[str, object]:
        payload = prepare_stock_entry_from_ticket(
            self.name,
            purpose=purpose,
            item_code=item_code,
            qty=qty,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
            remark=remark,
        )
        self.reload()
        return payload

    @frappe.whitelist()
    def add_stage_log(
        self,
        stage: str | None = None,
        qty_in: int | str | None = None,
        qty_out: int | str | None = None,
        defect_qty: int | str | None = None,
        warehouse: str | None = None,
        supplier: str | None = None,
        remark: str | None = None,
    ) -> dict[str, object]:
        payload = add_stage_log_to_ticket(
            self.name,
            stage=stage,
            qty_in=qty_in,
            qty_out=qty_out,
            defect_qty=defect_qty,
            warehouse=warehouse,
            supplier=supplier,
            remark=remark,
        )
        self.reload()
        return payload


def _run_and_reload(doc: Document, action) -> dict[str, object]:
    payload = action(doc.name)
    doc.reload()
    return payload
