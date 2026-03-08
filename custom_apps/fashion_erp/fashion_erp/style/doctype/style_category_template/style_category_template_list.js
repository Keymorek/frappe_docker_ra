frappe.listview_settings["Style Category Template"] = {
	onload(listview) {
		if (!canManageStyleCategoryTemplateList(listview)) {
			return;
		}

		listview.page.add_inner_button("同步内置抖音类目模板", () => syncBuiltinStyleCategoryTemplatesFromList(listview));
	}
};

function canManageStyleCategoryTemplateList(listview) {
	if (listview && listview.page && listview.page.doctype === "Style Category Template") {
		return true;
	}
	return false;
}

function syncBuiltinStyleCategoryTemplatesFromList(listview) {
	frappe.call({
		method: "fashion_erp.style.doctype.style_category_template.style_category_template.sync_builtin_style_category_templates",
		freeze: true,
		freeze_message: __("同步内置类目模板中...")
	}).then((response) => {
		const payload = response.message || {};
		if (payload.message) {
			frappe.show_alert({ message: payload.message, indicator: payload.ok === false ? "orange" : "green" }, 5);
		}
		listview.refresh();
	});
}
