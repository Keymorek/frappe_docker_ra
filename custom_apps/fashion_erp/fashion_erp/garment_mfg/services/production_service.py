import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, nowdate

from fashion_erp.style.services.style_service import (
    coerce_non_negative_float,
    coerce_non_negative_int,
    ensure_link_exists,
    get_color_metadata,
    get_size_range_summary,
    normalize_select,
    normalize_text,
)


PRODUCTION_STAGE_OPTIONS = ("计划", "裁剪", "车缝", "后整", "包装", "完成")
PRODUCTION_STAGE_ALIASES = {
    "Planned": "计划",
    "Cutting": "裁剪",
    "Stitching": "车缝",
    "Finishing": "后整",
    "Packing": "包装",
    "Done": "完成",
}
PRODUCTION_STATUS_OPTIONS = ("草稿", "进行中", "暂停", "已完成", "已取消")
PRODUCTION_STATUS_ALIASES = {
    "Draft": "草稿",
    "In Progress": "进行中",
    "Hold": "暂停",
    "Completed": "已完成",
    "Cancelled": "已取消",
}
NEXT_STAGE_BY_STAGE = {
    "计划": "裁剪",
    "裁剪": "车缝",
    "车缝": "后整",
    "后整": "包装",
    "包装": "完成",
    "完成": "完成",
}
PRODUCTION_STAGE_INDEX = {stage: idx for idx, stage in enumerate(PRODUCTION_STAGE_OPTIONS)}
STOCK_ENTRY_PURPOSE_OPTIONS = (
    "Material Transfer",
    "Material Receipt",
    "Material Transfer for Manufacture",
)
STOCK_ENTRY_PURPOSE_ALIASES = {
    "物料转移": "Material Transfer",
    "物料入库": "Material Receipt",
    "生产领料": "Material Transfer for Manufacture",
}


def validate_production_ticket(doc) -> None:
    doc.stage = normalize_select(
        doc.stage,
        "阶段",
        PRODUCTION_STAGE_OPTIONS,
        default="计划",
        alias_map=PRODUCTION_STAGE_ALIASES,
    )
    doc.status = normalize_select(
        doc.status,
        "状态",
        PRODUCTION_STATUS_OPTIONS,
        default="草稿",
        alias_map=PRODUCTION_STATUS_ALIASES,
    )
    doc.qty = coerce_non_negative_int(doc.qty, "数量")
    doc.defect_qty = coerce_non_negative_int(doc.defect_qty, "不良数量")
    doc.remark = normalize_text(doc.remark)
    if doc.qty <= 0:
        frappe.throw(_("数量必须大于 0。"))

    ensure_link_exists("Style", doc.style)
    ensure_link_exists("Item", doc.item_template)
    ensure_link_exists("BOM", doc.bom_no)
    ensure_link_exists("Work Order", doc.work_order)
    ensure_link_exists("Supplier", doc.supplier)

    _sync_style_defaults(doc)
    _sync_ticket_color(doc)
    _sync_stage_logs(doc)
    _normalize_ticket_dates(doc)
    _align_stage_with_logs(doc)
    _validate_dates(doc)
    _validate_business_rules(doc)


def start_production_ticket(ticket_name: str) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)
    _ensure_ticket_mutable(doc)
    if doc.status == "进行中":
        frappe.throw(_("生产跟踪单已处于进行中状态。"))

    if doc.stage == "计划":
        doc.stage = "裁剪"

    doc.status = "进行中"
    doc.actual_start_date = doc.actual_start_date or nowdate()
    doc.save(ignore_permissions=True)

    return _build_ticket_response(doc, _("生产跟踪单已开始。"))


def advance_production_ticket_stage(ticket_name: str) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)
    _ensure_ticket_mutable(doc)
    _ensure_not_on_hold(doc, _("请先恢复生产跟踪单，再推进下一阶段。"))

    next_stage = NEXT_STAGE_BY_STAGE.get(doc.stage or "计划", "完成")
    if next_stage == doc.stage == "完成":
        frappe.throw(_("生产跟踪单已处于最终阶段。"))

    doc.stage = next_stage
    doc.status = "已完成" if next_stage == "完成" else "进行中"
    doc.actual_start_date = doc.actual_start_date or nowdate()
    if next_stage == "完成":
        doc.actual_end_date = doc.actual_end_date or nowdate()

    doc.save(ignore_permissions=True)
    return _build_ticket_response(
        doc,
        _("生产跟踪单已推进到阶段：{0}。").format(frappe.bold(doc.stage)),
    )


def hold_production_ticket(ticket_name: str) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)
    _ensure_ticket_mutable(doc)
    if doc.status != "进行中":
        frappe.throw(_("只有进行中的生产跟踪单才能暂停。"))

    doc.status = "暂停"
    doc.save(ignore_permissions=True)
    return _build_ticket_response(doc, _("生产跟踪单已暂停。"))


def resume_production_ticket(ticket_name: str) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)
    _ensure_ticket_mutable(doc)
    if doc.status != "暂停":
        frappe.throw(_("只有暂停中的生产跟踪单才能恢复。"))

    if doc.stage == "计划":
        doc.stage = "裁剪"

    doc.status = "进行中"
    doc.actual_start_date = doc.actual_start_date or nowdate()
    doc.save(ignore_permissions=True)
    return _build_ticket_response(doc, _("生产跟踪单已恢复。"))


def complete_production_ticket(ticket_name: str) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)
    _ensure_ticket_mutable(doc)
    _ensure_not_on_hold(doc, _("请先恢复生产跟踪单，再执行完工。"))

    doc.stage = "完成"
    doc.status = "已完成"
    doc.actual_start_date = doc.actual_start_date or nowdate()
    doc.actual_end_date = doc.actual_end_date or nowdate()
    doc.save(ignore_permissions=True)

    return _build_ticket_response(doc, _("生产跟踪单已完工。"))


def add_stage_log_to_ticket(
    ticket_name: str,
    *,
    stage: str | None = None,
    qty_in: int | str | None = None,
    qty_out: int | str | None = None,
    defect_qty: int | str | None = None,
    warehouse: str | None = None,
    supplier: str | None = None,
    remark: str | None = None,
) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)
    _ensure_ticket_mutable(doc)
    _ensure_not_on_hold(doc, _("请先恢复生产跟踪单，再新增阶段日志。"))

    log_stage = normalize_select(
        stage,
        "阶段",
        PRODUCTION_STAGE_OPTIONS,
        default=doc.stage or "计划",
        alias_map=PRODUCTION_STAGE_ALIASES,
    )

    doc.append(
        "stage_logs",
        {
            "stage": log_stage,
            "qty_in": coerce_non_negative_int(qty_in, "投入数量"),
            "qty_out": coerce_non_negative_int(qty_out, "产出数量"),
            "defect_qty": coerce_non_negative_int(defect_qty, "不良数量"),
            "warehouse": warehouse,
            "supplier": supplier or doc.supplier,
            "log_time": now_datetime(),
            "remark": normalize_text(remark),
        },
    )

    if log_stage == "完成":
        doc.stage = "完成"
        doc.status = "已完成"
        doc.actual_end_date = doc.actual_end_date or nowdate()
    else:
        doc.stage = log_stage
        doc.status = "进行中"

    doc.actual_start_date = doc.actual_start_date or nowdate()
    doc.save(ignore_permissions=True)

    return _build_ticket_response(doc, _("阶段日志已添加到生产跟踪单。"))


def sync_linked_work_order(ticket_name: str) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)
    if not doc.work_order:
        frappe.throw(_("同步前必须先选择生产工单。"))

    work_order = frappe.get_doc("Work Order", doc.work_order)
    meta = frappe.get_meta("Work Order")
    changed_fields = []

    custom_values = {
        "style": doc.style,
        "production_ticket": doc.name,
        "color_code": doc.color_code,
        "size_range": _build_ticket_size_range(doc),
    }

    for fieldname, value in custom_values.items():
        if not meta.has_field(fieldname):
            continue
        if work_order.get(fieldname) != value:
            work_order.set(fieldname, value)
            changed_fields.append(fieldname)

    standard_fill_values = {
        "bom_no": doc.bom_no,
        "production_item": doc.item_template,
        "qty": doc.qty,
    }

    for fieldname, value in standard_fill_values.items():
        if not value or not meta.has_field(fieldname):
            continue
        current_value = work_order.get(fieldname)
        if current_value in (None, "", 0):
            work_order.set(fieldname, value)
            changed_fields.append(fieldname)

    if changed_fields:
        work_order.save(ignore_permissions=True)

    return {
        "ok": True,
        "work_order": work_order.name,
        "changed_fields": changed_fields,
        "message": _("已根据生产跟踪单同步生产工单。"),
    }


def sync_linked_bom(ticket_name: str) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)
    if not doc.bom_no:
        frappe.throw(_("同步前必须先选择物料清单。"))

    bom = frappe.get_doc("BOM", doc.bom_no)
    meta = frappe.get_meta("BOM")
    changed_fields = []

    custom_values = {
        "style": doc.style,
        "production_ticket": doc.name,
        "color_code": doc.color_code,
    }
    for fieldname, value in custom_values.items():
        if not meta.has_field(fieldname):
            continue
        if bom.get(fieldname) != value:
            bom.set(fieldname, value)
            changed_fields.append(fieldname)

    standard_fill_values = {
        "item": doc.item_template,
        "quantity": 1,
    }
    for fieldname, value in standard_fill_values.items():
        if value in (None, "") or not meta.has_field(fieldname):
            continue
        if bom.get(fieldname) in (None, "", 0):
            bom.set(fieldname, value)
            changed_fields.append(fieldname)

    if meta.has_field("company"):
        company = _get_ticket_company(doc)
        if company and not bom.get("company"):
            bom.set("company", company)
            changed_fields.append("company")

    if changed_fields:
        bom.save(ignore_permissions=True)

    return {
        "ok": True,
        "bom_no": bom.name,
        "changed_fields": changed_fields,
        "message": _("已根据生产跟踪单同步物料清单。"),
    }


def prepare_bom_from_ticket(
    ticket_name: str,
    *,
    company: str | None = None,
    item_code: str | None = None,
    source_bom: str | None = None,
    quantity: float | str | None = None,
    is_active: int | str | None = 1,
    is_default: int | str | None = 0,
    description: str | None = None,
) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)

    item_code = normalize_text(item_code) or doc.item_template
    if not item_code:
        frappe.throw(_("准备物料清单前必须先指定物料编码。"))
    ensure_link_exists("Item", item_code)

    prepared_quantity = coerce_non_negative_float(quantity, "物料清单数量", default=1)
    if prepared_quantity <= 0:
        frappe.throw(_("物料清单数量必须大于 0。"))

    source_bom = _resolve_source_bom(
        normalize_text(source_bom),
        item_code=item_code,
    )

    payload = _build_bom_payload(
        doc,
        company=normalize_text(company) or _get_ticket_company(doc),
        item_code=item_code,
        source_bom=source_bom,
        quantity=prepared_quantity,
        is_active=1 if cint(is_active) else 0,
        is_default=1 if cint(is_default) else 0,
        description=normalize_text(description),
    )
    return {
        "ok": True,
        "payload": payload,
        "source_bom": source_bom,
        "message": _("已根据生产跟踪单生成物料清单草稿。"),
    }


def prepare_work_order_from_ticket(
    ticket_name: str,
    *,
    company: str | None = None,
    production_item: str | None = None,
    bom_no: str | None = None,
    qty: float | str | None = None,
    source_warehouse: str | None = None,
    wip_warehouse: str | None = None,
    fg_warehouse: str | None = None,
    description: str | None = None,
) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)

    company = normalize_text(company) or _get_ticket_company(doc)
    if not company or not frappe.db.exists("Company", company):
        frappe.throw(_("准备生产工单前必须先确定公司。"))

    production_item = normalize_text(production_item) or doc.item_template
    if not production_item:
        frappe.throw(_("准备生产工单前必须先指定生产物料。"))
    ensure_link_exists("Item", production_item)

    bom_no = normalize_text(bom_no) or doc.bom_no
    if not bom_no:
        frappe.throw(_("准备生产工单前必须先指定物料清单。"))
    ensure_link_exists("BOM", bom_no)

    prepared_qty = coerce_non_negative_float(qty, "工单数量", default=doc.qty or 0)
    if prepared_qty <= 0:
        frappe.throw(_("工单数量必须大于 0。"))

    source_warehouse = normalize_text(source_warehouse)
    wip_warehouse = normalize_text(wip_warehouse)
    fg_warehouse = normalize_text(fg_warehouse)
    description = normalize_text(description)

    ensure_link_exists("Warehouse", source_warehouse)
    ensure_link_exists("Warehouse", wip_warehouse)
    ensure_link_exists("Warehouse", fg_warehouse)

    payload = _build_work_order_payload(
        doc,
        company=company,
        production_item=production_item,
        bom_no=bom_no,
        qty=prepared_qty,
        source_warehouse=source_warehouse,
        wip_warehouse=wip_warehouse,
        fg_warehouse=fg_warehouse,
        description=description,
    )
    return {
        "ok": True,
        "payload": payload,
        "message": _("已根据生产跟踪单生成生产工单草稿。"),
    }


def prepare_stock_entry_from_ticket(
    ticket_name: str,
    *,
    purpose: str | None = None,
    item_code: str | None = None,
    qty: float | str | None = None,
    source_warehouse: str | None = None,
    target_warehouse: str | None = None,
    remark: str | None = None,
) -> dict[str, object]:
    doc = _get_ticket_doc(ticket_name)
    stock_entry_purpose = normalize_select(
        purpose,
        "库存凭证用途",
        STOCK_ENTRY_PURPOSE_OPTIONS,
        default="Material Receipt",
        alias_map=STOCK_ENTRY_PURPOSE_ALIASES,
    )
    stock_item_code = normalize_text(item_code) or doc.item_template
    if not stock_item_code:
        frappe.throw(_("准备库存凭证前必须先指定物料编码。"))
    ensure_link_exists("Item", stock_item_code)

    prepared_qty = coerce_non_negative_float(
        qty,
        "库存凭证数量",
        default=max((doc.qty or 0) - (doc.defect_qty or 0), 0),
    )
    if prepared_qty <= 0:
        frappe.throw(_("库存凭证数量必须大于 0。"))

    source_warehouse = normalize_text(source_warehouse)
    target_warehouse = normalize_text(target_warehouse)
    remark = normalize_text(remark)

    _validate_stock_entry_warehouses(stock_entry_purpose, source_warehouse, target_warehouse)
    ensure_link_exists("Warehouse", source_warehouse)
    ensure_link_exists("Warehouse", target_warehouse)
    if stock_entry_purpose == "Material Transfer for Manufacture" and not doc.work_order:
        frappe.throw(_("生产领料前必须先关联生产工单。"))

    item_row = _build_stock_entry_item_row(
        doc,
        item_code=stock_item_code,
        qty=prepared_qty,
        source_warehouse=source_warehouse,
        target_warehouse=target_warehouse,
    )
    payload = _build_stock_entry_payload(
        doc,
        purpose=stock_entry_purpose,
        source_warehouse=source_warehouse,
        target_warehouse=target_warehouse,
        remark=remark,
        items=[item_row],
    )

    return {
        "ok": True,
        "payload": payload,
        "message": _("已根据生产跟踪单生成库存凭证草稿。"),
    }


def _get_ticket_doc(ticket_name: str):
    if not ticket_name:
        frappe.throw(_("生产跟踪单不能为空。"))
    return frappe.get_doc("Production Ticket", ticket_name)


def _sync_style_defaults(doc) -> None:
    if not doc.style:
        return

    style_item_template = frappe.db.get_value("Style", doc.style, "item_template")
    if style_item_template and not doc.item_template:
        doc.item_template = style_item_template


def _sync_ticket_color(doc) -> None:
    if not doc.color:
        frappe.throw(_("颜色不能为空。"))

    color_data = get_color_metadata(doc.color)
    doc.color = color_data["color"]
    doc.color_name = color_data["color_name"]
    doc.color_code = color_data["color_code"]

    if not doc.style:
        return

    allowed_colors = set(
        frappe.get_all(
            "Style Color",
            filters={"parent": doc.style, "parenttype": "Style", "parentfield": "colors"},
            pluck="color",
        )
    )
    if allowed_colors and doc.color not in allowed_colors:
        frappe.throw(
            _("颜色{0}未配置在款号{1}下。").format(
                frappe.bold(doc.color), frappe.bold(doc.style)
            )
        )


def _sync_stage_logs(doc) -> None:
    if not doc.stage_logs:
        return

    total_defect_qty = 0
    for row in doc.stage_logs:
        row.stage = normalize_select(
            row.stage,
            "阶段日志阶段",
            PRODUCTION_STAGE_OPTIONS,
            default=doc.stage or "计划",
            alias_map=PRODUCTION_STAGE_ALIASES,
        )
        row.qty_in = coerce_non_negative_int(row.qty_in, "投入数量")
        row.qty_out = coerce_non_negative_int(row.qty_out, "产出数量")
        row.defect_qty = coerce_non_negative_int(row.defect_qty, "不良数量")
        row.remark = normalize_text(row.remark)
        row.log_time = row.log_time or now_datetime()

        if row.qty_in and row.qty_out + row.defect_qty > row.qty_in:
            frappe.throw(
                _("阶段 {0} 的产出数量与不良数量之和不能超过投入数量。").format(
                    frappe.bold(row.stage)
                )
            )
        if row.qty_in > doc.qty:
            frappe.throw(
                _("阶段 {0} 的投入数量不能超过工单数量。").format(
                    frappe.bold(row.stage)
                )
            )
        if row.qty_out > doc.qty:
            frappe.throw(
                _("阶段 {0} 的产出数量不能超过工单数量。").format(
                    frappe.bold(row.stage)
                )
            )

        ensure_link_exists("Warehouse", row.warehouse)
        ensure_link_exists("Supplier", row.supplier)
        total_defect_qty += row.defect_qty

    doc.defect_qty = total_defect_qty
    if doc.defect_qty > doc.qty:
        frappe.throw(_("不良数量不能超过工单数量。"))


def _align_stage_with_logs(doc) -> None:
    if not doc.stage_logs:
        return

    last_row = sorted(doc.stage_logs, key=lambda row: cint(row.idx))[ -1 ]
    last_stage = last_row.stage or doc.stage
    if _get_stage_index(last_stage) > _get_stage_index(doc.stage):
        doc.stage = last_stage

    if not doc.actual_start_date and last_row.log_time:
        first_row = sorted(doc.stage_logs, key=lambda row: cint(row.idx))[0]
        doc.actual_start_date = _coerce_date_value(first_row.log_time)

    if last_stage == "完成":
        doc.stage = "完成"
        doc.status = "已完成"
        doc.actual_end_date = doc.actual_end_date or _coerce_date_value(last_row.log_time) or nowdate()


def _validate_dates(doc) -> None:
    if doc.planned_start_date and doc.planned_end_date and doc.planned_end_date < doc.planned_start_date:
        frappe.throw(_("计划结束日期不能早于计划开始日期。"))

    if doc.actual_start_date and doc.actual_end_date and doc.actual_end_date < doc.actual_start_date:
        frappe.throw(_("实际结束日期不能早于实际开始日期。"))


def _validate_business_rules(doc) -> None:
    if doc.defect_qty > doc.qty:
        frappe.throw(_("不良数量不能超过工单数量。"))

    if doc.stage == "完成":
        doc.status = "已完成"

    if doc.status == "已完成":
        doc.stage = "完成"
        doc.actual_end_date = doc.actual_end_date or nowdate()
        doc.actual_start_date = doc.actual_start_date or doc.actual_end_date

    if doc.status == "草稿" and doc.stage != "计划":
        doc.status = "进行中"

    if doc.status in ("进行中", "暂停", "已完成"):
        doc.actual_start_date = doc.actual_start_date or nowdate()

    if doc.status == "暂停" and doc.stage == "计划":
        frappe.throw(_("生产跟踪单开始前不能直接暂停。"))

    if doc.actual_end_date and doc.status not in ("已完成", "已取消"):
        frappe.throw(_("只有已完成或已取消的生产跟踪单才能填写实际结束日期。"))

    _validate_bom_reference(doc)
    _validate_work_order_reference(doc)


def _ensure_ticket_mutable(doc) -> None:
    if doc.status == "已取消":
        frappe.throw(_("已取消的生产跟踪单不能修改。"))
    if doc.status == "已完成":
        frappe.throw(_("已完成的生产跟踪单不能修改。"))


def _ensure_not_on_hold(doc, message: str) -> None:
    if doc.status == "暂停":
        frappe.throw(message)


def _validate_bom_reference(doc) -> None:
    if not doc.bom_no or not frappe.db.exists("BOM", doc.bom_no):
        return

    bom_meta = frappe.get_meta("BOM")
    if bom_meta.has_field("style"):
        bom_style = frappe.db.get_value("BOM", doc.bom_no, "style")
        if bom_style and bom_style != doc.style:
            frappe.throw(
                _("物料清单 {0} 关联的款号是 {1}，而不是 {2}。").format(
                    frappe.bold(doc.bom_no),
                    frappe.bold(bom_style),
                    frappe.bold(doc.style),
                )
            )

    if bom_meta.has_field("production_ticket"):
        bom_ticket = frappe.db.get_value("BOM", doc.bom_no, "production_ticket")
        if bom_ticket and bom_ticket != doc.name:
            frappe.throw(
                _("物料清单 {0} 已经关联到生产跟踪单 {1}。").format(
                    frappe.bold(doc.bom_no),
                    frappe.bold(bom_ticket),
                )
            )

    if bom_meta.has_field("item") and doc.item_template:
        bom_item = frappe.db.get_value("BOM", doc.bom_no, "item")
        if bom_item and bom_item != doc.item_template:
            frappe.throw(
                _("物料清单 {0} 关联的物料是 {1}，而不是 {2}。").format(
                    frappe.bold(doc.bom_no),
                    frappe.bold(bom_item),
                    frappe.bold(doc.item_template),
                )
            )


def _validate_work_order_reference(doc) -> None:
    if not doc.work_order or not frappe.db.exists("Work Order", doc.work_order):
        return

    work_order_meta = frappe.get_meta("Work Order")
    if work_order_meta.has_field("style"):
        work_order_style = frappe.db.get_value("Work Order", doc.work_order, "style")
        if work_order_style and work_order_style != doc.style:
            frappe.throw(
                _("生产工单 {0} 关联的款号是 {1}，而不是 {2}。").format(
                    frappe.bold(doc.work_order),
                    frappe.bold(work_order_style),
                    frappe.bold(doc.style),
                )
            )

    if work_order_meta.has_field("production_ticket"):
        work_order_ticket = frappe.db.get_value("Work Order", doc.work_order, "production_ticket")
        if work_order_ticket and work_order_ticket != doc.name:
            frappe.throw(
                _("生产工单 {0} 已经关联到生产跟踪单 {1}。").format(
                    frappe.bold(doc.work_order),
                    frappe.bold(work_order_ticket),
                )
            )


def _get_stage_index(stage: str | None) -> int:
    return PRODUCTION_STAGE_INDEX.get(stage or "计划", 0)


def _build_ticket_size_range(doc) -> str:
    if not doc.style or not frappe.db.exists("Style", doc.style):
        return ""
    size_system = frappe.db.get_value("Style", doc.style, "size_system")
    return get_size_range_summary(size_system)


def _build_ticket_response(doc, message: str) -> dict[str, object]:
    return {
        "ok": True,
        "name": doc.name,
        "style": doc.style,
        "color": doc.color,
        "color_code": doc.color_code,
        "stage": doc.stage,
        "status": doc.status,
        "qty": doc.qty,
        "defect_qty": doc.defect_qty,
        "actual_start_date": _format_date_value(doc.actual_start_date),
        "actual_end_date": _format_date_value(doc.actual_end_date),
        "message": message,
    }


def _normalize_ticket_dates(doc) -> None:
    doc.planned_start_date = _coerce_date_value(doc.planned_start_date)
    doc.planned_end_date = _coerce_date_value(doc.planned_end_date)
    doc.actual_start_date = _coerce_date_value(doc.actual_start_date)
    doc.actual_end_date = _coerce_date_value(doc.actual_end_date)


def _coerce_date_value(value):
    if not value:
        return None
    return getdate(value)


def _format_date_value(value) -> str | None:
    if not value:
        return None
    return str(getdate(value))


def _validate_stock_entry_warehouses(
    purpose: str,
    source_warehouse: str | None,
    target_warehouse: str | None,
) -> None:
    if purpose == "Material Receipt":
        if not target_warehouse:
            frappe.throw(_("物料入库时，目标仓库不能为空。"))
        return

    if purpose in ("Material Transfer", "Material Transfer for Manufacture"):
        if not source_warehouse:
            frappe.throw(_("用途为{0}时，来源仓库不能为空。").format(_get_purpose_label(purpose)))
        if not target_warehouse:
            frappe.throw(_("用途为{0}时，目标仓库不能为空。").format(_get_purpose_label(purpose)))
        if source_warehouse and target_warehouse and source_warehouse == target_warehouse:
            frappe.throw(_("用途为{0}时，来源仓库和目标仓库不能相同。").format(_get_purpose_label(purpose)))


def _build_stock_entry_item_row(
    doc,
    *,
    item_code: str,
    qty: float,
    source_warehouse: str,
    target_warehouse: str,
) -> dict[str, object]:
    item_data = _get_item_basic_data(item_code)

    row_payload = {
        "doctype": "Stock Entry Detail",
        "item_code": item_code,
        "qty": qty,
        "transfer_qty": qty,
        "basic_qty": qty,
        "item_name": item_data.get("item_name"),
        "uom": item_data.get("stock_uom"),
        "stock_uom": item_data.get("stock_uom"),
        "s_warehouse": source_warehouse,
        "t_warehouse": target_warehouse,
        "style": doc.style,
        "color_code": doc.color_code,
        "production_ticket": doc.name,
    }
    return _filter_doc_payload("Stock Entry Detail", row_payload)


def _build_stock_entry_payload(
    doc,
    *,
    purpose: str,
    source_warehouse: str,
    target_warehouse: str,
    remark: str,
    items: list[dict[str, object]],
) -> dict[str, object]:
    company = _require_ticket_company(doc, "库存凭证")
    stock_entry_type = _get_stock_entry_type(purpose)
    payload = {
        "doctype": "Stock Entry",
        "purpose": purpose,
        "stock_entry_type": stock_entry_type,
        "company": company,
        "work_order": doc.work_order,
        "bom_no": doc.bom_no,
        "from_warehouse": source_warehouse,
        "to_warehouse": target_warehouse,
        "remarks": remark or _("由生产跟踪单 {0} 自动生成。").format(doc.name),
        "items": items,
    }
    return _filter_doc_payload("Stock Entry", payload, items=items)


def _build_bom_payload(
    doc,
    *,
    company: str | None,
    item_code: str,
    source_bom: str | None,
    quantity: float,
    is_active: int,
    is_default: int,
    description: str,
) -> dict[str, object]:
    item_data = _get_item_basic_data(item_code)
    items, operations = _build_bom_children_from_source(source_bom)
    payload = {
        "doctype": "BOM",
        "item": item_code,
        "item_name": item_data.get("item_name"),
        "uom": item_data.get("stock_uom"),
        "item_uom": item_data.get("stock_uom"),
        "quantity": quantity,
        "company": company,
        "style": doc.style,
        "production_ticket": doc.name,
        "color_code": doc.color_code,
        "is_active": is_active,
        "is_default": is_default,
        "description": description or _("由生产跟踪单 {0} 自动生成。").format(doc.name),
        "items": items,
        "operations": operations,
    }
    return _filter_doc_payload("BOM", payload, items=items, operations=operations)


def _resolve_source_bom(source_bom: str | None, *, item_code: str) -> str | None:
    if source_bom:
        ensure_link_exists("BOM", source_bom)
        return source_bom
    return _find_default_source_bom(item_code)


def _find_default_source_bom(item_code: str) -> str | None:
    if not item_code:
        return None

    rows = frappe.get_all(
        "BOM",
        filters={
            "item": item_code,
            "is_active": 1,
            "docstatus": 1,
        },
        fields=["name", "is_default", "modified"],
        order_by="is_default desc, modified desc",
        limit=1,
    )
    return rows[0]["name"] if rows else None


def _build_bom_children_from_source(source_bom: str | None) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if not source_bom:
        return [], []

    bom = frappe.get_doc("BOM", source_bom)
    items = [_clone_bom_child_row(row) for row in (bom.items or [])]
    operations = [_clone_bom_child_row(row) for row in (bom.operations or [])]
    return items, operations


def _clone_bom_child_row(row) -> dict[str, object]:
    blocked_fields = {
        "name",
        "owner",
        "creation",
        "modified",
        "modified_by",
        "docstatus",
        "idx",
        "parent",
        "parentfield",
        "parenttype",
        "doctype",
        "amount",
        "base_amount",
        "stock_qty",
    }
    payload = {"doctype": row.doctype}
    for fieldname, value in row.as_dict().items():
        if fieldname in blocked_fields:
            continue
        payload[fieldname] = value
    return _filter_doc_payload(row.doctype, payload)


def _build_work_order_payload(
    doc,
    *,
    company: str,
    production_item: str,
    bom_no: str | None,
    qty: float,
    source_warehouse: str,
    wip_warehouse: str,
    fg_warehouse: str,
    description: str,
) -> dict[str, object]:
    payload = {
        "doctype": "Work Order",
        "company": company,
        "production_item": production_item,
        "bom_no": bom_no,
        "qty": qty,
        "style": doc.style,
        "production_ticket": doc.name,
        "color_code": doc.color_code,
        "size_range": _build_ticket_size_range(doc),
        "source_warehouse": source_warehouse,
        "wip_warehouse": wip_warehouse,
        "fg_warehouse": fg_warehouse,
        "description": description or _("由生产跟踪单 {0} 自动生成。").format(doc.name),
    }
    return _filter_doc_payload("Work Order", payload)


def _get_item_basic_data(item_code: str) -> dict[str, object]:
    item_meta = frappe.get_meta("Item")
    item_fields = ["item_name"]
    if item_meta.has_field("stock_uom"):
        item_fields.append("stock_uom")
    return frappe.db.get_value("Item", item_code, item_fields, as_dict=True) or {}


def _get_ticket_company(doc) -> str | None:
    if doc.work_order and frappe.db.exists("Work Order", doc.work_order):
        work_order_meta = frappe.get_meta("Work Order")
        if work_order_meta.has_field("company"):
            company = frappe.db.get_value("Work Order", doc.work_order, "company")
            if company:
                return company

    if doc.bom_no and frappe.db.exists("BOM", doc.bom_no):
        bom_meta = frappe.get_meta("BOM")
        if bom_meta.has_field("company"):
            company = frappe.db.get_value("BOM", doc.bom_no, "company")
            if company:
                return company

    defaults = [
        frappe.defaults.get_user_default("Company"),
        frappe.defaults.get_global_default("company"),
        frappe.defaults.get_global_default("Company"),
    ]
    for company in defaults:
        if company and frappe.db.exists("Company", company):
            return company
    return None


def _require_ticket_company(doc, document_label: str) -> str:
    company = _get_ticket_company(doc)
    if company:
        return company
    frappe.throw(
        _("{0}需要公司信息，请先设置默认公司或先关联带公司的生产工单。").format(
            document_label
        )
    )


def _get_stock_entry_type(purpose: str) -> str | None:
    if frappe.db.exists("Stock Entry Type", purpose):
        return purpose
    return None


def _get_purpose_label(purpose: str) -> str:
    return {
        "Material Receipt": "物料入库",
        "Material Transfer": "物料转移",
        "Material Transfer for Manufacture": "生产领料",
    }.get(purpose, purpose)


def _filter_doc_payload(
    doctype: str,
    payload: dict[str, object],
    *,
    items: list[dict[str, object]] | None = None,
    operations: list[dict[str, object]] | None = None,
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
        if fieldname == "operations":
            if meta.has_field("operations") and operations is not None:
                filtered["operations"] = operations
            continue
        if value in (None, ""):
            continue
        if meta.has_field(fieldname):
            filtered[fieldname] = value
    return filtered
