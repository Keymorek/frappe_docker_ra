import frappe
from frappe.model.document import Document

from fashion_erp.channel.services.order_sync_service import (
    autoname_order_sync_batch,
    execute_order_sync_batch,
    load_order_sync_batch_csv,
    preview_order_sync_batch,
    validate_order_sync_batch,
)


class OrderSyncBatch(Document):
    def autoname(self) -> None:
        autoname_order_sync_batch(self)

    def validate(self) -> None:
        validate_order_sync_batch(self)

    @frappe.whitelist()
    def preview_import(self) -> dict[str, object]:
        return _run_and_reload(self, preview_order_sync_batch)

    @frappe.whitelist()
    def execute_import(self) -> dict[str, object]:
        return _run_and_reload(self, execute_order_sync_batch)

    @frappe.whitelist()
    def load_csv(
        self,
        csv_content: str,
        source_file_name: str | None = None,
        replace_existing: int | str | bool | None = 1,
    ) -> dict[str, object]:
        return _run_and_reload(
            self,
            load_order_sync_batch_csv,
            csv_content=csv_content,
            source_file_name=source_file_name,
            replace_existing=replace_existing,
        )


def _run_and_reload(doc: Document, action, **kwargs) -> dict[str, object]:
    payload = action(doc.name, **kwargs)
    doc.reload()
    return payload
