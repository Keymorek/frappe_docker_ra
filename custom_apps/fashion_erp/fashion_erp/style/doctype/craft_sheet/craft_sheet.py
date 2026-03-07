import frappe
from frappe.model.document import Document

from fashion_erp.style.services.craft_sheet_service import (
    autoname_craft_sheet,
    build_next_craft_sheet_defaults,
    publish_craft_sheet,
    sync_craft_sheet_number,
    validate_craft_sheet,
    void_craft_sheet,
)


class CraftSheet(Document):
    def autoname(self) -> None:
        autoname_craft_sheet(self)

    def validate(self) -> None:
        validate_craft_sheet(self)

    def after_insert(self) -> None:
        sync_craft_sheet_number(self)

    @frappe.whitelist()
    def publish_sheet(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, publish_craft_sheet, note=note)

    @frappe.whitelist()
    def void_sheet(self, note: str | None = None) -> dict[str, object]:
        return _run_and_reload(self, void_craft_sheet, note=note)

    @frappe.whitelist()
    def prepare_next_version(self) -> dict[str, object]:
        return build_next_craft_sheet_defaults(self.name)


def _run_and_reload(doc: Document, action, **kwargs) -> dict[str, object]:
    payload = action(doc.name, **kwargs)
    doc.reload()
    return payload
