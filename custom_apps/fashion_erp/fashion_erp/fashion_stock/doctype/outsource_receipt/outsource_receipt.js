frappe.ui.form.on("Outsource Receipt", {
	setup(frm) {
		if (frm.fields_dict.outsource_order) {
			frm.set_query("outsource_order", () => ({
				filters: {
					order_status: ["in", ["已下单", "生产中", "已完成"]]
				}
			}));
		}

		if (frm.fields_dict.warehouse_location) {
			frm.set_query("warehouse_location", () => {
				const filters = { enabled: 1 };
				if (frm.doc.warehouse) {
					filters.warehouse = frm.doc.warehouse;
				}
				return { filters };
			});
		}

		if (frm.fields_dict.items && frm.fields_dict.items.grid) {
			frm.fields_dict.items.grid.get_field("item_code").get_query = function (doc) {
				const filters = [["Item", "item_usage_type", "=", "成品"]];
				if (doc.style) {
					filters.push(["Item", "style", "=", doc.style]);
				}
				if (doc.color_code) {
					filters.push(["Item", "color_code", "=", doc.color_code]);
				}
				return { filters };
			};
		}
	},

	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (frm.doc.outsource_order) {
			frm.add_custom_button(__("打开外包单"), () => {
				frappe.set_route("Form", "Outsource Order", frm.doc.outsource_order);
			});
		}

		if (frm.doc.qc_stock_entry) {
			frm.add_custom_button(__("打开入库凭证"), () => {
				frappe.set_route("Form", "Stock Entry", frm.doc.qc_stock_entry);
			});
		}

		if (frm.doc.final_stock_entry) {
			frm.add_custom_button(__("打开质检凭证"), () => {
				frappe.set_route("Form", "Stock Entry", frm.doc.final_stock_entry);
			});
		}

		if (frm.doc.receipt_status === "草稿") {
			frm.add_custom_button(__("确认收货"), () => {
				runOutsourceReceiptAction(frm, "confirm_receipt");
			});
		}

		if (frm.doc.receipt_status === "已收货") {
			frm.add_custom_button(__("生成待检入库草稿"), () => {
				prepareQcStockEntry(frm);
			});
			frm.add_custom_button(__("确认已入库"), () => {
				openMarkStockedDialog(frm);
			});
		}

		if (frm.doc.receipt_status === "已入库") {
			frm.add_custom_button(__("生成质检落账草稿"), () => {
				prepareFinalStockEntry(frm);
			});
			frm.add_custom_button(__("确认质检完成"), () => {
				openCompleteQcDialog(frm);
			});
		}

		if (!["已入库", "已质检", "已取消"].includes(frm.doc.receipt_status)) {
			frm.add_custom_button(__("取消到货单"), () => {
				runOutsourceReceiptAction(frm, "cancel_receipt");
			});
		}
	},

	outsource_order(frm) {
		if (!frm.doc.outsource_order) {
			return;
		}

		frappe.db.get_value(
			"Outsource Order",
			frm.doc.outsource_order,
			["supplier", "style", "style_name", "item_template", "craft_sheet", "sample_ticket", "color", "color_name", "color_code", "receipt_warehouse"]
		).then((response) => {
			const row = response.message || {};
			frm.set_value("supplier", row.supplier || "");
			frm.set_value("style", row.style || "");
			frm.set_value("style_name", row.style_name || "");
			frm.set_value("item_template", row.item_template || "");
			frm.set_value("craft_sheet", row.craft_sheet || "");
			frm.set_value("sample_ticket", row.sample_ticket || "");
			frm.set_value("color", row.color || "");
			frm.set_value("color_name", row.color_name || "");
			frm.set_value("color_code", row.color_code || "");
			if (!frm.doc.warehouse && row.receipt_warehouse) {
				frm.set_value("warehouse", row.receipt_warehouse);
			}
		});
	}
});

frappe.ui.form.on("Outsource Receipt Item", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) {
			return;
		}

		frappe.db.get_value(
			"Item",
			row.item_code,
			["item_name", "style", "color_code", "size_code"]
		).then((response) => {
			const item = response.message || {};
			if (item.item_name) {
				frappe.model.set_value(cdt, cdn, "item_name", item.item_name);
			}
			if (item.style) {
				frappe.model.set_value(cdt, cdn, "style", item.style);
			}
			if (item.color_code) {
				frappe.model.set_value(cdt, cdn, "color_code", item.color_code);
			}
			if (item.size_code) {
				frappe.model.set_value(cdt, cdn, "size_code", item.size_code);
			}
		});
	},

	qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row) {
			return;
		}

		const allocated = Number(row.sellable_qty || 0) + Number(row.repair_qty || 0) + Number(row.defective_qty || 0) + Number(row.frozen_qty || 0);
		if (allocated === 0 && Number(row.qty || 0) > 0) {
			frappe.model.set_value(cdt, cdn, "sellable_qty", row.qty);
		}
	}
});

function runOutsourceReceiptAction(frm, method, args = {}) {
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

function prepareQcStockEntry(frm) {
	const invoke = () => frm.call("prepare_qc_stock_entry").then((response) => {
		const payload = response.message || {};
		frappe.new_doc("Stock Entry", payload.payload || {});
	});

	if (frm.is_dirty()) {
		return frm.save().then(() => invoke());
	}

	return invoke();
}

function prepareFinalStockEntry(frm) {
	const invoke = () => frm.call("prepare_final_stock_entry").then((response) => {
		const payload = response.message || {};
		frappe.new_doc("Stock Entry", payload.payload || {});
	});

	if (frm.is_dirty()) {
		return frm.save().then(() => invoke());
	}

	return invoke();
}

function openMarkStockedDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("确认已入库"),
		fields: [
			{
				fieldname: "stock_entry_ref",
				fieldtype: "Link",
				label: "入库凭证",
				options: "Stock Entry",
				default: frm.doc.qc_stock_entry || ""
			},
			{
				fieldname: "note",
				fieldtype: "Small Text",
				label: "备注"
			}
		],
		primary_action_label: __("确认"),
		primary_action(values) {
			runOutsourceReceiptAction(frm, "mark_stocked", values).then(() => dialog.hide());
		}
	});

	dialog.show();
}

function openCompleteQcDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("确认质检完成"),
		fields: [
			{
				fieldname: "final_stock_entry_ref",
				fieldtype: "Link",
				label: "质检落账凭证",
				options: "Stock Entry",
				default: frm.doc.final_stock_entry || ""
			},
			{
				fieldname: "note",
				fieldtype: "Small Text",
				label: "备注"
			}
		],
		primary_action_label: __("确认"),
		primary_action(values) {
			runOutsourceReceiptAction(frm, "complete_qc", values).then(() => dialog.hide());
		}
	});

	dialog.show();
}
