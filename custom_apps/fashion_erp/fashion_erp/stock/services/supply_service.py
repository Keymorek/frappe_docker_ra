from __future__ import annotations

import frappe
from frappe import _

from fashion_erp.style.services.style_service import (
    coerce_checkbox,
    ensure_enabled_link,
    ensure_link_exists,
    normalize_select,
    normalize_text,
)


ITEM_USAGE_TYPES = ("成品", "面料", "辅料", "包装耗材", "其他")
ITEM_USAGE_TYPE_ALIASES = {
    "FINISHED_GOODS": "成品",
    "FABRIC": "面料",
    "TRIM": "辅料",
    "PACKING": "包装耗材",
    "OTHER": "其他",
}
SUPPLY_MODES = ("不适用", "自供", "外协自供")
SUPPLY_MODE_ALIASES = {
    "NA": "不适用",
    "SELF_SUPPLIED": "自供",
    "OUTSOURCE_SELF_SUPPLIED": "外协自供",
}
SUPPLY_STATUSES = ("未启用", "备货中", "在用", "停用")
SUPPLY_STATUS_ALIASES = {
    "INACTIVE": "未启用",
    "PREPARING": "备货中",
    "ACTIVE": "在用",
    "DISABLED": "停用",
}
SUPPLIER_ROLES = ("外包工厂", "面料供应商", "辅料供应商", "包装耗材供应商", "综合供应商")
SUPPLY_ORDER_TYPES = ("原辅料采购", "包装耗材采购", "综合采购")
SUPPLY_RECEIPT_TYPES = ("原辅料收货", "包装耗材收货", "综合收货")
SUPPLY_CONTEXTS = ("常备采购", "打样采购", "外包备货", "包装履约")

RAW_MATERIAL_ITEM_TYPES = {"面料", "辅料"}
CONSUMABLE_ITEM_TYPES = {"包装耗材"}
SUPPLY_ITEM_TYPES = RAW_MATERIAL_ITEM_TYPES | CONSUMABLE_ITEM_TYPES


def validate_supply_item(doc) -> None:
    doc.item_usage_type = normalize_select(
        doc.item_usage_type,
        "物料用途",
        ITEM_USAGE_TYPES,
        default="成品",
        alias_map=ITEM_USAGE_TYPE_ALIASES,
    )
    doc.supply_mode = normalize_select(
        doc.supply_mode,
        "供给方式",
        SUPPLY_MODES,
        default="不适用",
        alias_map=SUPPLY_MODE_ALIASES,
    )
    doc.supply_status = normalize_select(
        doc.supply_status,
        "供给状态",
        SUPPLY_STATUSES,
        default="在用",
        alias_map=SUPPLY_STATUS_ALIASES,
    )
    doc.supply_warehouse = normalize_text(doc.supply_warehouse)
    doc.default_location = normalize_text(doc.default_location)

    _apply_item_supply_defaults(doc)
    _validate_item_supply_links(doc)


def validate_supply_purchase_order(doc) -> None:
    doc.supply_order_type = normalize_select(
        doc.supply_order_type,
        "采购用途",
        SUPPLY_ORDER_TYPES,
        default="原辅料采购",
    )

    supplier_role = _get_supplier_role(getattr(doc, "supplier", None))
    _validate_supplier_role(doc.supply_order_type, supplier_role, is_receipt=False)

    row_item_types = set()
    for row in doc.items or []:
        item_usage_type = _prepare_supply_row(
            row,
            set_warehouse=None,
            item_label="采购明细",
        )
        row.supply_context = _normalize_supply_context(
            getattr(row, "supply_context", None),
            item_usage_type=item_usage_type,
        )
        _validate_supply_context(row, item_usage_type)
        _validate_supply_doc_row_type(
            doc.supply_order_type,
            item_usage_type,
            row.idx,
            is_receipt=False,
        )
        row_item_types.add(item_usage_type)

    _validate_supply_doc_type_mix(
        doc.supply_order_type,
        row_item_types,
        is_receipt=False,
    )


def validate_supply_purchase_receipt(doc) -> None:
    doc.supply_receipt_type = normalize_select(
        doc.supply_receipt_type,
        "收货用途",
        SUPPLY_RECEIPT_TYPES,
        default="原辅料收货",
    )

    supplier_role = _get_supplier_role(getattr(doc, "supplier", None))
    _validate_supplier_role(doc.supply_receipt_type, supplier_role, is_receipt=True)

    header_warehouse = normalize_text(getattr(doc, "set_warehouse", None))
    row_item_types = set()
    for row in doc.items or []:
        item_usage_type = _prepare_supply_row(
            row,
            set_warehouse=header_warehouse,
            item_label="收货明细",
        )
        row.supply_context = _normalize_supply_context(
            getattr(row, "supply_context", None),
            item_usage_type=item_usage_type,
        )
        _validate_supply_context(row, item_usage_type)
        _validate_supply_doc_row_type(
            doc.supply_receipt_type,
            item_usage_type,
            row.idx,
            is_receipt=True,
        )
        if item_usage_type in SUPPLY_ITEM_TYPES and not normalize_text(getattr(row, "warehouse", None)):
            frappe.throw(
                _("收货明细第 {0} 行缺少入库仓库。").format(frappe.bold(row.idx))
            )
        row_item_types.add(item_usage_type)

    _validate_supply_doc_type_mix(
        doc.supply_receipt_type,
        row_item_types,
        is_receipt=True,
    )


def _apply_item_supply_defaults(doc) -> None:
    usage_type = doc.item_usage_type

    if usage_type == "成品":
        doc.supply_mode = "不适用"
        doc.is_fulfillment_consumable = 0
        doc.sellable = coerce_checkbox(getattr(doc, "sellable", None), default=1)
        return

    doc.sellable = 0
    doc.is_stock_item = 1

    if doc.supply_mode == "不适用":
        doc.supply_mode = "自供"

    doc.is_fulfillment_consumable = 1 if usage_type == "包装耗材" else 0


def _validate_item_supply_links(doc) -> None:
    ensure_link_exists("Warehouse", doc.supply_warehouse)
    ensure_enabled_link("Warehouse Location", doc.default_location)

    if doc.default_location:
        location_warehouse = normalize_text(
            frappe.db.get_value("Warehouse Location", doc.default_location, "warehouse")
        )
        if doc.supply_warehouse and location_warehouse and location_warehouse != doc.supply_warehouse:
            frappe.throw(
                _(
                    "默认库位 {0} 不属于默认供给仓库 {1}。"
                ).format(
                    frappe.bold(doc.default_location),
                    frappe.bold(doc.supply_warehouse),
                )
            )


def _prepare_supply_row(row, *, set_warehouse: str | None, item_label: str) -> str:
    row.item_usage_type = normalize_text(getattr(row, "item_usage_type", None))
    row.reference_style = normalize_text(getattr(row, "reference_style", None))
    row.reference_sample_ticket = normalize_text(getattr(row, "reference_sample_ticket", None))
    row.supply_context = normalize_text(getattr(row, "supply_context", None))

    item_code = normalize_text(getattr(row, "item_code", None))
    if not item_code:
        return ""

    ensure_link_exists("Item", item_code)

    item_values = frappe.db.get_value(
        "Item",
        item_code,
        ["item_usage_type", "supply_warehouse"],
        as_dict=True,
    ) or {}

    item_usage_type = normalize_select(
        item_values.get("item_usage_type"),
        "物料用途",
        ITEM_USAGE_TYPES,
        default="其他",
        alias_map=ITEM_USAGE_TYPE_ALIASES,
    )
    row.item_usage_type = item_usage_type

    supply_warehouse = normalize_text(item_values.get("supply_warehouse"))
    if hasattr(row, "warehouse"):
        current_warehouse = normalize_text(getattr(row, "warehouse", None))
        row.warehouse = current_warehouse or supply_warehouse or set_warehouse or ""

    ensure_link_exists("Style", row.reference_style)
    ensure_link_exists("Sample Ticket", row.reference_sample_ticket)

    if row.reference_sample_ticket:
        sample_style = normalize_text(
            frappe.db.get_value("Sample Ticket", row.reference_sample_ticket, "style")
        )
        if not row.reference_style and sample_style:
            row.reference_style = sample_style
        elif row.reference_style and sample_style and row.reference_style != sample_style:
            frappe.throw(
                _(
                    "{0}第 {1} 行的关联款号与打样单 {2} 不一致。"
                ).format(
                    item_label,
                    frappe.bold(row.idx),
                    frappe.bold(row.reference_sample_ticket),
                )
            )

    return item_usage_type


def _normalize_supply_context(value: str | None, *, item_usage_type: str) -> str:
    default_context = "包装履约" if item_usage_type == "包装耗材" else "常备采购"
    return normalize_select(
        value,
        "采购场景",
        SUPPLY_CONTEXTS,
        default=default_context,
    )


def _validate_supply_context(row, item_usage_type: str) -> None:
    if row.supply_context == "打样采购" and not row.reference_sample_ticket:
        frappe.throw(_("第 {0} 行选择打样采购时，必须关联打样单。").format(frappe.bold(row.idx)))

    if row.supply_context in ("打样采购", "外包备货") and not row.reference_style:
        frappe.throw(
            _("第 {0} 行选择 {1} 时，必须关联款号。").format(
                frappe.bold(row.idx),
                frappe.bold(row.supply_context),
            )
        )

    if row.supply_context == "包装履约" and item_usage_type != "包装耗材":
        frappe.throw(
            _("第 {0} 行只有包装耗材才能使用包装履约场景。").format(
                frappe.bold(row.idx)
            )
        )


def _validate_supply_doc_row_type(
    header_type: str,
    item_usage_type: str,
    row_index: int,
    *,
    is_receipt: bool,
) -> None:
    if not item_usage_type:
        return

    doc_label = "收货单" if is_receipt else "采购单"
    if item_usage_type == "成品":
        frappe.throw(
            _("{0}第 {1} 行不应录入成品，请使用原辅料或包装耗材。").format(
                doc_label,
                frappe.bold(row_index),
            )
        )

    if header_type in ("原辅料采购", "原辅料收货") and item_usage_type not in RAW_MATERIAL_ITEM_TYPES:
        frappe.throw(
            _("{0}第 {1} 行必须是面料或辅料。").format(doc_label, frappe.bold(row_index))
        )

    if header_type in ("包装耗材采购", "包装耗材收货") and item_usage_type not in CONSUMABLE_ITEM_TYPES:
        frappe.throw(
            _("{0}第 {1} 行必须是包装耗材。").format(doc_label, frappe.bold(row_index))
        )


def _validate_supply_doc_type_mix(
    header_type: str,
    row_item_types: set[str],
    *,
    is_receipt: bool,
) -> None:
    if not row_item_types:
        return

    if header_type in ("原辅料采购", "原辅料收货") and row_item_types & CONSUMABLE_ITEM_TYPES:
        label = "收货单" if is_receipt else "采购单"
        frappe.throw(_("{0}用途为原辅料时，不允许混入包装耗材。").format(label))

    if header_type in ("包装耗材采购", "包装耗材收货") and row_item_types & RAW_MATERIAL_ITEM_TYPES:
        label = "收货单" if is_receipt else "采购单"
        frappe.throw(_("{0}用途为包装耗材时，不允许混入面料或辅料。").format(label))


def _validate_supplier_role(header_type: str, supplier_role: str, *, is_receipt: bool) -> None:
    if not supplier_role:
        return

    allowed_roles = {
        "原辅料采购": {"面料供应商", "辅料供应商", "综合供应商"},
        "原辅料收货": {"面料供应商", "辅料供应商", "综合供应商"},
        "包装耗材采购": {"包装耗材供应商", "综合供应商"},
        "包装耗材收货": {"包装耗材供应商", "综合供应商"},
        "综合采购": set(SUPPLIER_ROLES),
        "综合收货": set(SUPPLIER_ROLES),
    }.get(header_type, set(SUPPLIER_ROLES))

    if supplier_role not in allowed_roles:
        label = "收货单" if is_receipt else "采购单"
        frappe.throw(
            _("{0}用途 {1} 与供应商角色 {2} 不匹配。").format(
                label,
                frappe.bold(header_type),
                frappe.bold(supplier_role),
            )
        )


def _get_supplier_role(supplier_name: str | None) -> str:
    supplier_name = normalize_text(supplier_name)
    if not supplier_name:
        return ""
    ensure_link_exists("Supplier", supplier_name)
    return normalize_select(
        frappe.db.get_value("Supplier", supplier_name, "supplier_role"),
        "供应商角色",
        SUPPLIER_ROLES,
        default="综合供应商",
    )
