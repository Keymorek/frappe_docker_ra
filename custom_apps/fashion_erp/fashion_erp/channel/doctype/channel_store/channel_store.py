from frappe import _
from frappe.model.document import Document

from fashion_erp.style.services.style_service import (
    ensure_link_exists,
    normalize_select,
    normalize_text,
)


CHANNEL_OPTIONS = ("手工", "抖音", "虾皮", "独立站")
CHANNEL_ALIASES = {
    "Manual": "手工",
    "TikTok": "抖音",
    "Shopee": "虾皮",
    "Shopify": "独立站",
}
CHANNEL_STORE_STATUS_OPTIONS = ("草稿", "启用", "停用")
CHANNEL_STORE_STATUS_ALIASES = {
    "Draft": "草稿",
    "Active": "启用",
    "Disabled": "停用",
}


class ChannelStore(Document):
    def validate(self) -> None:
        self.channel = normalize_select(
            self.channel,
            "渠道",
            CHANNEL_OPTIONS,
            default="手工",
            alias_map=CHANNEL_ALIASES,
        )
        self.store_name = normalize_text(self.store_name)
        self.status = normalize_select(
            self.status,
            "状态",
            CHANNEL_STORE_STATUS_OPTIONS,
            default="草稿",
            alias_map=CHANNEL_STORE_STATUS_ALIASES,
        )
        self.api_config_ref = normalize_text(self.api_config_ref)

        ensure_link_exists("Warehouse", self.warehouse)
        ensure_link_exists("Price List", self.price_list)

        if self.status == "启用" and not self.warehouse:
            from frappe import throw

            throw(_("渠道店铺状态为启用时，仓库不能为空。"))
