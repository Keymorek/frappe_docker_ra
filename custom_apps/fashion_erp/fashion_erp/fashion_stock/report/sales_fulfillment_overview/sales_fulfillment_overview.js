frappe.query_reports["Sales Fulfillment Overview"] = {
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
			fieldname: "channel",
			label: __("渠道"),
			fieldtype: "Data"
		},
		{
			fieldname: "channel_store",
			label: __("渠道店铺"),
			fieldtype: "Link",
			options: "Channel Store"
		},
		{
			fieldname: "fulfillment_status",
			label: __("履约状态"),
			fieldtype: "Select",
			options: "\n待处理\n已锁库存\n拣货中\n已拣货\n打包中\n待发货\n部分发货\n已发货\n售后中\n已签收\n已关闭\n已取消"
		},
		{
			fieldname: "customer",
			label: __("客户"),
			fieldtype: "Link",
			options: "Customer"
		}
	]
};

