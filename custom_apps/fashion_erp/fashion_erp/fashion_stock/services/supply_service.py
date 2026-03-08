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
    _reset_supply_validation_cache(doc)
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
    _reset_supply_validation_cache(doc)
    doc.supply_order_type = normalize_select(
        doc.supply_order_type,
        "采购用途",
        SUPPLY_ORDER_TYPES,
        default="原辅料采购",
    )

    supplier_role = _get_supplier_role(getattr(doc, "supplier", None), doc=doc)
    _validate_supplier_role(doc.supply_order_type, supplier_role, is_receipt=False)

    row_item_types = set()
    for row in doc.items or []:
        item_usage_type = _prepare_supply_row(
            doc,
            row,
            set_warehouse=None,
            item_label="采购明细",
        )
        if getattr(row, "reference_outsource_order", None) and not getattr(row, "supply_context", None):
            row.supply_context = "外包备货"
        row.supply_context = _normalize_supply_context(
            getattr(row, "supply_context", None),
            item_usage_type=item_usage_type,
        )
        _sync_outsource_supply_context(row, item_usage_type, item_label="采购明细")
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
    _reset_supply_validation_cache(doc)
    doc.supply_receipt_type = normalize_select(
        doc.supply_receipt_type,
        "收货用途",
        SUPPLY_RECEIPT_TYPES,
        default="原辅料收货",
    )

    supplier_role = _get_supplier_role(getattr(doc, "supplier", None), doc=doc)
    _validate_supplier_role(doc.supply_receipt_type, supplier_role, is_receipt=True)

    header_warehouse = normalize_text(getattr(doc, "set_warehouse", None))
    row_item_types = set()
    for row in doc.items or []:
        item_usage_type = _prepare_supply_row(
            doc,
            row,
            set_warehouse=header_warehouse,
            item_label="收货明细",
        )
        _hydrate_supply_row_from_purchase_order(doc, row, item_label="收货明细")
        if getattr(row, "reference_outsource_order", None) and not getattr(row, "supply_context", None):
            row.supply_context = "外包备货"
        row.supply_context = _normalize_supply_context(
            getattr(row, "supply_context", None),
            item_usage_type=item_usage_type,
        )
        _sync_outsource_supply_context(row, item_usage_type, item_label="收货明细")
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
    _ensure_cached_link_exists(doc, "Warehouse", doc.supply_warehouse)
    _ensure_cached_enabled_link(doc, "Warehouse Location", doc.default_location)

    if doc.default_location:
        location_warehouse = _get_cached_location_warehouse(doc, doc.default_location)
        if doc.supply_warehouse and location_warehouse and location_warehouse != doc.supply_warehouse:
            frappe.throw(
                _(
                    "默认库位 {0} 不属于默认供给仓库 {1}。"
                ).format(
                    frappe.bold(doc.default_location),
                    frappe.bold(doc.supply_warehouse),
                )
            )


def _prepare_supply_row(doc, row, *, set_warehouse: str | None, item_label: str) -> str:
    row.item_usage_type = normalize_text(getattr(row, "item_usage_type", None))
    row.reference_style = normalize_text(getattr(row, "reference_style", None))
    row.reference_outsource_order = normalize_text(getattr(row, "reference_outsource_order", None))
    row.reference_sample_ticket = normalize_text(getattr(row, "reference_sample_ticket", None))
    row.supply_context = normalize_text(getattr(row, "supply_context", None))
    if row.reference_outsource_order and not row.supply_context:
        row.supply_context = "外包备货"

    item_code = normalize_text(getattr(row, "item_code", None))
    if not item_code:
        return ""

    _ensure_cached_link_exists(doc, "Item", item_code)

    item_values = _get_cached_supply_item_values(doc, item_code)

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

    _ensure_cached_link_exists(doc, "Outsource Order", row.reference_outsource_order)
    _sync_reference_style_from_sample_ticket(doc, row, item_label=item_label)
    return item_usage_type


def _hydrate_supply_row_from_purchase_order(doc, row, *, item_label: str) -> None:
    source_row_name = _resolve_purchase_order_item_reference(doc, row)
    if not source_row_name:
        return

    source_row = _get_cached_purchase_order_item_values(doc, source_row_name)

    for fieldname in ("reference_style", "reference_outsource_order", "reference_sample_ticket", "supply_context"):
        current_value = normalize_text(getattr(row, fieldname, None))
        source_value = normalize_text(source_row.get(fieldname))
        if not current_value and source_value:
            setattr(row, fieldname, source_value)

    _ensure_cached_link_exists(doc, "Outsource Order", row.reference_outsource_order)
    _sync_reference_style_from_sample_ticket(doc, row, item_label=item_label)

    if row.reference_outsource_order and not row.supply_context:
        row.supply_context = "外包备货"


def _sync_reference_style_from_sample_ticket(doc, row, *, item_label: str) -> None:
    row.reference_style = normalize_text(getattr(row, "reference_style", None))
    row.reference_sample_ticket = normalize_text(getattr(row, "reference_sample_ticket", None))

    _ensure_cached_link_exists(doc, "Style", row.reference_style)
    _ensure_cached_link_exists(doc, "Sample Ticket", row.reference_sample_ticket)

    if not row.reference_sample_ticket:
        return

    sample_style = _get_cached_sample_ticket_style(doc, row.reference_sample_ticket)
    if not row.reference_style and sample_style:
        row.reference_style = sample_style
        return

    if row.reference_style and sample_style and row.reference_style != sample_style:
        frappe.throw(
            _(
                "{0}第 {1} 行的关联款号与打样单 {2} 不一致。"
            ).format(
                item_label,
                frappe.bold(row.idx),
                frappe.bold(row.reference_sample_ticket),
            )
        )


def _resolve_purchase_order_item_reference(doc, row) -> str:
    source_row_name = normalize_text(getattr(row, "purchase_order_item", None)) or normalize_text(
        getattr(row, "po_detail", None)
    )
    if source_row_name:
        _ensure_cached_link_exists(doc, "Purchase Order Item", source_row_name)
        return source_row_name

    purchase_order = normalize_text(getattr(row, "purchase_order", None))
    item_code = normalize_text(getattr(row, "item_code", None))
    if not purchase_order or not item_code:
        return ""

    _ensure_cached_link_exists(doc, "Purchase Order", purchase_order)

    filters = {"parent": purchase_order, "item_code": item_code}
    warehouse = normalize_text(getattr(row, "warehouse", None))
    if warehouse:
        filters["warehouse"] = warehouse

    matches = _get_cached_purchase_order_item_matches(doc, filters)
    return matches[0] if len(matches) == 1 else ""


def _sync_outsource_supply_context(row, item_usage_type: str, *, item_label: str) -> None:
    row.reference_outsource_order = normalize_text(getattr(row, "reference_outsource_order", None))

    if row.reference_outsource_order and row.supply_context != "外包备货":
        frappe.throw(
            _(
                "{0}第 {1} 行已关联外包单，采购场景必须使用外包备货。"
            ).format(item_label, frappe.bold(row.idx))
        )

    if row.supply_context != "外包备货":
        return

    if item_usage_type not in RAW_MATERIAL_ITEM_TYPES:
        frappe.throw(
            _(
                "{0}第 {1} 行只有面料或辅料才能使用外包备货场景。"
            ).format(item_label, frappe.bold(row.idx))
        )

    if not row.reference_outsource_order:
        frappe.throw(
            _(
                "{0}第 {1} 行选择外包备货时，必须关联外包单。"
            ).format(item_label, frappe.bold(row.idx))
        )

    order_doc = frappe.get_cached_doc("Outsource Order", row.reference_outsource_order)
    order_status = normalize_text(getattr(order_doc, "order_status", None))
    order_style = normalize_text(getattr(order_doc, "style", None))
    order_sample_ticket = normalize_text(getattr(order_doc, "sample_ticket", None))
    material_item_codes = {
        normalize_text(getattr(material_row, "item_code", None))
        for material_row in order_doc.materials or []
        if normalize_text(getattr(material_row, "item_code", None))
    }

    if order_status == "已取消":
        frappe.throw(
            _(
                "{0}第 {1} 行关联的外包单 {2} 已取消。"
            ).format(item_label, frappe.bold(row.idx), frappe.bold(row.reference_outsource_order))
        )

    if not material_item_codes:
        frappe.throw(
            _(
                "外包单 {0} 还没有供料清单，当前不能关联外包备货。"
            ).format(frappe.bold(row.reference_outsource_order))
        )

    if order_style and not row.reference_style:
        row.reference_style = order_style
    elif order_style and row.reference_style and row.reference_style != order_style:
        frappe.throw(
            _(
                "{0}第 {1} 行的关联款号与外包单 {2} 不一致。"
            ).format(item_label, frappe.bold(row.idx), frappe.bold(row.reference_outsource_order))
        )

    if order_sample_ticket and not row.reference_sample_ticket:
        row.reference_sample_ticket = order_sample_ticket
    elif order_sample_ticket and row.reference_sample_ticket and row.reference_sample_ticket != order_sample_ticket:
        frappe.throw(
            _(
                "{0}第 {1} 行的关联打样单与外包单 {2} 不一致。"
            ).format(item_label, frappe.bold(row.idx), frappe.bold(row.reference_outsource_order))
        )

    if normalize_text(getattr(row, "item_code", None)) not in material_item_codes:
        frappe.throw(
            _(
                "{0}第 {1} 行的物料不在外包单 {2} 的供料清单中。"
            ).format(item_label, frappe.bold(row.idx), frappe.bold(row.reference_outsource_order))
        )


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

    if row.reference_outsource_order and row.supply_context != "外包备货":
        frappe.throw(_("第 {0} 行已关联外包单，只能使用外包备货场景。").format(frappe.bold(row.idx)))

    if row.supply_context in ("打样采购", "外包备货") and not row.reference_style:
        frappe.throw(
            _("第 {0} 行选择 {1} 时，必须关联款号。").format(
                frappe.bold(row.idx),
                frappe.bold(row.supply_context),
            )
        )

    if row.supply_context == "外包备货" and item_usage_type not in RAW_MATERIAL_ITEM_TYPES:
        frappe.throw(
            _("第 {0} 行只有面料或辅料才能使用外包备货场景。").format(
                frappe.bold(row.idx)
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


def _reset_supply_validation_cache(doc) -> None:
    cache = {
        "link_exists": {},
        "enabled_links": {},
        "item_values": {},
        "purchase_order_item_values": {},
        "purchase_order_item_matches": {},
        "sample_ticket_styles": {},
        "supplier_roles": {},
        "location_warehouses": {},
    }
    flags = getattr(doc, "flags", None)
    if flags is not None:
        flags.supply_validation_cache = cache
        return
    doc._supply_validation_cache = cache


def _get_supply_validation_cache(doc) -> dict[str, dict[object, object]]:
    flags = getattr(doc, "flags", None)
    if flags is not None:
        cache = getattr(flags, "supply_validation_cache", None)
        if isinstance(cache, dict):
            return cache
    else:
        cache = getattr(doc, "_supply_validation_cache", None)
        if isinstance(cache, dict):
            return cache

    _reset_supply_validation_cache(doc)
    return _get_supply_validation_cache(doc)


def _ensure_cached_link_exists(doc, doctype: str, name: str | None) -> None:
    normalized_name = normalize_text(name)
    if not normalized_name:
        return

    cache = _get_supply_validation_cache(doc)["link_exists"]
    cache_key = (doctype, normalized_name)
    if cache.get(cache_key):
        return

    ensure_link_exists(doctype, normalized_name)
    cache[cache_key] = True


def _ensure_cached_enabled_link(doc, doctype: str, name: str | None, enabled_field: str = "enabled") -> None:
    normalized_name = normalize_text(name)
    if not normalized_name:
        return

    cache = _get_supply_validation_cache(doc)["enabled_links"]
    cache_key = (doctype, normalized_name, enabled_field)
    if cache.get(cache_key):
        return

    ensure_enabled_link(doctype, normalized_name, enabled_field)
    cache[cache_key] = True


def _get_cached_supply_item_values(doc, item_code: str) -> dict[str, object]:
    normalized_item_code = normalize_text(item_code)
    if not normalized_item_code:
        return {}

    cache = _get_supply_validation_cache(doc)["item_values"]
    if normalized_item_code not in cache:
        cache[normalized_item_code] = frappe.db.get_value(
            "Item",
            normalized_item_code,
            ["item_usage_type", "supply_warehouse"],
            as_dict=True,
        ) or {}
    return cache[normalized_item_code]


def _get_cached_purchase_order_item_values(doc, source_row_name: str) -> dict[str, object]:
    normalized_row_name = normalize_text(source_row_name)
    if not normalized_row_name:
        return {}

    cache = _get_supply_validation_cache(doc)["purchase_order_item_values"]
    if normalized_row_name not in cache:
        cache[normalized_row_name] = frappe.db.get_value(
            "Purchase Order Item",
            normalized_row_name,
            ["reference_style", "reference_outsource_order", "reference_sample_ticket", "supply_context"],
            as_dict=True,
        ) or {}
    return cache[normalized_row_name]


def _get_cached_purchase_order_item_matches(doc, filters: dict[str, object]) -> list[str]:
    cache_key = tuple(sorted((key, normalize_text(value)) for key, value in filters.items()))
    cache = _get_supply_validation_cache(doc)["purchase_order_item_matches"]
    if cache_key not in cache:
        cache[cache_key] = frappe.get_all(
            "Purchase Order Item",
            filters=filters,
            pluck="name",
            limit_page_length=2,
        )
    return cache[cache_key]


def _get_cached_sample_ticket_style(doc, sample_ticket_name: str | None) -> str:
    normalized_ticket = normalize_text(sample_ticket_name)
    if not normalized_ticket:
        return ""

    cache = _get_supply_validation_cache(doc)["sample_ticket_styles"]
    if normalized_ticket not in cache:
        cache[normalized_ticket] = normalize_text(
            frappe.db.get_value("Sample Ticket", normalized_ticket, "style")
        )
    return cache[normalized_ticket]


def _get_cached_location_warehouse(doc, location_name: str | None) -> str:
    normalized_location = normalize_text(location_name)
    if not normalized_location:
        return ""

    cache = _get_supply_validation_cache(doc)["location_warehouses"]
    if normalized_location not in cache:
        cache[normalized_location] = normalize_text(
            frappe.db.get_value("Warehouse Location", normalized_location, "warehouse")
        )
    return cache[normalized_location]


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


def _get_supplier_role(supplier_name: str | None, *, doc=None) -> str:
    supplier_name = normalize_text(supplier_name)
    if not supplier_name:
        return ""
    if doc is not None:
        _ensure_cached_link_exists(doc, "Supplier", supplier_name)
        cache = _get_supply_validation_cache(doc)["supplier_roles"]
        if supplier_name not in cache:
            cache[supplier_name] = normalize_select(
                frappe.db.get_value("Supplier", supplier_name, "supplier_role"),
                "供应商角色",
                SUPPLIER_ROLES,
                default="综合供应商",
            )
        return cache[supplier_name]

    ensure_link_exists("Supplier", supplier_name)
    return normalize_select(
        frappe.db.get_value("Supplier", supplier_name, "supplier_role"),
        "供应商角色",
        SUPPLIER_ROLES,
        default="综合供应商",
    )
