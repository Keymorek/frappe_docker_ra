frappe.ui.form.on("Sample Ticket", {
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

		if (["新建", "需返修"].includes(frm.doc.sample_status)) {
			frm.add_custom_button(__("下发打样"), () => {
				runSampleAction(frm, "submit_ticket");
			});
		}

		if (frm.doc.sample_status === "已下发") {
			frm.add_custom_button(__("开始打样"), () => {
				runSampleAction(frm, "start_ticket");
			});
		}

		if (frm.doc.sample_status === "打样中") {
			frm.add_custom_button(__("提交评审"), () => {
				runSampleAction(frm, "submit_for_review");
			});
		}

		if (frm.doc.sample_status === "待评审") {
			frm.add_custom_button(__("要求返修"), () => {
				runSampleAction(frm, "request_revision");
			});
			frm.add_custom_button(__("确认样品"), () => {
				openConfirmDialog(frm);
			});
		}

		if (!["已确认", "已取消"].includes(frm.doc.sample_status)) {
			frm.add_custom_button(__("取消打样"), () => {
				runSampleAction(frm, "cancel_ticket");
			});
		}
	},

	style(frm) {
		if (!frm.doc.style) {
			return;
		}

		frappe.db.get_value(
			"Style",
			frm.doc.style,
			["style_name", "item_template"]
		).then((response) => {
			const row = response.message || {};
			if (row.style_name) {
				frm.set_value("style_name", row.style_name);
			}
			if (row.item_template) {
				frm.set_value("item_template", row.item_template);
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

function runSampleAction(frm, method, args = {}) {
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

function openConfirmDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("确认样品"),
		fields: [
			{
				fieldname: "actual_cost",
				fieldtype: "Currency",
				label: "实际成本",
				default: frm.doc.actual_cost || 0
			},
			{
				fieldname: "note",
				fieldtype: "Small Text",
				label: "备注"
			}
		],
		primary_action_label: __("确认"),
		primary_action(values) {
			runSampleAction(frm, "confirm_ticket", values).then(() => dialog.hide());
		}
	});

	dialog.show();
}
