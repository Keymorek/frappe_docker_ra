frappe.ui.form.on("Craft Sheet", {
	setup(frm) {
		if (frm.fields_dict.color) {
			frm.set_query("color", () => ({
				filters: {
					enabled: 1
				}
			}));
		}
	},

	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (frm.doc.style) {
			frm.add_custom_button(__("打开款号"), () => {
				frappe.set_route("Form", "Style", frm.doc.style);
			});
		}

		if (frm.doc.sample_ticket) {
			frm.add_custom_button(__("打开打样单"), () => {
				frappe.set_route("Form", "Sample Ticket", frm.doc.sample_ticket);
			});
		}

		if (frm.doc.sheet_status === "已发布") {
			frm.add_custom_button(__("创建外包单"), () => {
				createOutsourceOrder(frm);
			});
		}

		if (frm.doc.sheet_status === "草稿") {
			frm.add_custom_button(__("发布工艺单"), () => {
				runCraftSheetAction(frm, "publish_sheet");
			});
		}

		if (frm.doc.sheet_status !== "已作废") {
			frm.add_custom_button(__("创建新版本"), () => {
				prepareNextVersion(frm);
			});
		}

		if (frm.doc.sheet_status !== "已作废") {
			frm.add_custom_button(__("作废工艺单"), () => {
				runCraftSheetAction(frm, "void_sheet");
			});
		}
	},

	style(frm) {
		if (!frm.doc.style) {
			return;
		}

		frappe.db.get_value("Style", frm.doc.style, ["style_name", "item_template"]).then((response) => {
			const row = response.message || {};
			if (row.style_name) {
				frm.set_value("style_name", row.style_name);
			}
			if (row.item_template) {
				frm.set_value("item_template", row.item_template);
			}
		});
	},

	sample_ticket(frm) {
		if (!frm.doc.sample_ticket) {
			return;
		}

		frappe.db.get_value(
			"Sample Ticket",
			frm.doc.sample_ticket,
			["style", "style_name", "item_template", "color", "color_name", "color_code"]
		).then((response) => {
			const row = response.message || {};
			if (row.style) {
				frm.set_value("style", row.style);
			}
			if (row.style_name) {
				frm.set_value("style_name", row.style_name);
			}
			if (row.item_template) {
				frm.set_value("item_template", row.item_template);
			}
			if (row.color) {
				frm.set_value("color", row.color);
			}
			if (row.color_name) {
				frm.set_value("color_name", row.color_name);
			}
			if (row.color_code) {
				frm.set_value("color_code", row.color_code);
			}
		});
	},

	color(frm) {
		if (!frm.doc.color) {
			frm.set_value("color_name", "");
			frm.set_value("color_code", "");
			return;
		}

		frappe.db.get_value("Color", frm.doc.color, ["color_name", "color_group"]).then((response) => {
			const colorDoc = response.message || {};
			frm.set_value("color_name", colorDoc.color_name || frm.doc.color);

			if (!colorDoc.color_group) {
				frm.set_value("color_code", "");
				return null;
			}

			return frappe.db.get_value("Color Group", colorDoc.color_group, "color_group_code").then((groupResponse) => {
				const groupDoc = groupResponse.message || {};
				frm.set_value("color_code", groupDoc.color_group_code || "");
			});
		});
	}
});

function runCraftSheetAction(frm, method, args = {}) {
	const invoke = () => frm.call(method, args).then((response) => {
		const payload = response.message || {};
		if (payload.message) {
			frappe.show_alert({
				message: payload.message,
				indicator: "green"
			});
		}
		return frm.reload_doc();
	});

	if (frm.is_dirty()) {
		return frm.save().then(() => invoke());
	}

	return invoke();
}

function prepareNextVersion(frm) {
	const invoke = () => frm.call("prepare_next_version").then((response) => {
		const payload = response.message || {};
		frappe.new_doc("Craft Sheet", payload.defaults || {});
	});

	if (frm.is_dirty()) {
		return frm.save().then(() => invoke());
	}

	return invoke();
}

function createOutsourceOrder(frm) {
	frappe.new_doc("Outsource Order", {
		style: frm.doc.style,
		style_name: frm.doc.style_name || "",
		item_template: frm.doc.item_template || "",
		craft_sheet: frm.doc.name,
		sample_ticket: frm.doc.sample_ticket || "",
		color: frm.doc.color || "",
		color_name: frm.doc.color_name || "",
		color_code: frm.doc.color_code || ""
	});
}
