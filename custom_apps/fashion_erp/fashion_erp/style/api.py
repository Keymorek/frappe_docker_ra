import frappe
from frappe import _

from fashion_erp.style.services.sku_service import (
    build_style_matrix,
    create_template_item_for_style,
    generate_variants_for_style,
)
from fashion_erp.style.services.style_service import get_style_variant_generation_issues


def _get_style(style_name: str):
    if not style_name:
        frappe.throw(_("款号不能为空。"))
    return frappe.get_doc("Style", style_name)


@frappe.whitelist()
def create_template_item(style_name: str) -> dict[str, object]:
    style = _get_style(style_name)
    if style.item_template:
        result = create_template_item_for_style(style_name)
        return {
            "ok": True,
            "message": _("模板货品已关联：{0}。").format(frappe.bold(result["item_code"])),
            "result": result,
        }

    result = create_template_item_for_style(style_name)
    return {
        "ok": True,
        "message": _("模板货品已准备完成：{0}。").format(frappe.bold(result["item_code"])),
        "result": result,
    }


@frappe.whitelist()
def generate_variants(style_name: str) -> dict[str, object]:
    style = _get_style(style_name)
    issues = get_style_variant_generation_issues(style)
    if issues:
        return {
            "ok": False,
            "message": _("当前款号暂不满足单品编码生成条件。"),
            "issues": issues,
        }

    result = generate_variants_for_style(style_name)
    return {
        "ok": True,
        "message": _("单品编码生成完成。新增：{0}，更新：{1}，未变更：{2}。").format(
            len(result["created"]),
            len(result["updated"]),
            len(result["skipped"]),
        ),
        "result": result,
    }


@frappe.whitelist()
def get_style_matrix(style_name: str) -> dict[str, object]:
    style = _get_style(style_name)
    if not style.colors:
        return {
            "ok": False,
            "message": _("当前款号还没有配置颜色。"),
            "issues": [_("请先新增至少一条款式颜色。")],
        }

    return {
        "ok": True,
        "result": build_style_matrix(style_name),
    }
