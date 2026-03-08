frappe.query_reports["Outsource Estimated Cost Analysis"] = {
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
			fieldname: "supplier",
			label: __("外包工厂"),
			fieldtype: "Link",
			options: "Supplier"
		},
		{
			fieldname: "style",
			label: __("款号"),
			fieldtype: "Link",
			options: "Style"
		},
		{
			fieldname: "order_status",
			label: __("外包单状态"),
			fieldtype: "Select",
			options: "\n草稿\n已下单\n生产中\n已完成\n已取消"
		},
		{
			fieldname: "overdue_only",
			label: __("只看逾期"),
			fieldtype: "Check",
			default: 0
		},
		{
			fieldname: "include_closed_orders",
			label: __("包含已完成/已取消"),
			fieldtype: "Check",
			default: 0
		}
	]
};

