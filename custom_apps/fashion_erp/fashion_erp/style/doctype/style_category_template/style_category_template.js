frappe.ui.form.on("Style Category Template", {
	refresh(frm) {
		if (!canManageStyleCategoryTemplates(frm)) {
			return;
		}

		frm.add_custom_button("同步内置抖音类目模板", () => syncBuiltinStyleCategoryTemplates(frm), "工具");
	}
});

function canManageStyleCategoryTemplates(frm) {
	if (typeof frm.has_perm === "function") {
		return frm.has_perm("write");
	}
	return (frm.perm || []).some((perm) => Boolean(perm.write));
}

function syncBuiltinStyleCategoryTemplates(frm) {
	frappe.call({
		method: "fashion_erp.style.doctype.style_category_template.style_category_template.sync_builtin_style_category_templates",
		freeze: true,
		freeze_message: __("同步内置类目模板中...")
	}).then((response) => {
		const payload = response.message || {};
		if (payload.message) {
			frappe.show_alert({ message: payload.message, indicator: payload.ok === false ? "orange" : "green" }, 5);
		}
		if (frm.is_new()) {
			frappe.set_route("List", "Style Category Template");
			return;
		}
		frm.reload_doc();
	});
}
