import frappe


CHANNEL_VALUE_MAP = {
    "Manual": "手工",
    "TikTok": "抖音",
    "Shopee": "虾皮",
    "Shopify": "独立站",
}
CHANNEL_STATUS_MAP = {
    "Draft": "草稿",
    "Active": "启用",
    "Disabled": "停用",
}
STYLE_SEASON_MAP = {"SS": "春夏", "AW": "秋冬", "ALL": "全年"}
STYLE_GENDER_MAP = {"Women": "女装", "Unisex": "中性", "Kids": "童装"}
STYLE_LAUNCH_STATUS_MAP = {
    "Draft": "草稿",
    "Sampling": "打样中",
    "Approved": "已核准",
    "Ready": "待上市",
    "Launched": "已上市",
    "Archived": "已归档",
}
STYLE_SALES_STATUS_MAP = {
    "Not Ready": "未开售",
    "On Sale": "在售",
    "Stop Sale": "停售",
    "Clearance": "清仓",
    "Discontinued": "已停产",
}
PRODUCTION_STAGE_MAP = {
    "Planned": "计划",
    "Cutting": "裁剪",
    "Stitching": "车缝",
    "Finishing": "后整",
    "Packing": "包装",
    "Done": "完成",
}
PRODUCTION_STATUS_MAP = {
    "Draft": "草稿",
    "In Progress": "进行中",
    "Hold": "暂停",
    "Completed": "已完成",
    "Cancelled": "已取消",
}
LOCATION_TYPE_MAP = {"PICK": "拣货", "STORAGE": "存储", "BUFFER": "缓冲"}
AFTER_SALES_TICKET_TYPE_MAP = {
    "REFUND_ONLY": "仅退款",
    "RETURN_REFUND": "退货退款",
    "EXCHANGE": "换货",
    "RESEND": "补发",
    "REPAIR": "维修",
    "COMPLAINT": "投诉",
}
AFTER_SALES_TICKET_STATUS_MAP = {
    "NEW": "新建",
    "WAITING_RETURN": "待退回",
    "RECEIVED": "已收货",
    "INSPECTING": "质检中",
    "PENDING_DECISION": "待处理",
    "WAITING_REFUND": "待退款",
    "WAITING_RESEND": "待补发",
    "CLOSED": "已关闭",
    "CANCELLED": "已取消",
}
AFTER_SALES_PRIORITY_MAP = {
    "Low": "低",
    "Normal": "普通",
    "High": "高",
    "Urgent": "紧急",
}
REFUND_STATUS_MAP = {
    "NOT_REQUIRED": "无需退款",
    "PENDING": "待退款",
    "DONE": "已退款",
    "REJECTED": "已驳回",
}
AFTER_SALES_LOG_ACTION_MAP = {
    "CREATE": "创建",
    "STATUS_CHANGE": "状态变更",
    "RECEIVE": "收货",
    "INSPECT": "质检",
    "REFUND": "退款",
    "RESEND": "补发",
    "CLOSE": "关闭",
    "COMMENT": "备注",
}
SALES_ORDER_BIZ_TYPE_MAP = {
    "Retail": "零售",
    "Wholesale": "批发",
    "Presale": "预售",
    "Exchange": "换货",
}


def execute() -> None:
    _translate_channel_store()
    _translate_style()
    _translate_production_ticket()
    _translate_after_sales()
    _translate_warehouse_location()
    _translate_sales_order_fields()


def _translate_channel_store() -> None:
    _translate_field_values("Channel Store", "channel", CHANNEL_VALUE_MAP)
    _translate_field_values("Channel Store", "status", CHANNEL_STATUS_MAP)


def _translate_style() -> None:
    _translate_field_values("Style", "season", STYLE_SEASON_MAP)
    _translate_field_values("Style", "gender", STYLE_GENDER_MAP)
    _translate_field_values("Style", "launch_status", STYLE_LAUNCH_STATUS_MAP)
    _translate_field_values("Style", "sales_status", STYLE_SALES_STATUS_MAP)


def _translate_production_ticket() -> None:
    _translate_field_values("Production Ticket", "stage", PRODUCTION_STAGE_MAP)
    _translate_field_values("Production Ticket", "status", PRODUCTION_STATUS_MAP)
    _translate_field_values("Production Stage Log", "stage", PRODUCTION_STAGE_MAP)


def _translate_after_sales() -> None:
    _translate_field_values("After Sales Ticket", "ticket_type", AFTER_SALES_TICKET_TYPE_MAP)
    _translate_field_values("After Sales Ticket", "ticket_status", AFTER_SALES_TICKET_STATUS_MAP)
    _translate_field_values("After Sales Ticket", "priority", AFTER_SALES_PRIORITY_MAP)
    _translate_field_values("After Sales Ticket", "refund_status", REFUND_STATUS_MAP)
    _translate_field_values("After Sales Ticket", "channel", CHANNEL_VALUE_MAP)

    _translate_field_values("After Sales Item", "requested_action", AFTER_SALES_TICKET_TYPE_MAP)

    _translate_field_values("After Sales Log", "action_type", AFTER_SALES_LOG_ACTION_MAP)
    _translate_field_values("After Sales Log", "from_status", AFTER_SALES_TICKET_STATUS_MAP)
    _translate_field_values("After Sales Log", "to_status", AFTER_SALES_TICKET_STATUS_MAP)


def _translate_warehouse_location() -> None:
    _translate_field_values("Warehouse Location", "location_type", LOCATION_TYPE_MAP)


def _translate_sales_order_fields() -> None:
    _translate_field_values("Sales Order", "channel", CHANNEL_VALUE_MAP)
    _translate_field_values("Sales Order", "biz_type", SALES_ORDER_BIZ_TYPE_MAP)


def _translate_field_values(doctype: str, fieldname: str, mapping: dict[str, str]) -> None:
    if not frappe.db.exists("DocType", doctype):
        return

    meta = frappe.get_meta(doctype)
    if not meta.has_field(fieldname):
        return

    for source_value, target_value in mapping.items():
        rows = frappe.get_all(
            doctype,
            filters={fieldname: source_value},
            pluck="name",
            limit_page_length=0,
        )
        for name in rows:
            frappe.db.set_value(doctype, name, fieldname, target_value, update_modified=False)
