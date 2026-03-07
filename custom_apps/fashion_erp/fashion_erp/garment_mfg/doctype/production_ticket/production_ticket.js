frappe.ui.form.on("Production Ticket", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (!["已完成", "已取消"].includes(frm.doc.status)) {
			frm.add_custom_button(__("新增阶段日志"), () => {
				openStageLogDialog(frm);
			});
		}

		frm.add_custom_button(__("生成库存凭证"), () => {
			openStockEntryDialog(frm);
		});

		if (frm.doc.bom_no) {
			frm.add_custom_button(__("同步物料清单"), () => {
				runTicketAction(frm, "sync_bom");
			});

			frm.add_custom_button(__("打开物料清单"), () => {
				frappe.set_route("Form", "BOM", frm.doc.bom_no);
			});
		} else {
			frm.add_custom_button(__("创建物料清单"), () => {
				openBomDialog(frm);
			});
		}

		if (frm.doc.work_order) {
			frm.add_custom_button(__("同步生产工单"), () => {
				runTicketAction(frm, "sync_work_order");
			});

			frm.add_custom_button(__("打开生产工单"), () => {
				frappe.set_route("Form", "Work Order", frm.doc.work_order);
			});
		} else if (frm.doc.bom_no) {
			frm.add_custom_button(__("创建生产工单"), () => {
				openWorkOrderDialog(frm);
			});
		}

		if (frm.doc.status === "草稿") {
			frm.add_custom_button(__("开始"), () => {
				runTicketAction(frm, "start_ticket");
			});
		}

		if (!["已完成", "已取消"].includes(frm.doc.status) && frm.doc.stage !== "完成") {
			frm.add_custom_button(__("下一阶段"), () => {
				runTicketAction(frm, "next_stage");
			});
		}

		if (frm.doc.status === "进行中") {
			frm.add_custom_button(__("暂停"), () => {
				runTicketAction(frm, "hold_ticket");
			});
		}

		if (frm.doc.status === "暂停") {
			frm.add_custom_button(__("恢复"), () => {
				runTicketAction(frm, "resume_ticket");
			});
		}

		if (!["已完成", "已取消"].includes(frm.doc.status)) {
			frm.add_custom_button(__("完工"), () => {
				runTicketAction(frm, "complete_ticket");
			});
		}
	},

	style(frm) {
		if (!frm.doc.style) {
			return;
		}

		frappe.db.get_value("Style", frm.doc.style, "item_template").then((response) => {
			const styleDoc = response.message || {};
			if (styleDoc.item_template && !frm.doc.item_template) {
				frm.set_value("item_template", styleDoc.item_template);
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

function openStageLogDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("新增阶段日志"),
		fields: [
			{
				fieldname: "stage",
				fieldtype: "Select",
				label: "阶段",
				options: "计划\n裁剪\n车缝\n后整\n包装\n完成",
				reqd: 1,
				default: frm.doc.stage || "计划"
			},
			{
				fieldname: "qty_in",
				fieldtype: "Int",
				label: "投入数量",
				default: frm.doc.qty || 0
			},
			{
				fieldname: "qty_out",
				fieldtype: "Int",
				label: "产出数量",
				default: frm.doc.qty || 0
			},
			{
				fieldname: "defect_qty",
				fieldtype: "Int",
				label: "不良数量",
				default: 0
			},
			{
				fieldname: "warehouse",
				fieldtype: "Link",
				label: "仓库",
				options: "Warehouse"
			},
			{
				fieldname: "supplier",
				fieldtype: "Link",
				label: "供应商",
				options: "Supplier",
				default: frm.doc.supplier || ""
			},
			{
				fieldname: "remark",
				fieldtype: "Small Text",
				label: "备注"
			}
		]
	});

	dialog.set_primary_action(__("保存"), () => {
		const values = dialog.get_values();
		if (!values) {
			return;
		}

		runTicketAction(frm, "add_stage_log", values).then(() => {
			dialog.hide();
		});
	});

	dialog.show();
}

function openBomDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("生成物料清单草稿"),
		fields: [
			{
				fieldname: "company",
				fieldtype: "Link",
				label: "公司",
				options: "Company"
			},
			{
				fieldname: "item_code",
				fieldtype: "Link",
				label: "物料编码",
				options: "Item",
				reqd: 1,
				default: frm.doc.item_template || ""
			},
			{
				fieldname: "source_bom",
				fieldtype: "Link",
				label: "来源物料清单",
				options: "BOM"
			},
			{
				fieldname: "quantity",
				fieldtype: "Float",
				label: "物料清单数量",
				reqd: 1,
				default: 1
			},
			{
				fieldname: "is_active",
				fieldtype: "Check",
				label: "启用",
				default: 1
			},
			{
				fieldname: "is_default",
				fieldtype: "Check",
				label: "默认物料清单",
				default: 0
			},
			{
				fieldname: "description",
				fieldtype: "Small Text",
				label: "说明"
			}
		]
	});

	dialog.set_primary_action(__("打开草稿"), () => {
		const values = dialog.get_values();
		if (!values) {
			return;
		}

		callTicketMethod(frm, "prepare_bom", values).then((payload) => {
			const prepared = payload.payload || {};
			dialog.hide();
			openPreparedBom(prepared);
		});
	});

	dialog.show();
}

function openWorkOrderDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("生成生产工单草稿"),
		fields: [
			{
				fieldname: "company",
				fieldtype: "Link",
				label: "公司",
				options: "Company"
			},
			{
				fieldname: "production_item",
				fieldtype: "Link",
				label: "生产物料",
				options: "Item",
				reqd: 1,
				default: frm.doc.item_template || ""
			},
			{
				fieldname: "bom_no",
				fieldtype: "Link",
				label: "物料清单",
				options: "BOM",
				default: frm.doc.bom_no || ""
			},
			{
				fieldname: "qty",
				fieldtype: "Float",
				label: "数量",
				reqd: 1,
				default: frm.doc.qty || 0
			},
			{
				fieldname: "source_warehouse",
				fieldtype: "Link",
				label: "来源仓库",
				options: "Warehouse"
			},
			{
				fieldname: "wip_warehouse",
				fieldtype: "Link",
				label: "在制仓库",
				options: "Warehouse"
			},
			{
				fieldname: "fg_warehouse",
				fieldtype: "Link",
				label: "成品仓库",
				options: "Warehouse"
			},
			{
				fieldname: "description",
				fieldtype: "Small Text",
				label: "说明"
			}
		]
	});

	dialog.set_primary_action(__("打开草稿"), () => {
		const values = dialog.get_values();
		if (!values) {
			return;
		}

		callTicketMethod(frm, "prepare_work_order", values).then((payload) => {
			const prepared = payload.payload || {};
			dialog.hide();
			openPreparedWorkOrder(prepared);
		});
	});

	dialog.show();
}

function openStockEntryDialog(frm) {
	const defaultQty = Math.max(Number(frm.doc.qty || 0) - Number(frm.doc.defect_qty || 0), 0);
	const dialog = new frappe.ui.Dialog({
		title: __("生成库存凭证草稿"),
		fields: [
			{
				fieldname: "purpose",
				fieldtype: "Select",
				label: "用途",
				options: "物料入库\n物料转移\n生产领料",
				reqd: 1,
				default: frm.doc.work_order ? "生产领料" : "物料入库"
			},
			{
				fieldname: "item_code",
				fieldtype: "Link",
				label: "物料编码",
				options: "Item",
				reqd: 1,
				default: frm.doc.item_template || ""
			},
			{
				fieldname: "qty",
				fieldtype: "Float",
				label: "数量",
				reqd: 1,
				default: defaultQty
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
				options: "Warehouse"
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

		callTicketMethod(frm, "prepare_stock_entry", values).then((payload) => {
			const prepared = payload.payload || {};
			dialog.hide();
			openPreparedStockEntry(prepared);
		});
	});

	dialog.show();
	if (dialog.fields_dict.purpose.$input) {
		dialog.fields_dict.purpose.$input.on("change", () => {
			toggleStockEntryWarehouseFields(dialog);
		});
	}
	toggleStockEntryWarehouseFields(dialog);
}

function toggleStockEntryWarehouseFields(dialog) {
	const purpose = dialog.get_value("purpose");
	const sourceRequired = ["物料转移", "生产领料"].includes(purpose);
	const targetRequired = ["物料入库", "物料转移", "生产领料"].includes(purpose);

	dialog.set_df_property("source_warehouse", "reqd", sourceRequired ? 1 : 0);
	dialog.set_df_property("target_warehouse", "reqd", targetRequired ? 1 : 0);

	if (!sourceRequired) {
		dialog.set_value("source_warehouse", "");
	}
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

function openPreparedWorkOrder(payload) {
	frappe.new_doc("Work Order", {}, (doc) => {
		Object.keys(payload || {}).forEach((key) => {
			if (key === "doctype") {
				return;
			}
			doc[key] = payload[key];
		});
	});
}

function openPreparedBom(payload) {
	frappe.new_doc("BOM", {}, (doc) => {
		Object.keys(payload || {}).forEach((key) => {
			if (key === "doctype" || key === "items" || key === "operations") {
				return;
			}
			doc[key] = payload[key];
		});

		(payload.items || []).forEach((item) => {
			const row = frappe.model.add_child(doc, item.doctype || "BOM Item", "items");
			Object.keys(item).forEach((key) => {
				if (key === "doctype") {
					return;
				}
				row[key] = item[key];
			});
		});

		(payload.operations || []).forEach((operation) => {
			const row = frappe.model.add_child(doc, operation.doctype || "BOM Operation", "operations");
			Object.keys(operation).forEach((key) => {
				if (key === "doctype") {
					return;
				}
				row[key] = operation[key];
			});
		});
	});
}
