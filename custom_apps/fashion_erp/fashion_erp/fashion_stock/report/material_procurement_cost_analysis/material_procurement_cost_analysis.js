frappe.query_reports["Material Procurement Cost Analysis"] = {
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
			label: __("供应商"),
			fieldtype: "Link",
			options: "Supplier"
		},
		{
			fieldname: "supply_order_type",
			label: __("采购用途"),
			fieldtype: "Select",
			options: "\n原辅料采购\n包装耗材采购\n综合采购"
		},
		{
			fieldname: "item_usage_type",
			label: __("物料用途"),
			fieldtype: "Select",
			options: "\n成品\n面料\n辅料\n包装耗材\n其他"
		},
		{
			fieldname: "supply_context",
			label: __("采购场景"),
			fieldtype: "Select",
			options: "\n常备采购\n打样采购\n外包备货\n包装履约"
		},
		{
			fieldname: "reference_outsource_order",
			label: __("关联外包单"),
			fieldtype: "Link",
			options: "Outsource Order"
		}
	]
};

