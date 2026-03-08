# Fashion ERP 售后工单设计草案

本文档用于整理 `fashion_erp` 的售后工单一期字段设计，便于评审和后续落地为 DocType。

## 文档状态说明

- 本文件是售后模块的设计草案与字段参考
- 当前售后模块的真实实现进度，应以 [fashion-erp-phase2-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase2-task-list.md)、[fashion-erp-phase2-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase2-implementation.md) 和当前代码为准
- 如果本文件中的个别默认值、状态名或字段表达与代码不完全一致，应优先以代码和阶段文档为准

相关对象：

- 已有退货原因字典：`Return Reason`
- 已有退货结果字典：`Return Disposition`
- 已有库存状态字典：`Inventory Status`

## 设计目标

售后工单先覆盖女装电商最常见的售后场景：

- 退款
- 退货退款
- 换货
- 补发
- 维修
- 投诉

平台自动同步相关能力当前按 `外部依赖阻塞/暂停` 处理，第一版先做内部可执行工单。

## 建议对象结构

建议先做 `1 个主表 + 2 个子表`：

1. `After Sales Ticket`
2. `After Sales Item`
3. `After Sales Log`

## 1. After Sales Ticket

用途：

- 作为售后主工单
- 跟踪从申请到收货、质检、退款、换货、关闭的全过程

### DocType 级建议

| 项目 | 建议值 |
|---|---|
| 模块 | `Stock` 或后续独立 `After Sales` |
| 类型 | 主表 |
| `autoname` | 自定义命名函数 |
| 主显示字段 | `external_order_id` 或 `customer` |
| 搜索字段 | `name, external_order_id, sales_order, customer, tracking_no` |
| 默认状态 | `NEW` |

### 售后单号规则

售后单号不需要人工录入，建议在创建工单时自动生成。

目标格式：

`YYYYMMDDTK0001`

示例：

`20260307TK0001`

规则说明：

- `YYYYMMDD`：当天日期
- `TK`：售后工单固定前缀
- `0001`：四位流水号

实现建议：

- 使用服务端自定义命名逻辑，不用手工输入
- 四位流水号建议按“每天重新开始计数”处理
- 这个规则不适合只用简单 `format:`，因为通常还需要“按日期重置序号”

### 字段字典

| 字段代码 | 中文名称 | 类型 | 必填 | 说明 |
|---|---|---|---:|---|
| `ticket_no` | 售后单号 | 系统编号 | 是 | 主键，建议系统生成 |
| `ticket_type` | 工单类型 | `Select` | 是 | `退款`、`退货退款`、`换货`、`补发`、`维修`、`投诉` |
| `ticket_status` | 工单状态 | `Select` | 是 | `NEW`、`WAITING_RETURN`、`RECEIVED`、`INSPECTING`、`PENDING_DECISION`、`WAITING_REFUND`、`WAITING_RESEND`、`CLOSED`、`CANCELLED` |
| `priority` | 优先级 | `Select` | 是 | `Low`、`Normal`、`High`、`Urgent` |
| `channel` | 渠道 | `Data` | 否 | 如抖音、淘宝、视频号 |
| `channel_store` | 店铺 | `Link -> Channel Store` | 否 | 店铺维度 |
| `external_order_id` | 外部订单号 | `Data` | 否 | 平台订单号 |
| `sales_order` | 销售订单 | `Link -> Sales Order` | 否 | ERPNext 销售订单 |
| `sales_invoice` | 销售发票 | `Link -> Sales Invoice` | 否 | 如后续退款要对账可用 |
| `delivery_note` | 发货单 | `Link -> Delivery Note` | 否 | 对应原始发货单 |
| `customer` | 客户 | `Link -> Customer` | 否 | 客户主档 |
| `buyer_name` | 买家姓名 | `Data` | 否 | 冗余展示 |
| `mobile` | 手机号 | `Data` | 否 | 联系方式 |
| `apply_time` | 申请时间 | `Datetime` | 否 | 平台发起或人工登记时间 |
| `return_reason` | 售后原因 | `Link -> Return Reason` | 否 | 复用现有字典 |
| `reason_detail` | 原因说明 | `Small Text` | 否 | 补充说明 |
| `warehouse` | 收货仓 | `Link -> Warehouse` | 否 | 退货接收仓 |
| `warehouse_location` | 收货库位 | `Link -> Warehouse Location` | 否 | 退回时暂存或检验位 |
| `logistics_company` | 退回物流商 | `Data` | 否 | 逆向物流 |
| `tracking_no` | 退回运单号 | `Data` | 否 | 退货快递单号 |
| `received_at` | 收货时间 | `Datetime` | 否 | 实际签收时间 |
| `return_disposition` | 处理结果 | `Link -> Return Disposition` | 否 | 最终处理口径 |
| `refund_amount` | 退款金额 | `Currency` | 否 | 需退款金额 |
| `refund_status` | 退款状态 | `Select` | 否 | `NOT_REQUIRED`、`PENDING`、`DONE`、`REJECTED` |
| `replacement_sales_order` | 换货新单 | `Link -> Sales Order` | 否 | 换货时关联新单 |
| `owner_user` | 创建人 | `Link -> User` | 否 | 工单创建人 |
| `handler_user` | 当前处理人 | `Link -> User` | 否 | 当前跟进人 |
| `remark` | 内部备注 | `Small Text` | 否 | 内部说明 |
| `items` | 售后明细 | `Table -> After Sales Item` | 是 | 售后商品明细 |
| `logs` | 工单日志 | `Table -> After Sales Log` | 否 | 状态和动作记录 |

### 订单关联建议

可以，而且建议做成两层关联：

1. 主表关联订单头
2. 明细表关联订单行

这样才能区分：

- 这个售后单属于哪一个订单
- 这个售后单里的哪一件商品、哪一行明细出了问题

主表层建议至少保留：

- `external_order_id`
- `sales_order`
- `sales_invoice`
- `delivery_note`

## 2. After Sales Item

### 建议状态枚举

| 状态代码 | 中文说明 |
|---|---|
| `NEW` | 新建 |
| `WAITING_RETURN` | 等待买家退回 |
| `RECEIVED` | 已收货 |
| `INSPECTING` | 质检中 |
| `PENDING_DECISION` | 待判定 |
| `WAITING_REFUND` | 待退款 |
| `WAITING_RESEND` | 待补发/待换货 |
| `CLOSED` | 已关闭 |
| `CANCELLED` | 已取消 |

### 建议工单类型枚举

| 类型代码 | 中文说明 |
|---|---|
| `REFUND_ONLY` | 退款 |
| `RETURN_REFUND` | 退货退款 |
| `EXCHANGE` | 换货 |
| `RESEND` | 补发 |
| `REPAIR` | 维修 |
| `COMPLAINT` | 投诉 |

## 2. After Sales Item

用途：

- 记录售后单里的商品明细
- 作为库存状态变化和质检结果的主要落点

### 字段字典

| 字段代码 | 中文名称 | 类型 | 必填 | 说明 |
|---|---|---|---:|---|
| `item_code` | SKU | `Link -> Item` | 是 | 售后商品 |
| `sales_order_item_ref` | 订单明细行ID | `Data` | 否 | 对应原始订单行，可保存 `Sales Order Item.name` |
| `delivery_note_item_ref` | 发货明细行ID | `Data` | 否 | 对应原始发货行，可保存 `Delivery Note Item.name` |
| `style` | 款号 | `Link -> Style` | 否 | 冗余展示 |
| `color_code` | 颜色代码 | `Data` | 否 | 冗余展示 |
| `size_code` | 尺码代码 | `Data` | 否 | 冗余展示 |
| `qty` | 申请数量 | `Float` | 是 | 本次售后数量 |
| `requested_action` | 申请动作 | `Select` | 是 | `退款`、`退货退款`、`换货`、`补发`、`维修` |
| `received_qty` | 实收数量 | `Float` | 否 | 实际收到数量 |
| `inventory_status_from` | 原库存状态 | `Link -> Inventory Status` | 否 | 收货或处理前状态 |
| `inventory_status_to` | 目标库存状态 | `Link -> Inventory Status` | 否 | 处理后状态 |
| `return_reason` | 售后原因 | `Link -> Return Reason` | 否 | 可覆盖主单原因 |
| `return_disposition` | 处理结果 | `Link -> Return Disposition` | 否 | 单行结果 |
| `restock_qty` | 回可售数量 | `Float` | 否 | 可重新上架数量 |
| `defective_qty` | 次品数量 | `Float` | 否 | 不可售数量 |
| `inspection_note` | 质检说明 | `Small Text` | 否 | 质检备注 |

### 明细关联建议

如果只关联主订单，不关联订单行，后续会有两个问题：

1. 一个订单有多件商品时，无法准确定位是哪一件在售后
2. 换货、补发、退货入库时，无法精确追踪原始发货行

所以建议：

- 主表关联 `Sales Order / Delivery Note`
- 明细行再记录 `sales_order_item_ref / delivery_note_item_ref`

## 3. After Sales Log

用途：

- 记录售后工单过程日志
- 保存状态变化和关键动作

### 字段字典

| 字段代码 | 中文名称 | 类型 | 必填 | 说明 |
|---|---|---|---:|---|
| `action_time` | 操作时间 | `Datetime` | 是 | 日志时间 |
| `action_type` | 操作类型 | `Select` | 是 | `创建`、`收货`、`质检`、`退款`、`换货`、`关闭` |
| `from_status` | 原状态 | `Data` | 否 | 变更前状态 |
| `to_status` | 新状态 | `Data` | 否 | 变更后状态 |
| `operator` | 操作人 | `Link -> User` | 否 | 当前操作人 |
| `note` | 说明 | `Small Text` | 否 | 动作说明 |

## 第一版建议范围

第一版建议只做以下能力：

1. 售后主工单
2. 售后明细
3. 售后日志
4. 复用现有 `Return Reason / Return Disposition / Inventory Status`
5. 自动生成售后单号
6. 关联原始订单、发货单和订单明细
7. 人工驱动退款、退货入库、换货；平台自动回写当前按 `外部依赖阻塞/暂停` 处理

## 当前已实现的动作流

当前代码里已经补了第一轮售后动作：

1. `Wait for Return`
2. `Receive`
3. `Start Inspection`
4. `Apply Decision`
5. `Approve Refund`
6. `Create Replacement Order`
7. `Close`
8. `Cancel`

当前状态推进逻辑：

- `NEW -> WAITING_RETURN`
- `NEW/WAITING_RETURN -> RECEIVED`
- `RECEIVED -> INSPECTING`
- `NEW/RECEIVED/INSPECTING/PENDING_DECISION -> WAITING_REFUND / WAITING_RESEND / PENDING_DECISION`
- `WAITING_REFUND -> CLOSED`
- `WAITING_RESEND -> CLOSED`

补充说明：

- `REFUND_ONLY / RETURN_REFUND` 默认会进入 `WAITING_REFUND`
- `EXCHANGE / RESEND / REPAIR` 默认会进入 `WAITING_RESEND`
- `COMPLAINT` 当前先保留在 `PENDING_DECISION`
- `Replacement Sales Order` 已支持从售后单生成草稿，并通过 `Sales Order.after_sales_ticket` 回写到售后单

## 当前已实现的库存草稿联动

当前代码里已支持从售后单准备 `Stock Entry` 草稿：

1. `RECEIVE_PENDING`
2. `FINAL_DISPOSITION`

说明：

- `RECEIVE_PENDING` 用于把实收商品先按 `RETURN_PENDING` 入账
- `FINAL_DISPOSITION` 用于把商品按质检结论转入最终库存状态
- 当前是“准备草稿”，不是直接自动提交
- `Stock Entry` 和 `Stock Entry Detail` 都已增加 `after_sales_ticket` 追踪字段
- 如果单行同时存在 `restock_qty` 和 `defective_qty`，系统会要求拆分后再生成最终处置草稿

## 后续可扩展方向

后续可以继续加：

1. 平台售后单自动导入（外部依赖阻塞/暂停）
2. 平台退款状态回传（外部依赖阻塞/暂停）
3. 独立维修工单闭环（下一步研发计划）
4. 售后工单和库存状态自动联动
5. 售后照片、质检图片、聊天记录附件
