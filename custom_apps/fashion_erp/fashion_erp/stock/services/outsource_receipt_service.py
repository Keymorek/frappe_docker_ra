from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime, nowdate

from fashion_erp.stock.services.stock_service import validate_inventory_status_transition
from fashion_erp.stock.services.supply_service import ITEM_USAGE_TYPE_ALIASES, ITEM_USAGE_TYPES
from fashion_erp.style.services.style_service import (
    ensure_enabled_link,
    ensure_link_exists,
    normalize_select,
    normalize_text,
)


OUTSOURCE_RECEIPT_STATUSES = ("草稿", "已收货", "已入库", "已质检", "已取消")
OUTSOURCE_RECEIPT_STATUS_ALIASES = {
    "DRAFT": "草稿",
    "RECEIVED": "已收货",
    "STOCKED": "已入库",
    "QC_DONE": "已质检",
    "CANCELLED": "已取消",
}
OUTSOURCE_RECEIPT_LOG_ACTIONS = (
    "创建",
    "收货确认",
    "生成入库草稿",
    "确认已入库",
    "生成质检落账草稿",
    "确认质检完成",
    "取消",
    "状态变更",
    "备注",
)
OUTSOURCE_RECEIPT_LOG_ACTION_ALIASES = {
    "CREATE": "创建",
    "RECEIVE": "收货确认",
    "PREPARE_STOCK": "生成入库草稿",
    "CONFIRM_STOCK": "确认已入库",
    "PREPARE_FINAL_STOCK": "生成质检落账草稿",
    "CONFIRM_QC": "确认质检完成",
    "CANCEL": "取消",
    "STATUS_CHANGE": "状态变更",
    "COMMENT": "备注",
}


def autoname_outsource_receipt(doc) -> None:
    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.receipt_no = doc.name
        return

    reference_dt = _normalize_date(getattr(doc, "receipt_date", None), use_today=True)
    prefix = f"{reference_dt.strftime('%Y%m%d')}DH"
    receipt_no = _make_daily_sequence("Outsource Receipt", prefix)
    doc.name = receipt_no
    doc.receipt_no = receipt_no


def validate_outsource_receipt(doc) -> None:
    doc.receipt_no = normalize_text(doc.receipt_no)
    doc.outsource_order = normalize_text(doc.outsource_order)
    doc.supplier = normalize_text(doc.supplier)
    doc.receipt_status = normalize_select(
        doc.receipt_status,
        "单据状态",
        OUTSOURCE_RECEIPT_STATUSES,
        default="草稿",
        alias_map=OUTSOURCE_RECEIPT_STATUS_ALIASES,
    )
    doc.receipt_date = _normalize_date(doc.receipt_date, use_today=True)
    doc.company = normalize_text(doc.company) or _get_default_company()
    doc.supplier_delivery_no = normalize_text(doc.supplier_delivery_no)
    doc.warehouse = normalize_text(doc.warehouse)
    doc.warehouse_location = normalize_text(doc.warehouse_location)
    doc.style = normalize_text(doc.style)
    doc.style_name = normalize_text(doc.style_name)
    doc.item_template = normalize_text(doc.item_template)
    doc.craft_sheet = normalize_text(doc.craft_sheet)
    doc.sample_ticket = normalize_text(doc.sample_ticket)
    doc.color = normalize_text(doc.color)
    doc.color_name = normalize_text(doc.color_name)
    doc.color_code = normalize_text(doc.color_code).upper()
    doc.qc_stock_entry = normalize_text(doc.qc_stock_entry)
    doc.final_stock_entry = normalize_text(doc.final_stock_entry)
    doc.qc_completed_at = _normalize_datetime(doc.qc_completed_at)
    doc.remark = normalize_text(doc.remark)

    _sync_from_order(doc)
    _sync_location_context(doc)
    _validate_links(doc)
    _normalize_items(doc)
    _normalize_logs(doc)
    _append_system_logs(doc)

    doc.total_received_qty = round(sum(flt(row.qty) for row in (doc.items or [])), 2)

    if getattr(doc, "name", None) and not _is_unsaved_name(doc.name):
        doc.receipt_no = doc.name


def sync_outsource_receipt_number(doc) -> None:
    if doc.name and doc.receipt_no != doc.name:
        doc.db_set("receipt_no", doc.name, update_modified=False)
        doc.receipt_no = doc.name


def confirm_outsource_receipt(receipt_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_outsource_receipt_doc(receipt_name)
    _ensure_receipt_mutable(doc)
    if doc.receipt_status != "草稿":
        frappe.throw(_("只有草稿状态的到货单才能确认收货。"))
    if not doc.items:
        frappe.throw(_("确认收货前至少需要一条到货明细。"))

    previous_status = doc.receipt_status
    doc.receipt_status = "已收货"
    _append_log(
        doc,
        action_type="收货确认",
        from_status=previous_status,
        to_status=doc.receipt_status,
        note=normalize_text(note) or _("外包到货已确认收货。"),
    )
    return _save_receipt_action(doc, _("到货单已确认收货。"))


def build_outsource_receipt_stock_entry_payload(receipt_name: str) -> dict[str, object]:
    doc = _get_outsource_receipt_doc(receipt_name)
    if doc.receipt_status not in ("已收货", "已入库"):
        frappe.throw(_("只有已收货的到货单才能生成待质检入库草稿。"))

    company = normalize_text(doc.company) or _get_default_company()
    if not company:
        frappe.throw(_("生成待质检入库凭证前必须先确定公司。"))
    ensure_link_exists("Company", company)

    items = _build_qc_stock_entry_items(doc)
    if not items:
        frappe.throw(_("当前没有可用于生成入库凭证的到货明细。"))

    payload = _filter_doc_payload(
        "Stock Entry",
        {
            "doctype": "Stock Entry",
            "purpose": "Material Receipt",
            "stock_entry_type": "Material Receipt" if frappe.db.exists("Stock Entry Type", "Material Receipt") else None,
            "company": company,
            "to_warehouse": doc.warehouse,
            "outsource_order": doc.outsource_order,
            "outsource_receipt": doc.name,
            "remarks": _("由外包到货单 {0} 自动生成待质检入库草稿。").format(doc.name),
            "items": items,
        },
        items=items,
    )

    return {
        "ok": True,
        "payload": payload,
        "message": _("待质检入库凭证草稿已生成。"),
    }


def build_outsource_receipt_final_stock_entry_payload(receipt_name: str) -> dict[str, object]:
    doc = _get_outsource_receipt_doc(receipt_name)
    if doc.receipt_status not in ("已入库", "已质检"):
        frappe.throw(_("只有已入库的到货单才能生成质检落账草稿。"))

    company = normalize_text(doc.company) or _get_default_company()
    if not company:
        frappe.throw(_("生成质检落账凭证前必须先确定公司。"))
    ensure_link_exists("Company", company)

    items = _build_final_stock_entry_items(doc)
    if not items:
        frappe.throw(_("当前没有可用于生成质检落账凭证的到货明细。"))

    payload = _filter_doc_payload(
        "Stock Entry",
        {
            "doctype": "Stock Entry",
            "purpose": "Material Transfer",
            "stock_entry_type": "Material Transfer" if frappe.db.exists("Stock Entry Type", "Material Transfer") else None,
            "company": company,
            "from_warehouse": doc.warehouse,
            "to_warehouse": doc.warehouse,
            "outsource_order": doc.outsource_order,
            "outsource_receipt": doc.name,
            "remarks": _("由外包到货单 {0} 自动生成质检落账草稿。").format(doc.name),
            "items": items,
        },
        items=items,
    )

    return {
        "ok": True,
        "payload": payload,
        "message": _("质检落账凭证草稿已生成。"),
    }


def mark_outsource_receipt_stocked(
    receipt_name: str,
    *,
    stock_entry_ref: str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_outsource_receipt_doc(receipt_name)
    _ensure_receipt_mutable(doc)
    if doc.receipt_status != "已收货":
        frappe.throw(_("只有已收货的到货单才能确认已入库。"))

    stock_entry_ref = normalize_text(stock_entry_ref) or doc.qc_stock_entry
    if not stock_entry_ref:
        frappe.throw(_("确认已入库前必须先填写入库凭证。"))
    ensure_link_exists("Stock Entry", stock_entry_ref)
    doc.qc_stock_entry = stock_entry_ref

    previous_status = doc.receipt_status
    doc.receipt_status = "已入库"
    _append_log(
        doc,
        action_type="确认已入库",
        from_status=previous_status,
        to_status=doc.receipt_status,
        note=normalize_text(note) or _("到货商品已进入待质检库存。"),
    )
    return _save_receipt_action(doc, _("到货单已标记为已入库。"))


def complete_outsource_receipt_qc(
    receipt_name: str,
    *,
    final_stock_entry_ref: str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    doc = _get_outsource_receipt_doc(receipt_name)
    if doc.receipt_status == "已质检":
        return _build_receipt_response(doc, _("到货单已完成质检。"))
    if doc.receipt_status != "已入库":
        frappe.throw(_("只有已入库的到货单才能确认质检完成。"))

    final_stock_entry_ref = normalize_text(final_stock_entry_ref) or doc.final_stock_entry
    if not final_stock_entry_ref:
        frappe.throw(_("确认质检完成前必须先填写质检落账凭证。"))
    ensure_link_exists("Stock Entry", final_stock_entry_ref)

    _validate_qc_result_completion(doc)

    doc.final_stock_entry = final_stock_entry_ref
    doc.qc_completed_at = now_datetime()

    previous_status = doc.receipt_status
    doc.receipt_status = "已质检"
    _append_log(
        doc,
        action_type="确认质检完成",
        from_status=previous_status,
        to_status=doc.receipt_status,
        note=normalize_text(note) or _("外包到货已完成质检并落入最终库存状态。"),
    )
    return _save_receipt_action(doc, _("到货单已完成质检。"))


def cancel_outsource_receipt(receipt_name: str, *, note: str | None = None) -> dict[str, object]:
    doc = _get_outsource_receipt_doc(receipt_name)
    if doc.receipt_status == "已取消":
        return _build_receipt_response(doc, _("到货单已取消。"))
    if doc.receipt_status in ("已入库", "已质检"):
        frappe.throw(_("已入库或已质检的到货单不允许取消。"))

    previous_status = doc.receipt_status
    doc.receipt_status = "已取消"
    _append_log(
        doc,
        action_type="取消",
        from_status=previous_status,
        to_status=doc.receipt_status,
        note=normalize_text(note) or _("到货单已取消。"),
    )
    return _save_receipt_action(doc, _("到货单已取消。"))


def _validate_links(doc) -> None:
    if not doc.outsource_order:
        frappe.throw(_("关联外包单不能为空。"))

    ensure_link_exists("Outsource Order", doc.outsource_order)
    ensure_link_exists("Supplier", doc.supplier)
    ensure_link_exists("Company", doc.company)
    ensure_link_exists("Warehouse", doc.warehouse)
    ensure_enabled_link("Warehouse Location", doc.warehouse_location)
    ensure_link_exists("Style", doc.style)
    ensure_link_exists("Item", doc.item_template)
    ensure_link_exists("Craft Sheet", doc.craft_sheet)
    ensure_link_exists("Sample Ticket", doc.sample_ticket)
    ensure_enabled_link("Color", doc.color)
    ensure_link_exists("Stock Entry", doc.qc_stock_entry)
    ensure_link_exists("Stock Entry", doc.final_stock_entry)


def _sync_from_order(doc) -> None:
    order_row = frappe.db.get_value(
        "Outsource Order",
        doc.outsource_order,
        [
            "supplier",
            "style",
            "style_name",
            "item_template",
            "craft_sheet",
            "sample_ticket",
            "color",
            "color_name",
            "color_code",
            "receipt_warehouse",
        ],
        as_dict=True,
    ) or {}

    if order_row.get("supplier"):
        doc.supplier = normalize_text(order_row.get("supplier"))
    if order_row.get("style"):
        doc.style = normalize_text(order_row.get("style"))
    if order_row.get("style_name"):
        doc.style_name = normalize_text(order_row.get("style_name"))
    if order_row.get("item_template"):
        doc.item_template = normalize_text(order_row.get("item_template"))
    if order_row.get("craft_sheet"):
        doc.craft_sheet = normalize_text(order_row.get("craft_sheet"))
    if order_row.get("sample_ticket"):
        doc.sample_ticket = normalize_text(order_row.get("sample_ticket"))
    if order_row.get("color"):
        doc.color = normalize_text(order_row.get("color"))
    if order_row.get("color_name"):
        doc.color_name = normalize_text(order_row.get("color_name"))
    if order_row.get("color_code"):
        doc.color_code = normalize_text(order_row.get("color_code")).upper()
    if order_row.get("receipt_warehouse") and not doc.warehouse:
        doc.warehouse = normalize_text(order_row.get("receipt_warehouse"))


def _sync_location_context(doc) -> None:
    if not doc.warehouse_location:
        return

    location_warehouse = normalize_text(
        frappe.db.get_value("Warehouse Location", doc.warehouse_location, "warehouse")
    )
    if location_warehouse and not doc.warehouse:
        doc.warehouse = location_warehouse
    elif doc.warehouse and location_warehouse and doc.warehouse != location_warehouse:
        frappe.throw(
            _("暂存库位 {0} 属于仓库 {1}，而不是 {2}。").format(
                frappe.bold(doc.warehouse_location),
                frappe.bold(location_warehouse),
                frappe.bold(doc.warehouse),
            )
        )


def _normalize_items(doc) -> None:
    if not doc.items:
        return

    for row in doc.items or []:
        row.item_code = normalize_text(getattr(row, "item_code", None))
        row.item_name = normalize_text(getattr(row, "item_name", None))
        row.style = normalize_text(getattr(row, "style", None))
        row.color_code = normalize_text(getattr(row, "color_code", None)).upper()
        row.size_code = normalize_text(getattr(row, "size_code", None)).upper()
        row.qty = flt(getattr(row, "qty", None) or 0)
        row.sellable_qty = flt(getattr(row, "sellable_qty", None) or 0)
        row.repair_qty = flt(getattr(row, "repair_qty", None) or 0)
        row.defective_qty = flt(getattr(row, "defective_qty", None) or 0)
        row.frozen_qty = flt(getattr(row, "frozen_qty", None) or 0)
        row.qc_note = normalize_text(getattr(row, "qc_note", None))
        row.remark = normalize_text(getattr(row, "remark", None))

        if not row.item_code:
            frappe.throw(_("到货明细第 {0} 行缺少到货货品。").format(frappe.bold(row.idx)))
        ensure_link_exists("Item", row.item_code)

        item_row = frappe.db.get_value(
            "Item",
            row.item_code,
            ["item_name", "item_usage_type", "style", "color_code", "size_code"],
            as_dict=True,
        ) or {}
        item_usage_type = normalize_select(
            item_row.get("item_usage_type"),
            "物料用途",
            ITEM_USAGE_TYPES,
            default="成品",
            alias_map=ITEM_USAGE_TYPE_ALIASES,
        )
        if item_usage_type != "成品":
            frappe.throw(_("到货明细第 {0} 行只能录入成品货品。").format(frappe.bold(row.idx)))

        row.item_name = normalize_text(item_row.get("item_name")) or row.item_name or row.item_code
        row.style = normalize_text(item_row.get("style")) or row.style
        row.color_code = normalize_text(item_row.get("color_code") or row.color_code).upper()
        row.size_code = normalize_text(item_row.get("size_code") or row.size_code).upper()

        ensure_link_exists("Style", row.style)
        if doc.style and row.style != doc.style:
            frappe.throw(_("到货明细第 {0} 行的货品不属于当前外包单款号。").format(frappe.bold(row.idx)))
        if doc.color_code and row.color_code and row.color_code != doc.color_code:
            frappe.throw(_("到货明细第 {0} 行的颜色编码与外包单不一致。").format(frappe.bold(row.idx)))
        if row.qty <= 0:
            frappe.throw(_("到货明细第 {0} 行的到货数量必须大于 0。").format(frappe.bold(row.idx)))

        for fieldname, label in (
            ("sellable_qty", "可售数量"),
            ("repair_qty", "返修数量"),
            ("defective_qty", "次品数量"),
            ("frozen_qty", "冻结数量"),
        ):
            value = flt(getattr(row, fieldname, 0) or 0)
            if value < 0:
                frappe.throw(_("到货明细第 {0} 行的{1}不能小于 0。").format(frappe.bold(row.idx), label))

        result_qty = round(row.sellable_qty + row.repair_qty + row.defective_qty + row.frozen_qty, 2)
        if result_qty > round(row.qty, 2):
            frappe.throw(_("到货明细第 {0} 行的质检分配数量不能大于到货数量。").format(frappe.bold(row.idx)))


def _normalize_logs(doc) -> None:
    for row in doc.logs or []:
        row.action_time = _normalize_datetime(getattr(row, "action_time", None), use_now=True)
        row.action_type = normalize_select(
            getattr(row, "action_type", None),
            "操作类型",
            OUTSOURCE_RECEIPT_LOG_ACTIONS,
            default="备注",
            alias_map=OUTSOURCE_RECEIPT_LOG_ACTION_ALIASES,
        )
        row.from_status = OUTSOURCE_RECEIPT_STATUS_ALIASES.get(
            normalize_text(getattr(row, "from_status", None)),
            normalize_text(getattr(row, "from_status", None)),
        )
        row.to_status = OUTSOURCE_RECEIPT_STATUS_ALIASES.get(
            normalize_text(getattr(row, "to_status", None)),
            normalize_text(getattr(row, "to_status", None)),
        )
        row.operator = normalize_text(getattr(row, "operator", None)) or frappe.session.user
        row.note = normalize_text(getattr(row, "note", None))
        ensure_link_exists("User", row.operator)


def _append_system_logs(doc) -> None:
    if getattr(doc.flags, "skip_outsource_receipt_system_log", False):
        return

    previous_status = ""
    before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
    if before:
        previous_status = normalize_text(getattr(before, "receipt_status", None))

    if doc.is_new() and not _has_action_log(doc, "创建"):
        _append_log(
            doc,
            action_type="创建",
            to_status=doc.receipt_status,
            note=_("创建外包到货单。"),
        )
    elif previous_status and previous_status != doc.receipt_status:
        _append_log(
            doc,
            action_type="状态变更",
            from_status=previous_status,
            to_status=doc.receipt_status,
            note=_("到货单状态已更新。"),
        )


def _build_qc_stock_entry_items(doc) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for row in doc.items or []:
        validate_inventory_status_transition("", "QC_PENDING", row_label=f"到货明细第 {row.idx} 行")
        payload = _build_stock_entry_row_payload(
            doc,
            row,
            qty=row.qty,
            s_warehouse="",
            t_warehouse=doc.warehouse,
            inventory_status_from="",
            inventory_status_to="QC_PENDING",
        )
        items.append(payload)
    return items


def _build_final_stock_entry_items(doc) -> list[dict[str, object]]:
    _validate_qc_result_completion(doc)

    items: list[dict[str, object]] = []
    for row in doc.items or []:
        for target_status, qty in (
            ("SELLABLE", flt(row.sellable_qty or 0)),
            ("REPAIR", flt(row.repair_qty or 0)),
            ("DEFECTIVE", flt(row.defective_qty or 0)),
            ("FROZEN", flt(row.frozen_qty or 0)),
        ):
            qty = round(qty, 2)
            if qty <= 0:
                continue
            validate_inventory_status_transition("QC_PENDING", target_status, row_label=f"到货明细第 {row.idx} 行")
            items.append(
                _build_stock_entry_row_payload(
                    doc,
                    row,
                    qty=qty,
                    s_warehouse=doc.warehouse,
                    t_warehouse=doc.warehouse,
                    inventory_status_from="QC_PENDING",
                    inventory_status_to=target_status,
                )
            )
    return items


def _build_stock_entry_row_payload(
    doc,
    row,
    *,
    qty: float,
    s_warehouse: str,
    t_warehouse: str,
    inventory_status_from: str,
    inventory_status_to: str,
) -> dict[str, object]:
    item_row = _get_item_basic_data(row.item_code)
    return _filter_doc_payload(
        "Stock Entry Detail",
        {
            "doctype": "Stock Entry Detail",
            "item_code": row.item_code,
            "item_name": item_row.get("item_name"),
            "qty": qty,
            "transfer_qty": qty,
            "basic_qty": qty,
            "uom": item_row.get("stock_uom"),
            "stock_uom": item_row.get("stock_uom"),
            "s_warehouse": s_warehouse,
            "t_warehouse": t_warehouse,
            "style": row.style,
            "color_code": row.color_code,
            "size_code": row.size_code,
            "inventory_status_from": inventory_status_from,
            "inventory_status_to": inventory_status_to,
            "outsource_order": doc.outsource_order,
            "outsource_receipt": doc.name,
        },
    )


def _validate_qc_result_completion(doc) -> None:
    for row in doc.items or []:
        allocated_qty = round(
            flt(row.sellable_qty or 0)
            + flt(row.repair_qty or 0)
            + flt(row.defective_qty or 0)
            + flt(row.frozen_qty or 0),
            2,
        )
        row_qty = round(flt(row.qty or 0), 2)
        if allocated_qty != row_qty:
            frappe.throw(
                _(
                    "到货明细第 {0} 行的质检分配数量必须等于到货数量。当前分配 {1}，到货 {2}。"
                ).format(
                    frappe.bold(row.idx),
                    allocated_qty,
                    row_qty,
                )
            )


def _get_item_basic_data(item_code: str) -> dict[str, object]:
    return frappe.db.get_value(
        "Item",
        item_code,
        ["item_name", "stock_uom"],
        as_dict=True,
    ) or {}


def _save_receipt_action(doc, message: str) -> dict[str, object]:
    doc.flags.skip_outsource_receipt_system_log = True
    try:
        doc.save(ignore_permissions=True)
    finally:
        doc.flags.skip_outsource_receipt_system_log = False
    _sync_outsource_order_received_qty(doc.outsource_order)
    return _build_receipt_response(doc, message)


def _build_receipt_response(doc, message: str) -> dict[str, object]:
    return {
        "ok": True,
        "name": doc.name,
        "receipt_no": doc.receipt_no or doc.name,
        "receipt_status": doc.receipt_status,
        "total_received_qty": float(doc.total_received_qty or 0),
        "qc_stock_entry": doc.qc_stock_entry,
        "final_stock_entry": doc.final_stock_entry,
        "qc_completed_at": str(doc.qc_completed_at) if doc.qc_completed_at else None,
        "message": message,
    }


def _sync_outsource_order_received_qty(order_name: str) -> None:
    if not order_name or not frappe.db.exists("Outsource Order", order_name):
        return

    totals = frappe.get_all(
        "Outsource Receipt",
        filters={
            "outsource_order": order_name,
            "receipt_status": ["in", ["已收货", "已入库", "已质检"]],
        },
        fields=["total_received_qty"],
    )
    total_received_qty = round(sum(flt(row.total_received_qty) for row in totals), 2)
    frappe.db.set_value("Outsource Order", order_name, "received_qty", total_received_qty, update_modified=False)


def _filter_doc_payload(
    doctype: str,
    payload: dict[str, object],
    *,
    items: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    meta = frappe.get_meta(doctype)
    filtered = {"doctype": doctype}
    for fieldname, value in payload.items():
        if fieldname == "doctype":
            continue
        if fieldname == "items":
            if meta.has_field("items") and items is not None:
                filtered["items"] = items
            continue
        if value in (None, ""):
            continue
        if meta.has_field(fieldname):
            filtered[fieldname] = value
    return filtered


def _append_log(
    doc,
    *,
    action_type: str,
    from_status: str = "",
    to_status: str = "",
    note: str = "",
) -> None:
    doc.append(
        "logs",
        {
            "action_time": now_datetime(),
            "action_type": action_type,
            "from_status": from_status,
            "to_status": to_status,
            "operator": frappe.session.user,
            "note": note,
        },
    )


def _has_action_log(doc, action_type: str) -> bool:
    return any(normalize_text(row.action_type) == action_type for row in (doc.logs or []))


def _get_outsource_receipt_doc(receipt_name: str):
    return frappe.get_doc("Outsource Receipt", receipt_name)


def _ensure_receipt_mutable(doc) -> None:
    if doc.receipt_status == "已取消":
        frappe.throw(_("已取消的到货单不能继续操作。"))
    if doc.receipt_status == "已质检":
        frappe.throw(_("已质检的到货单不能继续操作。"))


def _get_default_company() -> str:
    defaults = [
        frappe.defaults.get_user_default("Company"),
        frappe.defaults.get_global_default("company"),
        frappe.defaults.get_global_default("Company"),
    ]
    for company in defaults:
        if company and frappe.db.exists("Company", company):
            return company
    return ""


def _normalize_date(value, *, use_today: bool = False):
    if not value:
        return getdate(nowdate()) if use_today else None
    return getdate(value)


def _normalize_datetime(value, *, use_now: bool = False):
    if not value:
        return now_datetime() if use_now else None
    return get_datetime(value)


def _make_daily_sequence(doctype: str, prefix: str, digits: int = 4) -> str:
    last_name = frappe.db.sql(
        f"""
        select name
        from `tab{doctype}`
        where name like %s
        order by name desc
        limit 1
        """,
        (f"{prefix}%",),
    )
    last_value = last_name[0][0] if last_name else ""
    suffix = normalize_text(last_value)[len(prefix):]
    last_index = int(suffix) if suffix.isdigit() else 0
    return f"{prefix}{last_index + 1:0{digits}d}"


def _is_unsaved_name(value: str) -> bool:
    normalized = normalize_text(value)
    return not normalized or normalized.startswith("New ")
