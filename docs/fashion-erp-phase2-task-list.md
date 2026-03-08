# Fashion ERP 第二阶段任务清单

本文档是 `fashion_erp` 第二阶段的任务级清单。

相关文档：

- 第二阶段实施版：[fashion-erp-phase2-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase2-implementation.md)
- 总体设计：[fashion-erp-doctype-design.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-doctype-design.md)

## 阶段结论

- 当前阶段聚焦 `仓储与状态流转`
- 电商订单同步及平台状态自动回写当前统一按 `外部依赖阻塞/暂停` 处理
- 生产闭环后置，当前不作为下一批任务重点

## 任务列表

### T300 第二阶段范围冻结

| 项目 | 内容 |
|---|---|
| 任务编号 | `T300` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 目标 | 冻结二阶段范围，明确电商订单同步转为 `外部依赖阻塞/暂停` |
| 交付物 | 二阶段实施文档 |

### T310 Warehouse Zone

| 项目 | 内容 |
|---|---|
| 任务编号 | `T310` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 目标 | 建立仓储功能区域字典 |
| 交付物 | `Warehouse Zone` DocType、种子数据 |

### T311 Inventory Status

| 项目 | 内容 |
|---|---|
| 任务编号 | `T311` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 目标 | 建立库存状态字典 |
| 交付物 | `Inventory Status` DocType、种子数据 |

### T312 Warehouse Location 增强

| 项目 | 内容 |
|---|---|
| 任务编号 | `T312` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 目标 | 把库位从简单名称扩展为编码、区域、类型、优先级模型 |
| 交付物 | 更新后的 `Warehouse Location` DocType |

### T320 Return Reason

| 项目 | 内容 |
|---|---|
| 任务编号 | `T320` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 目标 | 建立退货原因字典 |
| 交付物 | `Return Reason` DocType |

当前实现说明：

- 已新增 `Return Reason` DocType
- 已预置 `R01-R07` 与 `R99` 种子数据

### T321 Return Disposition

| 项目 | 内容 |
|---|---|
| 任务编号 | `T321` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 目标 | 建立退货结果字典 |
| 交付物 | `Return Disposition` DocType |

当前实现说明：

- 已新增 `Return Disposition` DocType
- 已预置 `A1/A2/B1/B2/C1/D1` 种子数据
- 每个退货结果都绑定目标 `Inventory Status`

### T330 状态流转规则

| 项目 | 内容 |
|---|---|
| 任务编号 | `T330` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 目标 | 限制库存状态只能按规则流转 |
| 交付物 | 状态流转服务与约束 |

当前实现说明：

- `Stock Entry.validate` 已接入库存状态流转校验
- `Stock Entry Detail` 已新增 `inventory_status_from / inventory_status_to / return_reason / return_disposition`
- `Return Disposition` 选定后会自动带出目标库存状态
- 非法 `from -> to` 流转会在保存时被阻止

### T340 After Sales Ticket

| 项目 | 内容 |
|---|---|
| 任务编号 | `T340` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 目标 | 建立售后工单主表、明细和日志 |
| 交付物 | `After Sales Ticket`、`After Sales Item`、`After Sales Log` |

范围说明：

- 售后单号自动生成，格式 `YYYYMMDDTK0001`
- 支持关联 `Sales Order / Sales Invoice / Delivery Note`
- 明细行支持关联原始订单行和发货行

当前实现说明：

- 已新增 `After Sales Ticket`、`After Sales Item`、`After Sales Log`
- 售后单号改为服务端自动生成，按日期前缀生成 `YYYYMMDDTK0001`
- 主表支持关联 `Sales Order / Sales Invoice / Delivery Note`
- 明细支持 `sales_order_item_ref / delivery_note_item_ref`
- 已加入基础校验、订单头字段自动回填、库存状态目标自动带出

### T341 After Sales Actions

| 项目 | 内容 |
|---|---|
| 任务编号 | `T341` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 目标 | 让售后工单具备可执行动作流转 |
| 交付物 | 售后状态动作、退款动作、换货新单草稿 |

当前实现说明：

- 已补 `Wait for Return / Receive / Start Inspection / Apply Decision / Approve Refund / Close / Cancel`
- 已支持从售后工单生成 `Replacement Sales Order` 草稿
- 已给 `Sales Order` 增加 `after_sales_ticket` 关联并在保存后反写 `replacement_sales_order`

### T342 After Sales Stock Entry Draft

| 项目 | 内容 |
|---|---|
| 任务编号 | `T342` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 目标 | 让售后工单可生成退货入库和最终处置的 `Stock Entry` 草稿 |
| 交付物 | 售后 `Stock Entry` 草稿服务、表单按钮、追踪字段 |

当前实现说明：

- 已补 `Prepare Stock Entry` 按钮
- 支持两种模式：`RECEIVE_PENDING`、`FINAL_DISPOSITION`
- 已给 `Stock Entry / Stock Entry Detail` 增加 `after_sales_ticket`
- 最终处置模式会把 `RETURN_PENDING -> 目标 Inventory Status` 带进明细

## 第二阶段收口

第二阶段任务到 `T342` 为止，当前文档不再继续追加“生产完工到库存状态映射”类任务。

原因：

1. 公司当前核心业务是女装电商运营
2. 大货生产以第三方外包为主
3. 内部生产流水线只承担打样辅助，不构成主业务闭环
4. 电商平台接口认证当前无法取得，因此订单同步只能手工处理

后续任务切换到第三阶段：

- [fashion-erp-phase3-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-implementation.md)
- [fashion-erp-phase3-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-task-list.md)
