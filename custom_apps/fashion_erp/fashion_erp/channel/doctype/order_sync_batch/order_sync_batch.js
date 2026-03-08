frappe.ui.form.on("Order Sync Batch", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.batch_status === "已取消") {
			return;
		}

		frm.add_custom_button(__("导入 CSV"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("导入 CSV 内容"),
				fields: [
					{
						fieldname: "source_file_name",
						fieldtype: "Data",
						label: __("来源文件名"),
						default: frm.doc.source_file_name || "fashion-erp-order-sync-template.csv"
					},
					{
						fieldname: "replace_existing",
						fieldtype: "Check",
						label: __("覆盖现有明细"),
						default: 1
					},
					{
						fieldname: "csv_content",
						fieldtype: "Long Text",
						label: __("CSV 内容"),
						reqd: 1
					}
				],
				primary_action_label: __("导入"),
				primary_action(values) {
					frm.call("load_csv", values).then((response) => {
						const payload = response.message || {};
						frappe.show_alert({
							message: payload.message || __("CSV 已导入。"),
							indicator: "green"
						});
						showBatchSummaryDialog(__("CSV 导入结果"), payload.summary || {});
						dialog.hide();
						frm.refresh();
					});
				}
			});
			dialog.show();
		});

		frm.add_custom_button(__("预览导入"), () => {
			frm.call("preview_import").then((response) => {
				const payload = response.message || {};
				frappe.show_alert({
					message: payload.message || __("批次预览完成。"),
					indicator: "blue"
				});
				showPreviewDialog(payload);
				frm.refresh();
			});
		});

		if (["待导入", "待校验", "部分导入"].includes(frm.doc.batch_status)) {
			frm.add_custom_button(__("执行导入"), () => {
				frm.call("execute_import").then((response) => {
					const payload = response.message || {};
					frappe.show_alert({
						message: payload.message || __("订单导入已执行。"),
						indicator: "green"
					});
					showExecuteDialog(payload);
					frm.refresh();
				});
			});
		}
	}
});

function showPreviewDialog(payload) {
	const orders = payload.orders || [];
	const rows = orders.length
		? orders
				.map((row) => `
					<tr>
						<td>${escapeHtml(row.external_order_id || "")}</td>
						<td>${escapeHtml(row.customer || "")}</td>
						<td>${escapeHtml(row.group_status || "")}</td>
						<td>${escapeHtml(String(row.row_count || 0))}</td>
						<td>${escapeHtml(row.sales_order || "")}</td>
						<td>${escapeHtml(row.message || "")}</td>
					</tr>
				`)
				.join("")
		: `<tr><td colspan="6">${__("没有可显示的订单摘要。")}</td></tr>`;

	frappe.msgprint({
		title: __("预览结果"),
		message: `
			<div style="margin-bottom:12px;">${escapeHtml(payload.message || __("批次预览完成。"))}</div>
			${renderSummaryMetrics(payload.summary || {})}
			<div style="margin-top:12px; overflow:auto;">
				<table class="table table-bordered">
					<thead>
						<tr>
							<th>${__("外部订单号")}</th>
							<th>${__("客户")}</th>
							<th>${__("状态")}</th>
							<th>${__("行数")}</th>
							<th>${__("销售订单")}</th>
							<th>${__("说明")}</th>
						</tr>
					</thead>
					<tbody>${rows}</tbody>
				</table>
			</div>
		`
	});
}

function showBatchSummaryDialog(title, summary) {
	frappe.msgprint({
		title: title || __("批次结果"),
		message: renderSummaryMetrics(summary || {})
	});
}

function showExecuteDialog(payload) {
	const createdOrders = payload.created_orders || [];
	const failedOrders = payload.failed_orders || [];
	const createdRows = createdOrders.length
		? createdOrders.map((name) => `<li>${escapeHtml(name)}</li>`).join("")
		: `<li>${__("无")}</li>`;
	const failedRows = failedOrders.length
		? failedOrders.map((name) => `<li>${escapeHtml(name)}</li>`).join("")
		: `<li>${__("无")}</li>`;

	frappe.msgprint({
		title: __("导入结果"),
		message: `
			<div style="margin-bottom:12px;">${escapeHtml(payload.message || __("订单导入已执行。"))}</div>
			${renderSummaryMetrics(payload.summary || {})}
			<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin-top:12px;">
				<div>
					<div style="font-weight:600; margin-bottom:6px;">${__("已创建订单")}</div>
					<ul style="margin:0; padding-left:18px;">${createdRows}</ul>
				</div>
				<div>
					<div style="font-weight:600; margin-bottom:6px;">${__("失败外部订单")}</div>
					<ul style="margin:0; padding-left:18px;">${failedRows}</ul>
				</div>
			</div>
		`
	});
}

function renderSummaryMetrics(summary) {
	const metrics = [
		[__("总行数"), summary.total_rows || 0],
		[__("有效行数"), summary.valid_rows || 0],
		[__("失败行数"), summary.failed_rows || 0],
		[__("待导入行数"), summary.pending_rows || 0],
		[__("已导入订单"), summary.imported_orders || 0],
		[__("重复订单"), summary.duplicate_orders || 0]
	];

	return `
		<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(120px, 1fr)); gap:8px;">
			${metrics
				.map(
					([label, value]) => `
						<div style="border:1px solid #d0d5dd; border-radius:8px; padding:10px 12px;">
							<div style="font-size:12px; color:#667085;">${escapeHtml(label)}</div>
							<div style="font-size:20px; font-weight:700; margin-top:4px;">${escapeHtml(String(value))}</div>
						</div>
					`
				)
				.join("")}
		</div>
	`;
}

function escapeHtml(value) {
	if (frappe.utils && frappe.utils.escape_html) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	}
	return String(value == null ? "" : value)
		.replaceAll("&", "&amp;")
		.replaceAll("<", "&lt;")
		.replaceAll(">", "&gt;")
		.replaceAll('"', "&quot;")
		.replaceAll("'", "&#39;");
}
