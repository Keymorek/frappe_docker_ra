frappe.query_reports["Style Inventory Overview"] = {
	filters: [
		{
			fieldname: "style",
			label: __("款号"),
			fieldtype: "Link",
			options: "Style"
		},
		{
			fieldname: "brand",
			label: __("品牌"),
			fieldtype: "Link",
			options: "Brand"
		},
		{
			fieldname: "item_group",
			label: __("物料组"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname: "warehouse",
			label: __("仓库"),
			fieldtype: "Link",
			options: "Warehouse"
		},
		{
			fieldname: "include_zero_stock",
			label: __("包含零库存"),
			fieldtype: "Check",
			default: 0
		}
	]
};

