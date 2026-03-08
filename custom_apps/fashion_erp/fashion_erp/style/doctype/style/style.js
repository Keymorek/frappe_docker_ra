frappe.ui.form.on("Style", {
	setup(frm) {
		frm.set_query("product_category", () => ({
			filters: {
				enabled: 1
			}
		}));

		frm.set_query("size_system", () => buildSizeSystemQuery(frm));
		frm.set_query("season", () => ({ filters: { enabled: 1 } }));
		frm.set_query("year", () => ({ filters: { enabled: 1 } }));
		frm.set_query("fabric_main", () => ({ filters: { enabled: 1 } }));
		frm.set_query("fabric_lining", () => ({ filters: { enabled: 1 } }));
		setupStyleSizeQuery(frm);
	},

	refresh(frm) {
		loadProductCategorySizeRule(frm, false);
		frm._lastSizeSystem = frm.doc.size_system || "";

		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("创建打样单"), () => {
			createSampleTicket(frm);
		});

		frm.add_custom_button(__("创建工艺单"), () => {
			createCraftSheet(frm);
		});

		frm.add_custom_button(__("生成单品编码"), () => {
			runStyleAction(frm, "fashion_erp.style.api.generate_variants");
		});

		frm.add_custom_button(__("创建模板货品"), () => {
			runStyleAction(frm, "fashion_erp.style.api.create_template_item");
		});

		frm.add_custom_button(__("查看矩阵"), () => {
			openStyleMatrix(frm);
		});

		frm.add_custom_button(__("创建生产跟踪单"), () => {
			createProductionTicket(frm);
		});
	},

	product_category(frm) {
		syncProductCategoryFields(frm);
		loadProductCategorySizeRule(frm, true);
	},

	size_system(frm) {
		handleSizeSystemChange(frm);
	},

	colors_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.sort_order) {
			frappe.model.set_value(cdt, cdn, "sort_order", (frm.doc.colors || []).length * 10);
		}
		if (row.enabled === undefined || row.enabled === null) {
			frappe.model.set_value(cdt, cdn, "enabled", 1);
		}
	}
});

frappe.ui.form.on("Style Color", {
	color(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.color) {
			return;
		}

		frappe.db.get_value("Color", row.color, ["color_name", "color_group"]).then((response) => {
			const colorDoc = response.message || {};
			frappe.model.set_value(cdt, cdn, "color_name", colorDoc.color_name || row.color);

			if (!colorDoc.color_group) {
				return null;
			}

			return frappe.db.get_value("Color Group", colorDoc.color_group, "color_group_code").then((groupResponse) => {
				const groupDoc = groupResponse.message || {};
				frappe.model.set_value(cdt, cdn, "color_code", groupDoc.color_group_code || "");
			});
		});
	}
});

frappe.ui.form.on("Style Size", {
	size(frm, cdt, cdn) {
		syncStyleSizeRow(cdt, cdn);
	}
});

function runStyleAction(frm, method) {
	frappe.call({
		method,
		args: {
			style_name: frm.doc.name
		}
	}).then((response) => {
		const payload = response.message || {};
		let message = payload.message || __("操作已完成。");
		if (payload.issues && payload.issues.length) {
			message += "<br><br>" + payload.issues.map((issue) => `- ${issue}`).join("<br>");
		}
		frappe.msgprint(message);
	});
}

function syncProductCategoryFields(frm) {
	if (!frm.doc.product_category) {
		frm.set_value("category_level_1", "");
		frm.set_value("category_level_2", "");
		frm.set_value("category_level_3", "");
		frm.set_value("category_level_4", "");
		frm.set_value("category_full_path", "");
		return;
	}

	frappe.db.get_value(
		"Style Category Template",
		frm.doc.product_category,
		["category_level_1", "category_level_2", "category_level_3", "category_level_4", "full_path"]
	).then((response) => {
		const row = response.message || {};
		frm.set_value("category_level_1", row.category_level_1 || "");
		frm.set_value("category_level_2", row.category_level_2 || "");
		frm.set_value("category_level_3", row.category_level_3 || "");
		frm.set_value("category_level_4", row.category_level_4 || "");
		frm.set_value("category_full_path", row.full_path || "");
	});
}

function loadProductCategorySizeRule(frm, applyDefault) {
	if (!frm.doc.product_category) {
		frm._allowedSizeSystems = [];
		refreshSizeSystemHint(frm);
		return Promise.resolve();
	}

	return frappe.call({
		method: "fashion_erp.style.api.get_product_category_size_rule",
		args: {
			product_category_name: frm.doc.product_category
		}
	}).then((response) => {
		const payload = response.message || {};
		const rule = payload.result || {};
		frm._allowedSizeSystems = rule.allowed_size_systems || [];

		if (frm.doc.size_system && frm._allowedSizeSystems.length && !frm._allowedSizeSystems.includes(frm.doc.size_system)) {
			frm.set_value("size_system", "");
		}

		if (applyDefault && !frm.doc.size_system && rule.default_size_system) {
			frm.set_value("size_system", rule.default_size_system);
		}

		refreshSizeSystemHint(frm, rule);
	});
}

function buildSizeSystemQuery(frm) {
	const allowed = frm._allowedSizeSystems || [];
	if (!allowed.length) {
		return {
			filters: {
				enabled: 1
			}
		};
	}

	return {
		filters: [
			["Size System", "enabled", "=", 1],
			["Size System", "name", "in", allowed]
		]
	};
}

function setupStyleSizeQuery(frm) {
	const grid = frm.fields_dict.style_sizes && frm.fields_dict.style_sizes.grid;
	if (!grid) {
		return;
	}

	grid.get_field("size").get_query = function () {
		if (!frm.doc.size_system) {
			return {
				filters: {
					enabled: 1,
					size_system: "__invalid__"
				}
			};
		}

		return {
			filters: {
				enabled: 1,
				size_system: frm.doc.size_system
			}
		};
	};
}

function handleSizeSystemChange(frm) {
	const previous = frm._lastSizeSystem || "";
	const current = frm.doc.size_system || "";
	if (previous && current && previous !== current && (frm.doc.style_sizes || []).length) {
		frappe.msgprint(__("尺码体系已变更，请重新选择本款尺码。"));
		frm.clear_table("style_sizes");
		frm.refresh_field("style_sizes");
		frm.set_value("size_range_summary", "");
	}
	frm._lastSizeSystem = current;
}

function syncStyleSizeRow(cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.size) {
		return;
	}

	frappe.db.get_value("Size Code", row.size, ["size_code", "size_name", "sort_order"]).then((response) => {
		const sizeRow = response.message || {};
		frappe.model.set_value(cdt, cdn, "size_code", sizeRow.size_code || "");
		frappe.model.set_value(cdt, cdn, "size_name", sizeRow.size_name || "");
		frappe.model.set_value(cdt, cdn, "sort_order", sizeRow.sort_order || 0);
	});
}

function refreshSizeSystemHint(frm, rule) {
	const payload = rule || {
		default_size_system: "",
		allowed_size_systems: frm._allowedSizeSystems || []
	};
	const allowedText = (payload.allowed_size_systems || []).join(" / ");
	let description = "";
	if (payload.default_size_system) {
		description = `${__("默认")}: ${payload.default_size_system}`;
	}
	if (allowedText) {
		description += description ? `<br>${__("允许")}: ${allowedText}` : `${__("允许")}: ${allowedText}`;
	}
	frm.set_df_property("size_system", "description", description);
}

function openStyleMatrix(frm) {
	frappe.call({
		method: "fashion_erp.style.api.get_style_matrix",
		args: {
			style_name: frm.doc.name
		}
	}).then((response) => {
		const payload = response.message || {};
		if (!payload.ok) {
			let message = payload.message || __("无法加载款色码矩阵。");
			if (payload.issues && payload.issues.length) {
				message += "<br><br>" + payload.issues.map((issue) => `- ${issue}`).join("<br>");
			}
			frappe.msgprint(message);
			return;
		}

		const matrix = payload.result || {};
		const dialog = new frappe.ui.Dialog({
			title: `${__("款色码矩阵")} - ${frm.doc.style_code || frm.doc.name}`,
			size: "extra-large",
			fields: [
				{
					fieldname: "matrix_html",
					fieldtype: "HTML"
				}
			]
		});

		dialog.fields_dict.matrix_html.$wrapper.html(renderStyleMatrix(matrix));
		dialog.show();
	});
}

function createProductionTicket(frm) {
	const defaults = {
		style: frm.doc.name,
		item_template: frm.doc.item_template || ""
	};
	const enabledColors = (frm.doc.colors || []).filter((row) => Number(row.enabled || 0) === 1);
	if (enabledColors.length === 1) {
		defaults.color = enabledColors[0].color;
	}
	frappe.new_doc("Production Ticket", defaults);
}

function createSampleTicket(frm) {
	const defaults = {
		style: frm.doc.name,
		style_name: frm.doc.style_name || "",
		item_template: frm.doc.item_template || ""
	};
	const enabledColors = (frm.doc.colors || []).filter((row) => Number(row.enabled || 0) === 1);
	if (enabledColors.length === 1) {
		defaults.color = enabledColors[0].color;
	}
	frappe.new_doc("Sample Ticket", defaults);
}

function createCraftSheet(frm) {
	const defaults = {
		style: frm.doc.name,
		style_name: frm.doc.style_name || "",
		item_template: frm.doc.item_template || ""
	};
	const enabledColors = (frm.doc.colors || []).filter((row) => Number(row.enabled || 0) === 1);
	if (enabledColors.length === 1) {
		defaults.color = enabledColors[0].color;
	}
	frappe.new_doc("Craft Sheet", defaults);
}

function renderStyleMatrix(matrix) {
	const sizeRows = matrix.size_rows || [];
	const matrixRows = matrix.matrix_rows || [];
	const summary = matrix.summary || {};
	const issues = matrix.issues || [];

	let html = `
			<div style="margin-bottom: 12px;">
				<div><strong>${escapeHtml(matrix.style_name || "")}</strong> (${escapeHtml(matrix.style_code || "")})</div>
				<div>${__("单品编码前缀")}: <strong>${escapeHtml(matrix.brand_prefix || "")}</strong></div>
				<div>${__("已生成")}: <strong>${summary.existing_count || 0}</strong> / ${summary.total_count || 0}</div>
				<div>${__("缺失")}: <strong style="color:#b42318;">${summary.missing_count || 0}</strong></div>
			</div>
	`;

	if (issues.length) {
		html += `
			<div style="margin-bottom: 12px; padding: 10px; background: #fff4e5; border: 1px solid #f5c36b; border-radius: 6px;">
				<div style="font-weight: 600; margin-bottom: 6px;">${__("前置问题")}</div>
				${issues.map((issue) => `<div>- ${escapeHtml(issue)}</div>`).join("")}
			</div>
		`;
	}

	html += `<div style="overflow:auto;"><table class="table table-bordered" style="min-width: 900px;">`;
	html += `<thead><tr><th>${__("颜色")}</th>`;
	sizeRows.forEach((sizeRow) => {
		html += `<th>${escapeHtml(sizeRow.size_name || sizeRow.size_code || "")}</th>`;
	});
	html += `</tr></thead><tbody>`;

	matrixRows.forEach((row) => {
		html += `<tr>`;
		html += `<td><strong>${escapeHtml(row.color_name || "")}</strong><br><span class="text-muted">${escapeHtml(row.color_code || "")}</span></td>`;

		(row.cells || []).forEach((cell) => {
			const bg = cell.exists ? "#ecfdf3" : "#fef3f2";
			const border = cell.exists ? "#6ce9a6" : "#fda29b";
			const label = cell.exists ? __("已存在") : __("缺失");
			const sellableText = cell.exists ? (cell.sellable ? __("可售") : __("不可售")) : "";
			const qtyText = cell.exists ? `${__("库存")}: ${formatNumber(cell.stock_qty)}` : "";
			html += `
				<td style="background:${bg}; border-color:${border}; min-width: 130px;">
					<div style="font-weight:600;">${escapeHtml(cell.sku_code || "")}</div>
					<div style="font-size:12px; color:${cell.exists ? "#067647" : "#b42318"};">${label}</div>
					${sellableText ? `<div style="font-size:12px;" class="text-muted">${escapeHtml(sellableText)}</div>` : ""}
					${qtyText ? `<div style="font-size:12px;" class="text-muted">${escapeHtml(qtyText)}</div>` : ""}
					${cell.item_name ? `<div style="font-size:12px;" class="text-muted">${escapeHtml(cell.item_name)}</div>` : ""}
				</td>
			`;
		});

		html += `</tr>`;
	});

	html += `</tbody></table></div>`;
	return html;
}

function escapeHtml(value) {
	return String(value || "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
}

function formatNumber(value) {
	return Number(value || 0).toLocaleString(undefined, {
		maximumFractionDigits: 2
	});
}
