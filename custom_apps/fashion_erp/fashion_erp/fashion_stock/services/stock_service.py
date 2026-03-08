import frappe
from frappe import _

from fashion_erp.style.services.style_service import ensure_enabled_link, normalize_text


LOCATION_TYPE_OPTIONS = ("拣货", "存储", "缓冲")
LOCATION_TYPE_ALIASES = {
    "PICK": "拣货",
    "STORAGE": "存储",
    "BUFFER": "缓冲",
}
ENTRY_ALLOWED_INVENTORY_STATUSES = {
    "QC_PENDING",
    "SELLABLE",
    "RETURN_PENDING",
    "SAMPLE",
    "FROZEN",
}
ALLOWED_INVENTORY_STATUS_TRANSITIONS = {
    "SELLABLE": {"RESERVED", "SAMPLE", "FROZEN"},
    "RESERVED": {"SELLABLE", "FROZEN"},
    "QC_PENDING": {"SELLABLE", "REPAIR", "DEFECTIVE", "FROZEN"},
    "RETURN_PENDING": {"SELLABLE", "REPAIR", "DEFECTIVE", "SAMPLE", "FROZEN"},
    "REPAIR": {"SELLABLE", "DEFECTIVE", "FROZEN"},
    "DEFECTIVE": {"FROZEN"},
    "SAMPLE": {"SELLABLE", "FROZEN"},
    "FROZEN": {"SELLABLE", "DEFECTIVE", "RETURN_PENDING", "REPAIR", "SAMPLE"},
}

WAREHOUSE_ZONE_SEEDS = [
    {"zone_code": "IN", "zone_name": "收货区", "purpose": "新货/退货签收", "enabled": 1, "sort_order": 10},
    {"zone_code": "QC", "zone_name": "待检区", "purpose": "质检前暂存", "enabled": 1, "sort_order": 20},
    {"zone_code": "FG", "zone_name": "成衣可售区", "purpose": "正常可售库存", "enabled": 1, "sort_order": 30},
    {"zone_code": "PK", "zone_name": "打包区", "purpose": "打包复核、待出货", "enabled": 1, "sort_order": 40},
    {"zone_code": "RT", "zone_name": "退货待检区", "purpose": "售后退回暂存", "enabled": 1, "sort_order": 50},
    {"zone_code": "RF", "zone_name": "返修区", "purpose": "可修复问题件", "enabled": 1, "sort_order": 60},
    {"zone_code": "DP", "zone_name": "次品区", "purpose": "不可售或待处理", "enabled": 1, "sort_order": 70},
    {"zone_code": "SM", "zone_name": "样衣区", "purpose": "样衣、直播样板", "enabled": 1, "sort_order": 80},
    {"zone_code": "FR", "zone_name": "冻结区", "purpose": "异常库存冻结", "enabled": 1, "sort_order": 90},
]

INVENTORY_STATUS_SEEDS = [
    {"status_code": "SELLABLE", "status_name": "可售", "is_sellable": 1, "enabled": 1, "sort_order": 10},
    {"status_code": "RESERVED", "status_name": "已预留", "is_sellable": 0, "enabled": 1, "sort_order": 20},
    {"status_code": "QC_PENDING", "status_name": "待质检", "is_sellable": 0, "enabled": 1, "sort_order": 30},
    {"status_code": "RETURN_PENDING", "status_name": "退货待检", "is_sellable": 0, "enabled": 1, "sort_order": 40},
    {"status_code": "REPAIR", "status_name": "返修中", "is_sellable": 0, "enabled": 1, "sort_order": 50},
    {"status_code": "DEFECTIVE", "status_name": "次品", "is_sellable": 0, "enabled": 1, "sort_order": 60},
    {"status_code": "FROZEN", "status_name": "冻结", "is_sellable": 0, "enabled": 1, "sort_order": 70},
    {"status_code": "SAMPLE", "status_name": "样衣", "is_sellable": 0, "enabled": 1, "sort_order": 80},
]
RETURN_REASON_SEEDS = [
    {"reason_code": "R01", "reason_name": "尺码不合适", "enabled": 1, "sort_order": 10},
    {"reason_code": "R02", "reason_name": "颜色不喜欢", "enabled": 1, "sort_order": 20},
    {"reason_code": "R03", "reason_name": "款式不喜欢", "enabled": 1, "sort_order": 30},
    {"reason_code": "R04", "reason_name": "质量问题", "enabled": 1, "sort_order": 40},
    {"reason_code": "R05", "reason_name": "发错货", "enabled": 1, "sort_order": 50},
    {"reason_code": "R06", "reason_name": "物流问题", "enabled": 1, "sort_order": 60},
    {"reason_code": "R07", "reason_name": "与描述不符", "enabled": 1, "sort_order": 70},
    {"reason_code": "R99", "reason_name": "其他", "enabled": 1, "sort_order": 999},
]
RETURN_DISPOSITION_SEEDS = [
    {
        "disposition_code": "A1",
        "disposition_name": "全新可售",
        "target_inventory_status": "SELLABLE",
        "return_to_sellable": 1,
        "enabled": 1,
        "sort_order": 10,
    },
    {
        "disposition_code": "A2",
        "disposition_name": "整理后可售",
        "target_inventory_status": "SELLABLE",
        "return_to_sellable": 1,
        "enabled": 1,
        "sort_order": 20,
    },
    {
        "disposition_code": "B1",
        "disposition_name": "需返修",
        "target_inventory_status": "REPAIR",
        "return_to_sellable": 0,
        "enabled": 1,
        "sort_order": 30,
    },
    {
        "disposition_code": "B2",
        "disposition_name": "次品不可售",
        "target_inventory_status": "DEFECTIVE",
        "return_to_sellable": 0,
        "enabled": 1,
        "sort_order": 40,
    },
    {
        "disposition_code": "C1",
        "disposition_name": "样衣回收",
        "target_inventory_status": "SAMPLE",
        "return_to_sellable": 0,
        "enabled": 1,
        "sort_order": 50,
    },
    {
        "disposition_code": "D1",
        "disposition_name": "异常争议",
        "target_inventory_status": "FROZEN",
        "return_to_sellable": 0,
        "enabled": 1,
        "sort_order": 60,
    },
]


def seed_stock_master_data() -> None:
    for row in WAREHOUSE_ZONE_SEEDS:
        _upsert_named_doc("Warehouse Zone", "zone_code", row)

    for row in INVENTORY_STATUS_SEEDS:
        _upsert_named_doc("Inventory Status", "status_code", row)

    for row in RETURN_REASON_SEEDS:
        _upsert_named_doc("Return Reason", "reason_code", row)

    for row in RETURN_DISPOSITION_SEEDS:
        _upsert_named_doc("Return Disposition", "disposition_code", row)


def validate_location_type(value: str | None) -> str:
    location_type = normalize_text(value) or "存储"
    location_type = LOCATION_TYPE_ALIASES.get(location_type.upper(), location_type)
    if location_type not in LOCATION_TYPE_OPTIONS:
        frappe.throw(
            _("库位类型必须是以下值之一：{0}。").format("、".join(LOCATION_TYPE_OPTIONS))
        )
    return location_type


def normalize_location_code(value: str | None) -> str:
    location_code = normalize_text(value).upper()
    if not location_code:
        frappe.throw(_("库位编码不能为空。"))
    return location_code


def prepare_return_metadata(row) -> None:
    row.return_reason = normalize_text(getattr(row, "return_reason", None))
    row.return_disposition = normalize_text(getattr(row, "return_disposition", None))
    row.inventory_status_from = normalize_text(
        getattr(row, "inventory_status_from", None)
    ).upper()
    row.inventory_status_to = normalize_text(
        getattr(row, "inventory_status_to", None)
    ).upper()

    if row.return_reason:
        ensure_enabled_link("Return Reason", row.return_reason)

    if row.return_disposition:
        ensure_enabled_link("Return Disposition", row.return_disposition)
        target_status = normalize_text(
            frappe.db.get_value(
                "Return Disposition",
                row.return_disposition,
                "target_inventory_status",
            )
        ).upper()
        if not row.inventory_status_to:
            row.inventory_status_to = target_status
        elif row.inventory_status_to != target_status:
            frappe.throw(
                _(
                    "退货处理结果 {0} 要求目标库存状态必须为 {1}。"
                ).format(frappe.bold(row.return_disposition), frappe.bold(target_status))
            )

        if not row.return_reason and row.inventory_status_from == "RETURN_PENDING":
            frappe.throw(
                _(
                    "应用退货处理结果 {0} 时，退货原因不能为空。"
                ).format(frappe.bold(row.return_disposition))
            )

    if row.return_reason and not row.inventory_status_to:
        frappe.throw(_("填写退货原因后，目标库存状态不能为空。"))


def validate_inventory_status_transition(
    from_status: str | None,
    to_status: str | None,
    *,
    row_label: str = "",
) -> None:
    current_status = normalize_text(from_status).upper()
    next_status = normalize_text(to_status).upper()

    if not current_status and not next_status:
        return

    context = f"（{row_label}）" if row_label else ""

    ensure_enabled_link("Inventory Status", current_status)
    ensure_enabled_link("Inventory Status", next_status)

    if current_status == next_status:
        return

    if not current_status:
        if next_status not in ENTRY_ALLOWED_INVENTORY_STATUSES:
            frappe.throw(
                _(
                    "库存状态 {0} 不能作为入库初始状态{1}。"
                ).format(frappe.bold(get_inventory_status_display(next_status)), context)
            )
        return

    allowed_targets = ALLOWED_INVENTORY_STATUS_TRANSITIONS.get(current_status, set())
    if next_status not in allowed_targets:
        frappe.throw(
            _(
                "库存状态不允许从 {0} 流转到 {1}{2}。"
            ).format(
                frappe.bold(get_inventory_status_display(current_status)),
                frappe.bold(get_inventory_status_display(next_status)),
                context,
            )
        )


def get_inventory_status_display(status_code: str | None) -> str:
    normalized = normalize_text(status_code).upper()
    if not normalized:
        return ""

    for row in INVENTORY_STATUS_SEEDS:
        if row["status_code"] == normalized:
            return row["status_name"]

    status_name = frappe.db.get_value("Inventory Status", normalized, "status_name")
    return normalize_text(status_name) or normalized


def _upsert_named_doc(doctype: str, name_field: str, values: dict[str, object]) -> str:
    docname = values[name_field]
    if frappe.db.exists(doctype, docname):
        doc = frappe.get_doc(doctype, docname)
        changed = False
        for fieldname, value in values.items():
            if doc.get(fieldname) != value:
                doc.set(fieldname, value)
                changed = True
        if changed:
            doc.save(ignore_permissions=True)
        return doc.name

    doc = frappe.get_doc({"doctype": doctype, **values})
    doc.insert(ignore_permissions=True)
    return doc.name
