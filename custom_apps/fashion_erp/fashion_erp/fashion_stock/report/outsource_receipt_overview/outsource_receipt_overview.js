frappe.query_reports["Outsource Receipt Overview"] = {
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
			fieldname: "receipt_status",
			label: __("到货状态"),
			fieldtype: "Select",
			options: "\n草稿\n已收货\n已入库\n已质检\n已取消"
		},
		{
			fieldname: "company",
			label: __("公司"),
			fieldtype: "Link",
			options: "Company"
		}
	]
};

