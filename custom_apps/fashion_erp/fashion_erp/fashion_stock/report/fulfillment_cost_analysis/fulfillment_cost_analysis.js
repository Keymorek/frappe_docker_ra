frappe.query_reports["Fulfillment Cost Analysis"] = {
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
			fieldname: "company",
			label: __("公司"),
			fieldtype: "Link",
			options: "Company"
		},
		{
			fieldname: "customer",
			label: __("客户"),
			fieldtype: "Link",
			options: "Customer"
		}
	]
};

