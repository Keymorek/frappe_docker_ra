frappe.query_reports["Material Supply Overview"] = {
	filters: [
		{
			fieldname: "style",
			label: __("款号"),
			fieldtype: "Link",
			options: "Style"
		},
		{
			fieldname: "supplier",
			label: __("外包工厂"),
			fieldtype: "Link",
			options: "Supplier"
		},
		{
			fieldname: "order_status",
			label: __("外包单状态"),
			fieldtype: "Select",
			options: "\n草稿\n已下单\n生产中\n已完成\n已取消"
		},
		{
			fieldname: "item_code",
			label: __("物料"),
			fieldtype: "Link",
			options: "Item"
		},
		{
			fieldname: "supply_status",
			label: __("供料状态"),
			fieldtype: "Select",
			options: "\n已覆盖\n待备货\n待发料\n需采购"
		},
		{
			fieldname: "include_closed_orders",
			label: __("包含已完成/已取消"),
			fieldtype: "Check",
			default: 0
		}
	]
};

