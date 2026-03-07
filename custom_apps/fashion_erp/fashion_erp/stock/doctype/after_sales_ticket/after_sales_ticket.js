frappe.ui.form.on("After Sales Ticket", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (frm.doc.replacement_sales_order) {
			frm.add_custom_button(__("打开补发订单"), () => {
				frappe.set_route("Form", "Sales Order", frm.doc.replacement_sales_order);
			});
		}

		if (["已收货", "质检中", "待处理", "待退款", "待补发"].includes(frm.doc.ticket_status)) {
			frm.add_custom_button(__("生成库存凭证"), () => {
				openReturnStockEntryDialog(frm);
			});
		}

		if (frm.doc.ticket_status === "新建" && ["退货退款", "换货", "维修"].includes(frm.doc.ticket_type)) {
			frm.add_custom_button(__("待客户退回"), () => {
				runTicketAction(frm, "move_to_waiting_return");
			});
		}

		if (["新建", "待退回"].includes(frm.doc.ticket_status)) {
			frm.add_custom_button(__("收货"), () => {
				openReceiveDialog(frm);
			});
		}

		if (frm.doc.ticket_status === "已收货") {
			frm.add_custom_button(__("开始质检"), () => {
				runTicketAction(frm, "start_inspection");
			});
		}

		if (["新建", "已收货", "质检中", "待处理"].includes(frm.doc.ticket_status)) {
			frm.add_custom_button(__("应用处理结论"), () => {
				openDecisionDialog(frm);
			});
		}

		if (frm.doc.ticket_status === "待退款") {
			frm.add_custom_button(__("确认退款"), () => {
				openRefundDialog(frm);
			});
		}

		if (
			["待补发", "待处理"].includes(frm.doc.ticket_status) &&
			["换货", "补发", "维修"].includes(frm.doc.ticket_type) &&
			!frm.doc.replacement_sales_order
		) {
			frm.add_custom_button(__("创建补发订单"), () => {
				openReplacementOrderDialog(frm);
			});
		}

		if (["待退款", "待补发", "待处理"].includes(frm.doc.ticket_status)) {
			frm.add_custom_button(__("关闭工单"), () => {
				runTicketAction(frm, "close_ticket");
			});
		}

		if (!["已关闭", "已取消"].includes(frm.doc.ticket_status)) {
			frm.add_custom_button(__("取消工单"), () => {
				runTicketAction(frm, "cancel_ticket");
			});
		}
	},

	setup(frm) {
		if (frm.fields_dict.warehouse_location) {
			frm.set_query("warehouse_location", () => {
				const filters = { enabled: 1 };
				if (frm.doc.warehouse) {
					filters.warehouse = frm.doc.warehouse;
				}
				return { filters };
			});
		}

		const items_grid = frm.fields_dict.items && frm.fields_dict.items.grid;
		if (!items_grid) {
			return;
		}

		["return_reason", "return_disposition", "inventory_status_from", "inventory_status_to"].forEach((fieldname) => {
			items_grid.get_field(fieldname).get_query = function () {
				return {
					filters: {
						enabled: 1
					}
				};
			};
		});

		items_grid.get_field("sales_order_item_ref").get_query = function () {
			const filters = {};
			if (frm.doc.sales_order) {
				filters.parent = frm.doc.sales_order;
			}
			return { filters };
		};

		items_grid.get_field("delivery_note_item_ref").get_query = function () {
			const filters = {};
			if (frm.doc.delivery_note) {
				filters.parent = frm.doc.delivery_note;
			}
			return { filters };
		};
	},

	sales_order(frm) {
		if (!frm.doc.sales_order) {
			return;
		}

		frappe.db.get_value(
			"Sales Order",
			frm.doc.sales_order,
			["customer", "customer_name", "channel", "channel_store", "external_order_id"]
		).then((response) => {
			const row = response.message || {};
			if (row.customer) {
				frm.set_value("customer", row.customer);
			}
			if (!frm.doc.buyer_name && row.customer_name) {
				frm.set_value("buyer_name", row.customer_name);
			}
			if (row.channel) {
				frm.set_value("channel", row.channel);
			}
			if (row.channel_store) {
				frm.set_value("channel_store", row.channel_store);
			}
			if (row.external_order_id) {
				frm.set_value("external_order_id", row.external_order_id);
			}
		});
	},

	warehouse(frm) {
		if (!frm.doc.warehouse_location) {
			return;
		}

		frappe.db.get_value("Warehouse Location", frm.doc.warehouse_location, "warehouse").then((response) => {
			const row = response.message || {};
			if (row.warehouse && frm.doc.warehouse && row.warehouse !== frm.doc.warehouse) {
				frm.set_value("warehouse_location", "");
			}
		});
	}
});

frappe.ui.form.on("After Sales Item", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code) {
			return;
		}

		frappe.db.get_value("Item", row.item_code, ["style", "color_code", "size_code"]).then((response) => {
			const item = response.message || {};
			frappe.model.set_value(cdt, cdn, "style", item.style || "");
			frappe.model.set_value(cdt, cdn, "color_code", item.color_code || "");
			frappe.model.set_value(cdt, cdn, "size_code", item.size_code || "");
		});
	},

	sales_order_item_ref(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.sales_order_item_ref) {
			return;
		}

		frappe.db.get_value(
			"Sales Order Item",
			row.sales_order_item_ref,
			["parent", "item_code", "style", "color_code", "size_code"]
		).then((response) => {
			const item = response.message || {};
			if (!frm.doc.sales_order && item.parent) {
				frm.set_value("sales_order", item.parent);
			}
			if (item.item_code) {
				frappe.model.set_value(cdt, cdn, "item_code", item.item_code);
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

	delivery_note_item_ref(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.delivery_note_item_ref) {
			return;
		}

		frappe.db.get_value(
			"Delivery Note Item",
			row.delivery_note_item_ref,
			["parent", "item_code", "against_sales_order"]
		).then((response) => {
			const item = response.message || {};
			if (!frm.doc.delivery_note && item.parent) {
				frm.set_value("delivery_note", item.parent);
			}
			if (!frm.doc.sales_order && item.against_sales_order) {
				frm.set_value("sales_order", item.against_sales_order);
			}
			if (item.item_code) {
				frappe.model.set_value(cdt, cdn, "item_code", item.item_code);
			}
		});
	},

	return_disposition(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.return_disposition) {
			return;
		}

		frappe.db.get_value(
			"Return Disposition",
			row.return_disposition,
			"target_inventory_status"
		).then((response) => {
			const disposition = response.message || {};
			if (disposition.target_inventory_status) {
				frappe.model.set_value(cdt, cdn, "inventory_status_to", disposition.target_inventory_status);
			}
		});
	}
});

function runTicketAction(frm, method, args = {}) {
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

function callTicketMethod(frm, method, args = {}) {
	const invoke = () => frm.call(method, args).then((response) => {
		const payload = response.message || {};
		if (payload.message) {
			frappe.show_alert({
				message: payload.message,
				indicator: "green"
			});
		}
		return payload;
	});

	if (frm.is_dirty()) {
		return frm.save().then(() => invoke());
	}

	return invoke();
}

function openReceiveDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("售后收货"),
		fields: [
			{
				fieldname: "warehouse",
				fieldtype: "Link",
				label: "仓库",
				options: "Warehouse",
				default: frm.doc.warehouse || ""
			},
			{
				fieldname: "warehouse_location",
				fieldtype: "Link",
				label: "仓库库位",
				options: "Warehouse Location",
				default: frm.doc.warehouse_location || "",
				get_query: () => {
					const filters = { enabled: 1 };
					if (dialog.get_value("warehouse")) {
						filters.warehouse = dialog.get_value("warehouse");
					}
					return { filters };
				}
			},
			{
				fieldname: "logistics_company",
				fieldtype: "Data",
				label: "物流公司",
				default: frm.doc.logistics_company || ""
			},
			{
				fieldname: "tracking_no",
				fieldtype: "Data",
				label: "运单号",
				default: frm.doc.tracking_no || ""
			},
			{
				fieldname: "received_at",
				fieldtype: "Datetime",
				label: "收货时间",
				default: frappe.datetime.now_datetime()
			},
			{
				fieldname: "note",
				fieldtype: "Small Text",
				label: "备注"
			}
		]
	});

	dialog.set_primary_action(__("确认"), () => {
		const values = dialog.get_values();
		if (!values) {
			return;
		}

		runTicketAction(frm, "receive_ticket", values).then(() => {
			dialog.hide();
		});
	});

	dialog.show();
}

function openDecisionDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("应用处理结论"),
		fields: [
			{
				fieldname: "return_disposition",
				fieldtype: "Link",
				label: "退货处理结果",
				options: "Return Disposition",
				default: frm.doc.return_disposition || "",
				get_query: () => ({ filters: { enabled: 1 } })
			},
			{
				fieldname: "refund_amount",
				fieldtype: "Currency",
				label: "退款金额",
				default: frm.doc.refund_amount || 0
			},
			{
				fieldname: "note",
				fieldtype: "Small Text",
				label: "备注"
			}
		]
	});

	dialog.set_primary_action(__("应用"), () => {
		const values = dialog.get_values();
		if (!values) {
			return;
		}

		runTicketAction(frm, "apply_decision", values).then(() => {
			dialog.hide();
		});
	});

	dialog.show();
}

function openRefundDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("确认退款"),
		fields: [
			{
				fieldname: "refund_amount",
				fieldtype: "Currency",
				label: "退款金额",
				reqd: 1,
				default: frm.doc.refund_amount || 0
			},
			{
				fieldname: "note",
				fieldtype: "Small Text",
				label: "备注"
			}
		]
	});

	dialog.set_primary_action(__("确认"), () => {
		const values = dialog.get_values();
		if (!values) {
			return;
		}

		runTicketAction(frm, "approve_refund", values).then(() => {
			dialog.hide();
		});
	});

	dialog.show();
}

function openReplacementOrderDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("生成补发订单草稿"),
		fields: [
			{
				fieldname: "company",
				fieldtype: "Link",
				label: "公司",
				options: "Company"
			},
			{
				fieldname: "delivery_date",
				fieldtype: "Date",
				label: "交付日期"
			},
			{
				fieldname: "set_warehouse",
				fieldtype: "Link",
				label: "仓库",
				options: "Warehouse",
				default: frm.doc.warehouse || ""
			},
			{
				fieldname: "note",
				fieldtype: "Small Text",
				label: "备注"
			}
		]
	});

	dialog.set_primary_action(__("打开草稿"), () => {
		const values = dialog.get_values();
		if (!values) {
			return;
		}

		callTicketMethod(frm, "prepare_replacement_order", values).then((payload) => {
			dialog.hide();
			openPreparedSalesOrder(payload.payload || {});
		});
	});

	dialog.show();
}

function openReturnStockEntryDialog(frm) {
	const defaultMode = ["待退款", "待补发", "待处理"].includes(frm.doc.ticket_status)
		? "最终处理"
		: "待检入库";
	const dialog = new frappe.ui.Dialog({
		title: __("生成库存凭证草稿"),
		fields: [
			{
				fieldname: "entry_mode",
				fieldtype: "Select",
				label: "处理模式",
				reqd: 1,
				options: "待检入库\n最终处理",
				default: defaultMode
			},
			{
				fieldname: "company",
				fieldtype: "Link",
				label: "公司",
				options: "Company"
			},
			{
				fieldname: "purpose",
				fieldtype: "Select",
				label: "用途",
				reqd: 1,
				options: "物料入库\n物料转移",
				default: "物料入库"
			},
			{
				fieldname: "source_warehouse",
				fieldtype: "Link",
				label: "来源仓库",
				options: "Warehouse"
			},
			{
				fieldname: "target_warehouse",
				fieldtype: "Link",
				label: "目标仓库",
				options: "Warehouse",
				default: frm.doc.warehouse || ""
			},
			{
				fieldname: "remark",
				fieldtype: "Small Text",
				label: "备注"
			}
		]
	});

	dialog.set_primary_action(__("打开草稿"), () => {
		const values = dialog.get_values();
		if (!values) {
			return;
		}

		callTicketMethod(frm, "prepare_return_stock_entry", values).then((payload) => {
			dialog.hide();
			openPreparedStockEntry(payload.payload || {});
		});
	});

	dialog.show();
	if (dialog.fields_dict.purpose.$input) {
		dialog.fields_dict.purpose.$input.on("change", () => {
			toggleReturnStockEntryWarehouseFields(dialog);
		});
	}
	toggleReturnStockEntryWarehouseFields(dialog);
}

function toggleReturnStockEntryWarehouseFields(dialog) {
	const purpose = dialog.get_value("purpose");
	const sourceRequired = purpose === "物料转移";

	dialog.set_df_property("source_warehouse", "reqd", sourceRequired ? 1 : 0);
	if (!sourceRequired) {
		dialog.set_value("source_warehouse", "");
	}
}

function openPreparedSalesOrder(payload) {
	frappe.new_doc("Sales Order", {}, (doc) => {
		Object.keys(payload || {}).forEach((key) => {
			if (key === "doctype" || key === "items") {
				return;
			}
			doc[key] = payload[key];
		});

		(payload.items || []).forEach((item) => {
			const row = frappe.model.add_child(doc, "Sales Order Item", "items");
			Object.keys(item).forEach((key) => {
				if (key === "doctype") {
					return;
				}
				row[key] = item[key];
			});
		});
	});
}

function openPreparedStockEntry(payload) {
	frappe.new_doc("Stock Entry", {}, (doc) => {
		Object.keys(payload || {}).forEach((key) => {
			if (key === "doctype" || key === "items") {
				return;
			}
			doc[key] = payload[key];
		});

		(payload.items || []).forEach((item) => {
			const row = frappe.model.add_child(doc, "Stock Entry Detail", "items");
			Object.keys(item).forEach((key) => {
				if (key === "doctype") {
					return;
				}
				row[key] = item[key];
			});
		});
	});
}
