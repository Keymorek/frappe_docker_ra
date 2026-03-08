frappe.query_reports["Production Board"] = {
	filters: [
		{
			fieldname: "style",
			label: __("款号"),
			fieldtype: "Link",
			options: "Style"
		},
		{
			fieldname: "supplier",
			label: __("供应商"),
			fieldtype: "Link",
			options: "Supplier"
		},
		{
			fieldname: "stage",
			label: __("阶段"),
			fieldtype: "Select",
			options: "\n计划\n裁剪\n车缝\n后整\n包装\n完成"
		},
		{
			fieldname: "status",
			label: __("状态"),
			fieldtype: "Select",
			options: "\n草稿\n进行中\n暂停\n已完成\n已取消"
		},
		{
			fieldname: "planned_date_from",
			label: __("计划开始从"),
			fieldtype: "Date"
		},
		{
			fieldname: "planned_date_to",
			label: __("计划结束至"),
			fieldtype: "Date"
		},
		{
			fieldname: "only_open",
			label: __("只看未完成"),
			fieldtype: "Check",
			default: 0
		},
		{
			fieldname: "only_overdue",
			label: __("只看延期"),
			fieldtype: "Check",
			default: 0
		}
	]
};
