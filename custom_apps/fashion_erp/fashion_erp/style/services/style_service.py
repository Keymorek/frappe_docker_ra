import csv
import re
from pathlib import Path

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
    "Fabric Master": "面料档案",
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
    "Style Category Template": "款式类目模板",
    "Style Season": "季节档案",
    "Style Sub Category": "款式小类",
    "Style Year": "年份档案",
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

STYLE_SEASON_SEEDS = [
    {"season_name": "春夏", "season_code": "SS", "enabled": 1, "sort_order": 10},
    {"season_name": "秋冬", "season_code": "AW", "enabled": 1, "sort_order": 20},
    {"season_name": "全年", "season_code": "ALL", "enabled": 1, "sort_order": 30},
]

BOTTOM_CATEGORY_KEYWORDS = ("裤", "短裤", "牛仔裤", "休闲裤", "西装裤", "卫裤", "连体衣/裤")
DRESS_CATEGORY_KEYWORDS = ("连衣裙", "婚纱", "旗袍", "礼服", "秀禾服")
SKIRT_CATEGORY_KEYWORDS = ("半身裙", "裙子")
SHOE_CATEGORY_KEYWORDS = ("鞋",)
BRA_CATEGORY_KEYWORDS = ("内衣", "文胸", "bra")
ACCESSORY_CATEGORY_KEYWORDS = ("配饰", "帽", "围巾", "腰带")


def normalize_text(value: str | None) -> str:
    return (value or "").strip()


def normalize_size_system_rule_text(value: str | None) -> str:
    return serialize_size_system_rule_text(parse_size_system_rule_text(value))


def parse_size_system_rule_text(value: str | None) -> list[str]:
    rules: list[str] = []
    for line in normalize_text(value).splitlines():
        size_system = normalize_business_code(line, "尺码体系规则")
        if size_system and size_system not in rules:
            rules.append(size_system)
    return rules


def serialize_size_system_rule_text(values: list[str] | tuple[str, ...]) -> str:
    unique_values: list[str] = []
    for value in values or []:
        normalized = normalize_business_code(value, "尺码体系规则")
        if normalized and normalized not in unique_values:
            unique_values.append(normalized)
    return "\n".join(unique_values)


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
    if alias_map:
        normalized = get_select_alias_value(normalized, alias_map)
    if uppercase:
        normalized = normalized.upper()
    if normalized and normalized not in allowed_values:
        frappe.throw(
            _("{0}必须是以下值之一：{1}。").format(field_label, "、".join(allowed_values))
        )
    return normalized


def get_select_alias_value(value: str, alias_map: dict[str, str]) -> str:
    if value in alias_map:
        return alias_map[value]

    folded = value.casefold()
    for alias, target in alias_map.items():
        if alias.casefold() == folded:
            return target
    return value


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


def normalize_category_level(value: str | None) -> str:
    normalized = normalize_text(value)
    if normalized in {"无", "-", "/", "N/A"}:
        return ""
    return normalized


def build_style_category_template_details(
    category_level_1: str | None,
    category_level_2: str | None = None,
    category_level_3: str | None = None,
    category_level_4: str | None = None,
) -> dict[str, object]:
    levels = [
        normalize_category_level(category_level_1),
        normalize_category_level(category_level_2),
        normalize_category_level(category_level_3),
        normalize_category_level(category_level_4),
    ]
    if not levels[0]:
        frappe.throw(_("一级类目不能为空。"))

    for index in range(1, len(levels)):
        if levels[index] and not levels[index - 1]:
            frappe.throw(_("类目层级不能跳级，请按一级到四级连续维护。"))

    non_empty_levels = [level for level in levels if level]
    return {
        "category_level_1": levels[0],
        "category_level_2": levels[1],
        "category_level_3": levels[2],
        "category_level_4": levels[3],
        "leaf_category_name": non_empty_levels[-1],
        "full_path": " / ".join(non_empty_levels),
        "level_depth": len(non_empty_levels),
    }


def get_style_category_template_details(template_name: str | None) -> dict[str, object]:
    if not template_name:
        return {}

    row = frappe.db.get_value(
        "Style Category Template",
        template_name,
        [
            "category_level_1",
            "category_level_2",
            "category_level_3",
            "category_level_4",
            "leaf_category_name",
            "full_path",
            "level_depth",
            "enabled",
        ],
        as_dict=True,
    )
    return row or {}


def guess_size_system_rule_for_category(category_path: str | None) -> dict[str, object]:
    category_text = normalize_text(category_path)
    if not category_text:
        return {"default_size_system": "", "allowed_size_systems": []}

    if _contains_any(category_text, SHOE_CATEGORY_KEYWORDS):
        return {"default_size_system": "SHOE", "allowed_size_systems": ["SHOE"]}
    if _contains_any(category_text, BRA_CATEGORY_KEYWORDS):
        return {"default_size_system": "BRA", "allowed_size_systems": ["BRA"]}
    if _contains_any(category_text, DRESS_CATEGORY_KEYWORDS):
        return {"default_size_system": "DRESS", "allowed_size_systems": ["DRESS"]}
    if _contains_any(category_text, SKIRT_CATEGORY_KEYWORDS):
        return {"default_size_system": "SKIRT", "allowed_size_systems": ["SKIRT"]}
    if _contains_any(category_text, BOTTOM_CATEGORY_KEYWORDS):
        return {"default_size_system": "BOTTOM", "allowed_size_systems": ["BOTTOM"]}
    if _contains_any(category_text, ACCESSORY_CATEGORY_KEYWORDS):
        return {"default_size_system": "ACC", "allowed_size_systems": ["ACC", "FREE"]}
    if "套装" in category_text:
        return {"default_size_system": "TOP", "allowed_size_systems": ["TOP", "FREE"]}
    return {"default_size_system": "TOP", "allowed_size_systems": ["TOP", "FREE"]}


def get_product_category_size_rule(product_category: str | None) -> dict[str, object]:
    if not product_category:
        return {"default_size_system": "", "allowed_size_systems": []}

    row = frappe.db.get_value(
        "Style Category Template",
        product_category,
        ["default_size_system", "allowed_size_systems", "full_path"],
        as_dict=True,
    ) or {}

    allowed_size_systems = parse_size_system_rule_text(row.get("allowed_size_systems"))
    default_size_system = normalize_text(row.get("default_size_system"))
    if not allowed_size_systems:
        guessed = guess_size_system_rule_for_category(row.get("full_path") or product_category)
        allowed_size_systems = guessed["allowed_size_systems"]
        if not default_size_system:
            default_size_system = guessed["default_size_system"]

    if default_size_system and default_size_system not in allowed_size_systems:
        allowed_size_systems.insert(0, default_size_system)

    return {
        "default_size_system": default_size_system,
        "allowed_size_systems": allowed_size_systems,
    }


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


def get_size_range_summary(size_system: str | None, *, selected_size_codes: list[str] | None = None) -> str:
    size_codes = list(selected_size_codes or [])
    if not size_codes:
        size_codes = get_enabled_size_codes(size_system)
    if not size_codes:
        return ""
    if len(size_codes) == 1:
        return size_codes[0]
    return f"{size_codes[0]}-{size_codes[-1]}"


def sync_style_size_row(row, size_system: str) -> None:
    if not getattr(row, "size", None):
        frappe.throw(_("尺码不能为空。"))

    size_row = frappe.db.get_value(
        "Size Code",
        row.size,
        ["size_system", "size_code", "size_name", "sort_order", "enabled"],
        as_dict=True,
    )
    if not size_row:
        frappe.throw(_("尺码{0}不存在。").format(frappe.bold(row.size)))
    if not cint(size_row.enabled):
        frappe.throw(_("尺码{0}已停用。").format(frappe.bold(row.size)))
    if normalize_text(size_row.size_system) != normalize_text(size_system):
        frappe.throw(
            _("尺码{0}不属于尺码体系{1}。").format(
                frappe.bold(size_row.size_code), frappe.bold(size_system)
            )
        )

    row.size_code = size_row.size_code
    row.size_name = size_row.size_name
    row.sort_order = coerce_non_negative_int(size_row.sort_order, "尺码排序")


def get_selected_style_size_rows(style_doc) -> list[object]:
    return sorted(
        [row for row in (getattr(style_doc, "style_sizes", None) or []) if getattr(row, "size_code", None)],
        key=lambda row: (
            coerce_non_negative_int(getattr(row, "sort_order", None), "尺码排序"),
            normalize_text(getattr(row, "size_code", None)),
        ),
    )


def get_selected_style_size_codes(style_doc) -> list[str]:
    return [row.size_code for row in get_selected_style_size_rows(style_doc)]


def style_has_generated_variants(style_name: str | None, *, template_item: str | None = None) -> bool:
    normalized_style_name = normalize_text(style_name)
    if not normalized_style_name:
        return False

    rows = frappe.get_all(
        "Item",
        filters={"style": normalized_style_name},
        fields=["name", "item_code"],
        limit_page_length=0,
    )
    for row in rows or []:
        item_code = normalize_text(row.get("item_code") or row.get("name"))
        if not item_code:
            continue
        if template_item and item_code == normalize_text(template_item):
            continue
        if item_code.startswith("TPL-"):
            continue
        return True
    return False


def get_style_variant_generation_issues(
    style_doc,
    *,
    enabled_size_codes: list[str] | None = None,
    brand_abbreviation: str | None = None,
) -> list[str]:
    issues = []
    category_rule = get_product_category_size_rule(getattr(style_doc, "product_category", None))

    if not style_doc.brand:
        issues.append(_("生成单品编码前必须先选择品牌。"))
    else:
        if not has_brand_abbreviation_field():
            issues.append(_("品牌上缺少品牌简称字段，请先应用本应用的字段配置。"))
        else:
            brand_abbr = brand_abbreviation
            if brand_abbr is None:
                brand_abbr = get_brand_abbreviation(style_doc.brand)
            if brand_abbr:
                brand_abbr = normalize_business_code(brand_abbr, "品牌简称")
            if not brand_abbr:
                issues.append(
                    _("生成单品编码前，品牌{0}必须先维护品牌简称。").format(
                        frappe.bold(style_doc.brand)
                    )
                )

    if not style_doc.size_system:
        issues.append(_("尺码体系不能为空。"))
    elif not is_enabled_doc("Size System", style_doc.size_system):
        issues.append(_("尺码体系{0}已停用。").format(frappe.bold(style_doc.size_system)))
    else:
        allowed_size_systems = category_rule["allowed_size_systems"]
        if allowed_size_systems and style_doc.size_system not in allowed_size_systems:
            issues.append(
                _("商品类目{0}不允许使用尺码体系{1}。").format(
                    frappe.bold(getattr(style_doc, "product_category", "")),
                    frappe.bold(style_doc.size_system),
                )
            )
        size_codes = enabled_size_codes
        if size_codes is None:
            size_codes = get_selected_style_size_codes(style_doc)
        if not size_codes:
            issues.append(
                _("款号{0}还没有选择任何尺码。").format(
                    frappe.bold(getattr(style_doc, "style_code", getattr(style_doc, "name", "")))
                )
            )
        elif not get_enabled_size_codes(style_doc.size_system):
            issues.append(
                _("尺码体系{0}下没有启用的尺码编码。").format(
                    frappe.bold(style_doc.size_system)
                )
            )

    if not style_doc.item_group:
        issues.append(_("生成单品编码前必须先选择成品物料组。"))

    enabled_colors = [row for row in (style_doc.colors or []) if cint(row.enabled)]
    if not enabled_colors:
        issues.append(_("至少需要一条启用的款式颜色。"))

    return issues


def build_style_year_seeds() -> list[dict[str, object]]:
    current_year = get_current_year()
    return [
        {
            "year_name": str(year_value),
            "enabled": 1,
            "sort_order": (index + 1) * 10,
        }
        for index, year_value in enumerate(range(current_year - 1, current_year + 4))
    ]


def load_style_category_template_seeds() -> list[dict[str, object]]:
    csv_path = _find_style_category_csv_path()
    if not csv_path.exists():
        return []

    seeds_by_path: dict[str, dict[str, object]] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            details = build_style_category_template_details(
                row.get("一级类目"),
                row.get("二级类目"),
                row.get("三级类目"),
                row.get("四级类目"),
            )
            size_rule = guess_size_system_rule_for_category(details["full_path"])
            details.update(
                {
                    "source_platform": "抖音",
                    "external_text": normalize_text(row.get("文本")),
                    "default_size_system": size_rule["default_size_system"],
                    "allowed_size_systems": serialize_size_system_rule_text(
                        size_rule["allowed_size_systems"]
                    ),
                    "enabled": 1,
                    "sort_order": index * 10,
                }
            )
            seeds_by_path[details["full_path"]] = details

    return list(seeds_by_path.values())


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

    for row in STYLE_SEASON_SEEDS:
        _upsert_named_doc("Style Season", "season_name", row)

    for row in build_style_year_seeds():
        _upsert_named_doc("Style Year", "year_name", row)

    for row in load_style_category_template_seeds():
        _upsert_named_doc("Style Category Template", "full_path", row)


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


def _find_style_category_csv_path() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "docs" / "抖音抖店女装服饰内衣类目.csv"
        if candidate.exists():
            return candidate
    return current.parents[-1] / "docs" / "抖音抖店女装服饰内衣类目.csv"


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)
