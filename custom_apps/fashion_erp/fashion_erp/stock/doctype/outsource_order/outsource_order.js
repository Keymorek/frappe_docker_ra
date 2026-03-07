frappe.ui.form.on("Outsource Order", {
	setup(frm) {
		if (frm.fields_dict.color) {
			frm.set_query("color", () => ({
				filters: {
					enabled: 1
				}
			}));
		}

		if (frm.fields_dict.craft_sheet) {
			frm.set_query("craft_sheet", () => {
				const filters = {};
				if (frm.doc.style) {
					filters.style = frm.doc.style;
				}
				return { filters };
			});
		}

		if (frm.fields_dict.materials && frm.fields_dict.materials.grid) {
			frm.fields_dict.materials.grid.get_field("item_code").get_query = function () {
				return {
					filters: [["Item", "item_usage_type", "in", ["面料", "辅料"]]]
				};
			};

			frm.fields_dict.materials.grid.get_field("default_location").get_query = function (doc, cdt, cdn) {
				const row = locals[cdt][cdn];
				const filters = {
					enabled: 1
				};
				if (row.warehouse) {
					filters.warehouse = row.warehouse;
				}
				return { filters };
			};
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

		if (frm.doc.craft_sheet) {
			frm.add_custom_button(__("打开工艺单"), () => {
				frappe.set_route("Form", "Craft Sheet", frm.doc.craft_sheet);
			});
		}

		frm.add_custom_button(__("创建到货单"), () => {
			createOutsourceReceipt(frm);
		});

		if (frm.doc.sample_ticket) {
			frm.add_custom_button(__("打开打样单"), () => {
				frappe.set_route("Form", "Sample Ticket", frm.doc.sample_ticket);
			});
		}

		if (frm.doc.order_status === "草稿") {
			frm.add_custom_button(__("下发外包单"), () => {
				runOutsourceAction(frm, "submit_order");
			});
		}

		if (frm.doc.order_status === "已下单") {
			frm.add_custom_button(__("开始生产"), () => {
				runOutsourceAction(frm, "start_order");
			});
		}

		if (["已下单", "生产中"].includes(frm.doc.order_status)) {
			frm.add_custom_button(__("完成外包单"), () => {
				runOutsourceAction(frm, "complete_order");
			});
		}

		if (!["已完成", "已取消"].includes(frm.doc.order_status)) {
			frm.add_custom_button(__("取消外包单"), () => {
				runOutsourceAction(frm, "cancel_order");
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

	craft_sheet(frm) {
		if (!frm.doc.craft_sheet) {
			return;
		}

		frappe.db.get_value(
			"Craft Sheet",
			frm.doc.craft_sheet,
			["style", "style_name", "item_template", "sample_ticket", "color", "color_name", "color_code"]
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
			if (row.sample_ticket) {
				frm.set_value("sample_ticket", row.sample_ticket);
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

frappe.ui.form.on("Outsource Order Material", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) {
			return;
		}

		frappe.db.get_value(
			"Item",
			row.item_code,
			["item_name", "item_usage_type", "stock_uom", "supply_warehouse", "default_location"]
		).then((response) => {
			const item = response.message || {};
			if (item.item_name) {
				frappe.model.set_value(cdt, cdn, "item_name", item.item_name);
			}
			if (item.item_usage_type) {
				frappe.model.set_value(cdt, cdn, "item_usage_type", item.item_usage_type);
			}
			if (item.stock_uom) {
				frappe.model.set_value(cdt, cdn, "uom", item.stock_uom);
			}
			if (item.supply_warehouse && !row.warehouse) {
				frappe.model.set_value(cdt, cdn, "warehouse", item.supply_warehouse);
			}
			if (item.default_location && !row.default_location) {
				frappe.model.set_value(cdt, cdn, "default_location", item.default_location);
			}
		});
	}
});

function runOutsourceAction(frm, method, args = {}) {
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

function createOutsourceReceipt(frm) {
	frappe.new_doc("Outsource Receipt", {
		outsource_order: frm.doc.name,
		supplier: frm.doc.supplier || "",
		style: frm.doc.style || "",
		style_name: frm.doc.style_name || "",
		item_template: frm.doc.item_template || "",
		craft_sheet: frm.doc.craft_sheet || "",
		sample_ticket: frm.doc.sample_ticket || "",
		color: frm.doc.color || "",
		color_name: frm.doc.color_name || "",
		color_code: frm.doc.color_code || "",
		warehouse: frm.doc.receipt_warehouse || ""
	});
}
