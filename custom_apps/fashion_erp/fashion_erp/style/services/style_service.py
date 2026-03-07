import re

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate


BUSINESS_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")
SEASON_OPTIONS = ("春夏", "秋冬", "全年")
SEASON_ALIASES = {"SS": "春夏", "AW": "秋冬", "ALL": "全年"}
GENDER_OPTIONS = ("女装", "中性", "童装")
GENDER_ALIASES = {"Women": "女装", "Unisex": "中性", "Kids": "童装"}
LAUNCH_STATUS_OPTIONS = ("草稿", "打样中", "已核准", "待上市", "已上市", "已归档")
LAUNCH_STATUS_ALIASES = {
    "Draft": "草稿",
    "Sampling": "打样中",
    "Approved": "已核准",
    "Ready": "待上市",
    "Launched": "已上市",
    "Archived": "已归档",
}
SALES_STATUS_OPTIONS = ("未开售", "在售", "停售", "清仓", "已停产")
SALES_STATUS_ALIASES = {
    "Not Ready": "未开售",
    "On Sale": "在售",
    "Stop Sale": "停售",
    "Clearance": "清仓",
    "Discontinued": "已停产",
}
DOCTYPE_LABELS = {
    "After Sales Ticket": "售后工单",
    "BOM": "物料清单",
    "Brand": "品牌",
    "Channel Store": "渠道店铺",
    "Color": "颜色",
    "Color Group": "颜色组",
    "Company": "公司",
    "Craft Sheet": "工艺单",
    "Craft Sheet Log": "工艺单日志",
    "Customer": "客户",
    "Delivery Note": "发货单",
    "Delivery Note Item": "发货单明细",
    "Inventory Status": "库存状态",
    "Item": "物料",
    "Item Group": "物料组",
    "Outsource Order": "外包单",
    "Outsource Order Log": "外包单日志",
    "Outsource Order Material": "外包原辅料明细",
    "Outsource Receipt": "外包到货单",
    "Outsource Receipt Item": "外包到货明细",
    "Outsource Receipt Log": "外包到货日志",
    "Price List": "价格表",
    "Purchase Invoice": "采购发票",
    "Purchase Order": "采购订单",
    "Purchase Receipt": "采购收货",
    "Production Ticket": "生产跟踪单",
    "Return Disposition": "退货处理结果",
    "Return Reason": "退货原因",
    "Sales Invoice": "销售发票",
    "Sales Order": "销售订单",
    "Sales Order Item": "销售订单明细",
    "Sample Ticket": "打样单",
    "Sample Ticket Log": "打样日志",
    "Size Code": "尺码编码",
    "Size System": "尺码体系",
    "Style": "款号",
    "Style Category": "款式大类",
    "Style Sub Category": "款式小类",
    "Supplier": "供应商",
    "User": "用户",
    "Warehouse": "仓库",
    "Warehouse Location": "仓库库位",
    "Warehouse Zone": "仓区",
    "Work Order": "生产工单",
}

COLOR_GROUP_SEEDS = [
    {"color_group_code": "WHT", "color_group_name": "白色系", "sort_order": 10, "enabled": 1},
    {"color_group_code": "BLK", "color_group_name": "黑色系", "sort_order": 20, "enabled": 1},
    {"color_group_code": "GRY", "color_group_name": "灰色系", "sort_order": 30, "enabled": 1},
    {"color_group_code": "BLU", "color_group_name": "蓝色系", "sort_order": 40, "enabled": 1},
    {"color_group_code": "RED", "color_group_name": "红色系", "sort_order": 50, "enabled": 1},
    {"color_group_code": "PNK", "color_group_name": "粉色系", "sort_order": 60, "enabled": 1},
    {"color_group_code": "GRN", "color_group_name": "绿色系", "sort_order": 70, "enabled": 1},
    {"color_group_code": "BRN", "color_group_name": "棕色系", "sort_order": 80, "enabled": 1},
    {"color_group_code": "KHK", "color_group_name": "卡其色系", "sort_order": 90, "enabled": 1},
    {"color_group_code": "YLW", "color_group_name": "黄色系", "sort_order": 100, "enabled": 1},
]

COLOR_SEEDS = [
    {"color_name": "奶油白", "color_group": "WHT", "enabled": 1},
    {"color_name": "米白", "color_group": "WHT", "enabled": 1},
    {"color_name": "象牙白", "color_group": "WHT", "enabled": 1},
    {"color_name": "本白", "color_group": "WHT", "enabled": 1},
    {"color_name": "冷白", "color_group": "WHT", "enabled": 1},
    {"color_name": "黑色", "color_group": "BLK", "enabled": 1},
    {"color_name": "炭灰", "color_group": "GRY", "enabled": 1},
    {"color_name": "藏蓝", "color_group": "BLU", "enabled": 1},
    {"color_name": "酒红", "color_group": "RED", "enabled": 1},
    {"color_name": "豆沙粉", "color_group": "PNK", "enabled": 1},
    {"color_name": "军绿", "color_group": "GRN", "enabled": 1},
    {"color_name": "巧克力棕", "color_group": "BRN", "enabled": 1},
    {"color_name": "卡其", "color_group": "KHK", "enabled": 1},
    {"color_name": "奶黄", "color_group": "YLW", "enabled": 1},
]

SIZE_SYSTEM_SEEDS = [
    {
        "size_system_code": "TOP",
        "size_system_name": "上装尺码",
        "applicable_products": "T恤、衬衫、针织衫、卫衣、外套",
        "enabled": 1,
    },
    {
        "size_system_code": "DRESS",
        "size_system_name": "连衣裙尺码",
        "applicable_products": "连衣裙",
        "enabled": 1,
    },
    {
        "size_system_code": "BOTTOM",
        "size_system_name": "裤装尺码",
        "applicable_products": "牛仔裤、休闲裤",
        "enabled": 1,
    },
    {
        "size_system_code": "SKIRT",
        "size_system_name": "半裙尺码",
        "applicable_products": "短裙、长裙",
        "enabled": 1,
    },
    {
        "size_system_code": "SHOE",
        "size_system_name": "鞋类尺码",
        "applicable_products": "女鞋",
        "enabled": 1,
    },
    {
        "size_system_code": "FREE",
        "size_system_name": "均码体系",
        "applicable_products": "均码商品",
        "enabled": 1,
    },
    {
        "size_system_code": "BRA",
        "size_system_name": "内衣尺码",
        "applicable_products": "内衣",
        "enabled": 1,
    },
    {
        "size_system_code": "ACC",
        "size_system_name": "配饰尺码",
        "applicable_products": "帽子、围巾、腰带等",
        "enabled": 1,
    },
]

SIZE_CODE_SEEDS = [
    {"size_system": "TOP", "size_code": "XXS", "size_name": "XXS", "sort_order": 10, "enabled": 1},
    {"size_system": "TOP", "size_code": "XS", "size_name": "XS", "sort_order": 20, "enabled": 1},
    {"size_system": "TOP", "size_code": "S", "size_name": "S", "sort_order": 30, "enabled": 1},
    {"size_system": "TOP", "size_code": "M", "size_name": "M", "sort_order": 40, "enabled": 1},
    {"size_system": "TOP", "size_code": "L", "size_name": "L", "sort_order": 50, "enabled": 1},
    {"size_system": "TOP", "size_code": "XL", "size_name": "XL", "sort_order": 60, "enabled": 1},
    {"size_system": "TOP", "size_code": "XXL", "size_name": "2XL", "sort_order": 70, "enabled": 1},
    {"size_system": "TOP", "size_code": "XXXL", "size_name": "3XL", "sort_order": 80, "enabled": 1},
    {"size_system": "TOP", "size_code": "F", "size_name": "F", "sort_order": 90, "enabled": 1},
    {"size_system": "DRESS", "size_code": "XS", "size_name": "XS", "sort_order": 10, "enabled": 1},
    {"size_system": "DRESS", "size_code": "S", "size_name": "S", "sort_order": 20, "enabled": 1},
    {"size_system": "DRESS", "size_code": "M", "size_name": "M", "sort_order": 30, "enabled": 1},
    {"size_system": "DRESS", "size_code": "L", "size_name": "L", "sort_order": 40, "enabled": 1},
    {"size_system": "DRESS", "size_code": "XL", "size_name": "XL", "sort_order": 50, "enabled": 1},
    {"size_system": "SKIRT", "size_code": "XS", "size_name": "XS", "sort_order": 10, "enabled": 1},
    {"size_system": "SKIRT", "size_code": "S", "size_name": "S", "sort_order": 20, "enabled": 1},
    {"size_system": "SKIRT", "size_code": "M", "size_name": "M", "sort_order": 30, "enabled": 1},
    {"size_system": "SKIRT", "size_code": "L", "size_name": "L", "sort_order": 40, "enabled": 1},
    {"size_system": "SKIRT", "size_code": "XL", "size_name": "XL", "sort_order": 50, "enabled": 1},
    {"size_system": "BOTTOM", "size_code": "24", "size_name": "24", "sort_order": 10, "enabled": 1},
    {"size_system": "BOTTOM", "size_code": "25", "size_name": "25", "sort_order": 20, "enabled": 1},
    {"size_system": "BOTTOM", "size_code": "26", "size_name": "26", "sort_order": 30, "enabled": 1},
    {"size_system": "BOTTOM", "size_code": "27", "size_name": "27", "sort_order": 40, "enabled": 1},
    {"size_system": "BOTTOM", "size_code": "28", "size_name": "28", "sort_order": 50, "enabled": 1},
    {"size_system": "BOTTOM", "size_code": "29", "size_name": "29", "sort_order": 60, "enabled": 1},
    {"size_system": "BOTTOM", "size_code": "30", "size_name": "30", "sort_order": 70, "enabled": 1},
    {"size_system": "BOTTOM", "size_code": "31", "size_name": "31", "sort_order": 80, "enabled": 1},
    {"size_system": "BOTTOM", "size_code": "32", "size_name": "32", "sort_order": 90, "enabled": 1},
    {"size_system": "FREE", "size_code": "ONE", "size_name": "均码", "sort_order": 10, "enabled": 1},
    {"size_system": "ACC", "size_code": "ONE", "size_name": "均码", "sort_order": 10, "enabled": 1},
]


def normalize_text(value: str | None) -> str:
    return (value or "").strip()


def normalize_business_code(value: str | None, field_label: str) -> str:
    code = normalize_text(value).upper()
    if code and not BUSINESS_CODE_PATTERN.fullmatch(code):
        frappe.throw(
            _("{0}只能包含大写字母、数字、中划线或下划线。").format(
                field_label
            )
        )
    return code


def coerce_checkbox(value: object, default: int = 1) -> int:
    if value in (None, ""):
        return default
    return 1 if cint(value) else 0


def coerce_non_negative_int(value: object, field_label: str, default: int = 0) -> int:
    number = cint(value if value not in (None, "") else default)
    if number < 0:
        frappe.throw(_("{0}不能为负数。").format(field_label))
    return number


def coerce_non_negative_float(value: object, field_label: str, default: float = 0) -> float:
    number = flt(value if value not in (None, "") else default)
    if number < 0:
        frappe.throw(_("{0}不能为负数。").format(field_label))
    return number


def normalize_select(
    value: str | None,
    field_label: str,
    allowed_values: tuple[str, ...],
    *,
    default: str | None = None,
    uppercase: bool = False,
    alias_map: dict[str, str] | None = None,
) -> str:
    normalized = normalize_text(value) or normalize_text(default)
    if alias_map and normalized in alias_map:
        normalized = alias_map[normalized]
    if uppercase:
        normalized = normalized.upper()
    if normalized and normalized not in allowed_values:
        frappe.throw(
            _("{0}必须是以下值之一：{1}。").format(field_label, "、".join(allowed_values))
        )
    return normalized


def get_doctype_label(doctype: str) -> str:
    return DOCTYPE_LABELS.get(doctype, doctype)


def ensure_link_exists(doctype: str, name: str | None) -> None:
    if not name:
        return
    if not frappe.db.exists(doctype, name):
        frappe.throw(
            _("{0}{1}不存在。").format(get_doctype_label(doctype), frappe.bold(name))
        )


def is_enabled_doc(doctype: str, name: str | None, enabled_field: str = "enabled") -> bool:
    if not name or not frappe.db.exists(doctype, name):
        return False
    value = frappe.db.get_value(doctype, name, enabled_field)
    if value is None:
        return True
    return bool(cint(value))


def ensure_enabled_link(doctype: str, name: str | None, enabled_field: str = "enabled") -> None:
    ensure_link_exists(doctype, name)
    if name and not is_enabled_doc(doctype, name, enabled_field):
        frappe.throw(
            _("{0}{1}已停用。").format(get_doctype_label(doctype), frappe.bold(name))
        )


def get_current_year() -> int:
    return int(nowdate().split("-")[0])


def has_brand_abbreviation_field() -> bool:
    return frappe.get_meta("Brand").has_field("brand_abbr")


def get_brand_abbreviation(brand_name: str | None, *, raise_on_missing_meta: bool = False) -> str:
    if not brand_name:
        return ""

    ensure_link_exists("Brand", brand_name)

    if not has_brand_abbreviation_field():
        if raise_on_missing_meta:
            frappe.throw(_("品牌简称字段缺失，请先应用本应用的字段配置。"))
        return ""

    brand_abbr = frappe.db.get_value("Brand", brand_name, "brand_abbr")
    return normalize_business_code(brand_abbr, "品牌简称")


def get_color_metadata(color_name: str | None) -> dict[str, object]:
    if not color_name:
        frappe.throw(_("颜色不能为空。"))

    color = frappe.db.get_value(
        "Color",
        color_name,
        ["name", "color_name", "color_group", "enabled"],
        as_dict=True,
    )
    if not color:
        frappe.throw(_("颜色{0}不存在。").format(frappe.bold(color_name)))
    if not cint(color.enabled):
        frappe.throw(_("颜色{0}已停用。").format(frappe.bold(color_name)))

    group = frappe.db.get_value(
        "Color Group",
        color.color_group,
        ["name", "color_group_code", "enabled"],
        as_dict=True,
    )
    if not group:
        frappe.throw(
            _("颜色{1}关联的颜色组{0}不存在。").format(
                frappe.bold(color.color_group), frappe.bold(color_name)
            )
        )
    if not cint(group.enabled):
        frappe.throw(_("颜色组{0}已停用。").format(frappe.bold(group.name)))

    return {
        "color": color.name,
        "color_name": color.color_name,
        "color_group": color.color_group,
        "color_code": group.color_group_code,
    }


def sync_style_color_row(row, default_sort_order: int = 0) -> None:
    color_data = get_color_metadata(row.color)
    row.color = color_data["color"]
    row.color_name = color_data["color_name"]
    row.color_code = color_data["color_code"]
    row.sort_order = coerce_non_negative_int(row.sort_order, "款式颜色排序", default_sort_order)
    row.enabled = coerce_checkbox(row.enabled)


def get_enabled_size_codes(size_system: str | None) -> list[str]:
    if not size_system:
        return []
    return frappe.get_all(
        "Size Code",
        filters={"size_system": size_system, "enabled": 1},
        pluck="size_code",
        order_by="sort_order asc, size_code asc",
    )


def get_size_range_summary(size_system: str | None) -> str:
    size_codes = get_enabled_size_codes(size_system)
    if not size_codes:
        return ""
    if len(size_codes) == 1:
        return size_codes[0]
    return f"{size_codes[0]}-{size_codes[-1]}"


def get_style_variant_generation_issues(style_doc) -> list[str]:
    issues = []

    if not style_doc.brand:
        issues.append(_("生成单品编码前必须先选择品牌。"))
    else:
        if not has_brand_abbreviation_field():
            issues.append(_("品牌上缺少品牌简称字段，请先应用本应用的字段配置。"))
        elif not get_brand_abbreviation(style_doc.brand):
            issues.append(
                _("生成单品编码前，品牌{0}必须先维护品牌简称。").format(
                    frappe.bold(style_doc.brand)
                )
            )

    if not style_doc.size_system:
        issues.append(_("尺码体系不能为空。"))
    elif not is_enabled_doc("Size System", style_doc.size_system):
        issues.append(_("尺码体系{0}已停用。").format(frappe.bold(style_doc.size_system)))
    elif not get_enabled_size_codes(style_doc.size_system):
        issues.append(
            _("尺码体系{0}下没有启用的尺码编码。").format(
                frappe.bold(style_doc.size_system)
            )
        )

    if not style_doc.item_group:
        issues.append(_("生成单品编码前必须先选择物料组。"))

    enabled_colors = [row for row in (style_doc.colors or []) if cint(row.enabled)]
    if not enabled_colors:
        issues.append(_("至少需要一条启用的款式颜色。"))

    return issues


def seed_master_data() -> None:
    for row in COLOR_GROUP_SEEDS:
        _upsert_named_doc("Color Group", "color_group_code", row)

    for row in COLOR_SEEDS:
        ensure_link_exists("Color Group", row["color_group"])
        _upsert_named_doc("Color", "color_name", row)

    for row in SIZE_SYSTEM_SEEDS:
        _upsert_named_doc("Size System", "size_system_code", row)

    for row in SIZE_CODE_SEEDS:
        ensure_link_exists("Size System", row["size_system"])
        _upsert_size_code(row)


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


def _upsert_size_code(values: dict[str, object]) -> str:
    filters = {"size_system": values["size_system"], "size_code": values["size_code"]}
    existing = frappe.db.get_value("Size Code", filters, "name")
    if existing:
        doc = frappe.get_doc("Size Code", existing)
        changed = False
        for fieldname, value in values.items():
            if doc.get(fieldname) != value:
                doc.set(fieldname, value)
                changed = True
        if changed:
            doc.save(ignore_permissions=True)
        return doc.name

    doc = frappe.get_doc({"doctype": "Size Code", **values})
    doc.insert(ignore_permissions=True)
    return doc.name
