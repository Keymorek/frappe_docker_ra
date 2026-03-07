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

		frm.add_custom_button(__("查看供料视图"), () => {
			openSupplySummary(frm);
		});

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

function openSupplySummary(frm) {
	const invoke = () => frm.call("get_supply_summary").then((response) => {
		const payload = response.message || {};
		if (!payload.ok) {
			frappe.msgprint(payload.message || __("当前没有可展示的供料数据。"));
			return null;
		}

		const dialog = new frappe.ui.Dialog({
			title: `${__("供料视图")} - ${frm.doc.order_no || frm.doc.name}`,
			size: "extra-large",
			fields: [
				{
					fieldname: "summary_html",
					fieldtype: "HTML"
				}
			]
		});

		dialog.fields_dict.summary_html.$wrapper.html(renderSupplySummary(payload));
		dialog.show();
		return dialog;
	});

	if (frm.is_dirty()) {
		return frm.save().then(() => invoke());
	}

	return invoke();
}

function renderSupplySummary(payload) {
	const summary = payload.summary || {};
	const rows = payload.rows || [];
	const shortageCount = Number(summary.shortage_count || 0);
	const indicatorColor = shortageCount > 0 ? "#b42318" : "#067647";
	const orderLabel = escapeHtml(payload.order_no || payload.order_name || "");
	const styleLabel = escapeHtml(payload.style_name || payload.style || "");

	let html = `
		<div style="margin-bottom: 12px;">
			<div><strong>${orderLabel}</strong></div>
			${styleLabel ? `<div class="text-muted">${styleLabel}</div>` : ""}
		</div>
		<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-bottom:16px;">
			${renderSupplyMetric(__("物料条数"), formatNumber(summary.line_count || 0))}
			${renderSupplyMetric(__("需采购条数"), formatNumber(shortageCount), indicatorColor)}
			${renderSupplyMetric(__("总需求"), formatNumber(summary.total_required_qty || 0))}
			${renderSupplyMetric(__("已备货"), formatNumber(summary.total_prepared_qty || 0))}
			${renderSupplyMetric(__("已发料"), formatNumber(summary.total_issued_qty || 0))}
			${renderSupplyMetric(__("现货口径"), formatNumber(summary.total_on_hand_qty || 0))}
			${renderSupplyMetric(__("在途口径"), formatNumber(summary.total_on_order_qty || 0))}
			${renderSupplyMetric(__("待采购"), formatNumber(summary.total_to_purchase_qty || 0), shortageCount > 0 ? "#b42318" : "#344054")}
		</div>
	`;

	if (!rows.length) {
		html += `<div class="text-muted">${__("当前没有供料明细。")}</div>`;
		return html;
	}

	html += `<div style="overflow:auto;"><table class="table table-bordered" style="min-width: 1300px;">`;
	html += `
		<thead>
			<tr>
				<th>${__("物料")}</th>
				<th>${__("来源行")}</th>
				<th>${__("仓库范围")}</th>
				<th>${__("库位")}</th>
				<th>${__("需求")}</th>
				<th>${__("已备")}</th>
				<th>${__("已发")}</th>
				<th>${__("现货")}</th>
				<th>${__("在途")}</th>
				<th>${__("待备货")}</th>
				<th>${__("待发料")}</th>
				<th>${__("待采购")}</th>
				<th>${__("状态")}</th>
			</tr>
		</thead>
		<tbody>
	`;

	rows.forEach((row) => {
		const statusTone = getSupplyStatusTone(row.status);
		html += `
			<tr>
				<td>
					<div style="font-weight:600;">${escapeHtml(row.item_code || "")}</div>
					<div class="text-muted">${escapeHtml(row.item_name || "")}</div>
					${row.uom ? `<div class="text-muted">${escapeHtml(row.uom)}</div>` : ""}
					${row.warning ? `<div style="font-size:12px; color:#b54708;">${escapeHtml(row.warning)}</div>` : ""}
				</td>
				<td>${escapeHtml(row.source_rows || "")}</td>
				<td>${escapeHtml(row.warehouse_scope || "")}</td>
				<td>${escapeHtml(row.locations || "")}</td>
				<td>${formatNumber(row.required_qty)}</td>
				<td>${formatNumber(row.prepared_qty)}</td>
				<td>${formatNumber(row.issued_qty)}</td>
				<td>${formatNumber(row.on_hand_qty)}</td>
				<td>${formatNumber(row.on_order_qty)}</td>
				<td>${formatNumber(row.to_prepare_qty)}</td>
				<td>${formatNumber(row.to_issue_qty)}</td>
				<td style="color:${Number(row.to_purchase_qty || 0) > 0 ? "#b42318" : "#344054"}; font-weight:600;">${formatNumber(row.to_purchase_qty)}</td>
				<td>
					<span style="display:inline-block; padding:2px 8px; border-radius:999px; background:${statusTone.background}; color:${statusTone.color};">
						${escapeHtml(row.status || "")}
					</span>
				</td>
			</tr>
		`;
	});

	html += `</tbody></table></div>`;
	return html;
}

function renderSupplyMetric(label, value, color = "#101828") {
	return `
		<div style="padding:12px; border:1px solid #eaecf0; border-radius:8px; background:#ffffff;">
			<div style="font-size:12px; color:#475467; margin-bottom:4px;">${escapeHtml(label)}</div>
			<div style="font-size:20px; font-weight:700; color:${color};">${escapeHtml(value)}</div>
		</div>
	`;
}

function getSupplyStatusTone(status) {
	if (status === "需采购") {
		return { background: "#fef3f2", color: "#b42318" };
	}
	if (status === "待备货") {
		return { background: "#fffaeb", color: "#b54708" };
	}
	if (status === "待发料") {
		return { background: "#eff8ff", color: "#175cd3" };
	}
	return { background: "#ecfdf3", color: "#067647" };
}

function formatNumber(value) {
	const number = Number(value || 0);
	return number.toLocaleString(undefined, {
		minimumFractionDigits: 0,
		maximumFractionDigits: 2
	});
}

function escapeHtml(value) {
	return String(value || "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
}
