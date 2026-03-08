frappe.query_reports["After Sales Overview"] = {
	filters: [
		{
			fieldname: "date_from",
			label: __("开始日期"),
			fieldtype: "Date"
		},
		{
			fieldname: "date_to",
			label: __("结束日期"),
			fieldtype: "Date"
		},
		{
			fieldname: "ticket_type",
			label: __("工单类型"),
			fieldtype: "Select",
			options: "\n仅退款\n退货退款\n换货\n补发\n维修\n投诉"
		},
		{
			fieldname: "ticket_status",
			label: __("工单状态"),
			fieldtype: "Select",
			options: "\n新建\n待退回\n已收货\n质检中\n待处理\n待退款\n待补发\n已关闭\n已取消"
		},
		{
			fieldname: "channel_store",
			label: __("渠道店铺"),
			fieldtype: "Link",
			options: "Channel Store"
		},
		{
			fieldname: "handler_user",
			label: __("处理人"),
			fieldtype: "Link",
			options: "User"
		}
	]
};

