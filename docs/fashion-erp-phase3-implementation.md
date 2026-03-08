# Fashion ERP 第三阶段实施版

本文档用于冻结新的主路线：

`原辅料采购与备货 -> 打样与工艺单 -> 外包下单与预计成本 -> 外包到货入库 -> 手工订单同步与履约成本 -> 售后闭环 -> 运营/财务报表`

相关文档：

- 产品需求分析：[fashion-erp-product-analysis.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-product-analysis.md)
- 第二阶段实施版：[fashion-erp-phase2-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase2-implementation.md)
- 第三阶段任务清单：[fashion-erp-phase3-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-task-list.md)
- 手工订单同步设计：[fashion-erp-order-sync-design.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-order-sync-design.md)

## 第三阶段结论

1. ERP 正式起点是 `Style` 款式录入
2. 季度主题、设计理念、品类规划仍在外部软件
3. 所有依赖平台官方数据结构或接口的能力，当前统一按 `外部依赖阻塞/暂停` 处理
4. 大货默认来自第三方外包工厂
5. 面料、辅料由我方提供，不由外包工厂自供
6. 包装耗材也由我方采购、入库、出库
7. 外包下单和原料出库不做自动联动，只做订单与原料引用关联
8. 快递费采用手工录入
9. 内部生产仅作为打样辅助，不作为当前主线

## 第三阶段目标

本阶段目标是把“从款式到入库、从订单到售后”的主业务链打通：

1. 原辅料与包装耗材可采购、入库、备货
2. 款式录入后可以进入打样
3. 工艺单可作为外包下单依据
4. 外包下单可记录预计成本并关联我方原辅料
5. 商品到货后可收货、质检、入库
6. 订单可手工同步并推进履约
7. 履约时可记录包装耗材和快递费
8. 售后与订单、库存形成闭环
9. 运营与财务报表可落地

## 第三阶段包含范围

### 3A 原辅料与耗材供给

- 面料、辅料、包装耗材主数据
- 采购、收货、入库、备货
- 外包订单与原辅料引用关联
- 外包单驱动供料需求与待采购视图
- 履约时包装耗材挂单
- 快递费录入

当前进度：

- `T405` 已完成基础版，已具备 `Item / Supplier` 分类字段、默认供给仓和履约耗材标识
- `T406` 已完成基础版，已在标准 `Purchase Order / Purchase Receipt` 上补采购用途、款号/打样引用、默认仓和服务端校验逻辑
- `T413` 已完成，已具备 `Outsource Order.materials` 子表、`planned_qty / prepared_qty / issued_qty_manual` 人工登记字段，以及备货仓/库位默认与服务端校验
- `T414` 已完成基础版，已具备 `required_qty / on_hand_qty / on_order_qty / prepared_qty / to_purchase_qty` 服务端计算逻辑和外包单上的供料视图入口
- `T415` 已完成，已在 `Purchase Order / Purchase Receipt Item` 增加外包单引用、收货从来源采购行自动回填外包上下文、`外包备货` 强制绑定外包单并校验款号/供料清单，供料视图在途优先按 `reference_outsource_order` 精确聚合，旧款号口径仅作兼容回退

### 3B 打样与工艺单

- 打样单
- 样品状态跟踪
- 工艺单
- 样品确认结论

当前进度：

- `T410` 已完成基础版，已具备打样单对象、状态流转、处理日志和 `Style` 发起入口
- `T411` 已完成基础版，已具备工艺单对象、版本控制、发布/作废动作，以及从 `Style / Sample Ticket` 发起和从工艺单创建外包单入口

### 3C 外包下单与入库

- 外包下单
- 预计成本
- 供应商来货登记
- 收货、质检、入库
- 异常记录

当前进度：

- `T412` 已完成基础版，已具备 `Outsource Order`、预计成本字段、工艺单/打样单引用、状态流转和工作区入口
- `T413/T414` 已完成基础版，已具备原辅料引用子表、人工登记字段，以及外包单级供料汇总视图
- `T420` 已完成基础版，已具备 `Outsource Receipt`、到货明细、收货确认、待质检入库 `Stock Entry` 草稿、已入库确认和累计到货回写逻辑
- `T421` 已完成基础版，已具备质检分配字段、`QC_PENDING -> SELLABLE / REPAIR / DEFECTIVE / FROZEN` 质检落账草稿、质检完成动作和 `已质检` 状态闭环

### 3D 订单履约与售后

- 手工订单同步
- 订单履约状态
- 配货、拣货、打包、发货动作
- 包装耗材出库
- 快递费录入
- 售后闭环

当前进度：

- `T430/T431` 仓库内已具备 `Channel Store / Order Sync Batch / preview_import / execute_import` 等基础实现，可保留作内部结构参考
- `T430/T431` 已支持店铺默认上下文、批次/行级留痕、CSV 粘贴导入、去重预判、订单聚合和 `Sales Order` 草稿创建
- `T430/T431` 但因暂时没有抖音官方稳定数据来源结构，当前统一按 `外部依赖阻塞/暂停` 处理；附件上传导入、导入结果报表和更完整批量交互不再继续投入
- `T432` 已完成基础版，已给 `Sales Order / Sales Order Item` 增加履约状态字段；保存销售订单时会统一初始化或聚合订单头/订单行状态，并基于 `delivered_qty` 自动推进到 `部分发货 / 已发货`
- `T432` 已补 `Delivery Note.on_submit / on_cancel` 回刷，发货或撤销发货后会重算关联 `Sales Order` 的订单头/订单行履约状态；当前中间态仍以订单行手工维护为主，待 `T433` 仓储动作接管
- `T433` 已完成基础版，已新增 `Sales Order` 履约服务层动作 `配货 / 拣货 / 打包 / 生成发货单`，可直接推进订单行状态到 `已锁库存 / 已拣货 / 待发货`
- `T433` 已在 `Sales Order` 标准表单补履约按钮入口；生成发货单当前为 `Delivery Note` 草稿模式，正式提交后再由现有 hook 回刷销售订单状态
- `T434` 已完成基础版，已给 `Delivery Note` 增加包装耗材子表、耗材数量/估算金额汇总字段和耗材出库单引用；保存出货单时会校验“只允许包装耗材”并自动补默认仓/估算金额
- `T434` 已补“生成耗材出库”入口，可从 `Delivery Note` 直接生成 `Stock Entry(Material Issue)` 草稿，并以 `delivery_note` 追踪出库来源
- `T435` 已完成基础版，`Delivery Note` 已补 `manual_logistics_fee / fulfillment_total_cost` 字段；保存时会把包装耗材估算金额与手工快递费汇总成统一履约总成本
- `T435` 已补履约成本汇总接口，可按日期范围、公司汇总已提交 `Delivery Note` 的耗材金额、手工快递费和履约总成本；当前金额口径仍为“耗材估算金额 + 手工快递费”
- `T440` 已完成基础版，售后工单激活时会把原销售订单头状态推进为 `售后中`，命中的销售订单行推进为 `售后中`；工单关闭后命中的订单行会推进为 `已关闭`
- `T440` 已补 `After Sales Ticket.on_update` 回刷，工单状态变化时会重算原单与补发单的销售订单履约状态；同时已补补发单直建、补发履约状态回写，以及补发单完成/取消后的售后工单自动关单与回退
- `T422` 已完成基础版，`Outsource Receipt / Outsource Receipt Item` 已补短装、错色、错码、次品异常字段与汇总字段；零到货的纯短装行允许留痕，但不会进入入库或质检落账
- `T422` 当前仍是轻量异常留痕口径，已补异常数量汇总与异常摘要；尚未扩展为独立异常单、对厂索赔或责任归属流程
- `T441` 已由现有售后服务承接，现已补齐库存闭环增强：售后单可直接提交库存凭证，`Stock Entry` 提交/撤销会自动回写售后工单的待检/最终处理凭证与库存闭环状态，退款后和关闭前也会真实校验最终处理库存是否已回写；补发场景下关闭前还会校验补发单是否已真实履约完成

### 3E 运营与财务分析

- 运营报表
- 财务/成本报表

当前进度：

- `T450` 已完成基础版，已新增 `Style Inventory Overview / Material Supply Overview / Outsource Receipt Overview / Sales Fulfillment Overview / After Sales Overview`
- `T450` 已把 5 张运营报表挂入 `Fashion ERP` Workspace，当前可直接从工作台进入
- `T451` 已完成基础版，已新增 `Outsource Estimated Cost Analysis / Material Procurement Cost Analysis / Fulfillment Cost Analysis`
- `T451` 已把 3 张财务/成本报表挂入 `Fashion ERP` Workspace，当前可直接从工作台进入
- `T490` 已完成基础版，已新增 `Production Board`，可直接从 `Production Ticket` 视角查看阶段分布、延期、最近日志和 BOM/工单/库存联动
- `T490` 已把 `Production Board` 挂入 `Fashion ERP` Workspace 的 `辅助生产` 卡片

### 3F 质量保障与性能收口

- 测试基础设施
- 工具函数与服务函数单元测试
- 状态机与集成测试
- 关键 N+1 查询与重复加载优化

当前规划：

- `T460`：已完成，已建立 `custom_apps/fashion_erp/tests/unit` 与 fake `frappe` 单测基座，并落地首批服务层单元测试
- `T461`：已完成，已补外包单、外包到货单、售后工单状态流转测试，以及 seed 幂等性与 SKU 主流程回归测试
- `T462`：已完成，已收口 `after_sales_service` 的明细/头信息/补发行缓存与默认公司、库存凭证类型复用；`order_sync_service` 的批次级链接/商品缓存；`sku_service.build_style_matrix / generate_variants_for_style` 的批量查询与上下文复用，以及 `style.api` 对已加载 `Style` 的服务层复用；同时补了 `outsource_service` 的外包单材料归一化缓存、`sample_service / craft_sheet_service` 的单据级元数据缓存、`sales_order_fulfillment_service` 的售后工单上下文批量读取、`after_sales_ticket` 事件的销售订单父单与订单存在性批量读取、`sales_order` 事件的售后补发回写轻量读取、`bom / work_order` 事件的生产跟踪单轻量回写、`supply_service` 的采购/收货校验缓存、`outsource_receipt_service` 的外包到货单头/库位/货品/操作人缓存、`production_service` 的生产跟踪单引用/默认公司/库存凭证类型缓存，以及 `delivery_note_fulfillment_service` 的包装耗材校验缓存，业务主线上的明显 N+1 和重复加载问题已完成本轮收口

说明：

- 这一轨道正式纳入计划
- `T460/T461` 已完成，且当前单元测试口径 `python3 -m unittest discover -s custom_apps/fashion_erp/tests/unit -p 'test_*.py'` 已通过
- 本轮 `T450 / T451 / T490` 已完成基础交付，后续仅在真实内部生产场景明确后再拆更深任务
- 后续若出现新的查询性能需求，随对应业务任务一并处理，不再单独保留 `T462`

## 第三阶段外部依赖阻塞/暂停项

- 平台 API 对接
- 自动拉单
- 自动回写平台发货状态
- 自动回写平台售后状态
- 自动退款对账

## 第三阶段明确后置

- 完整内部生产闭环
- 自动根据外包订单扣减原料库存
- 复杂车间排产
- MES / APS

## 当前优先级判断

### P0

1. 原辅料与包装耗材管理
2. 打样单
3. 工艺单
4. 外包下单与预计成本
5. 外包订单与原辅料关联
6. 外包到货入库与质检
7. 履约状态与履约成本
8. 售后闭环
9. 独立维修工单闭环

### P1

1. 外包异常处理
2. 预计成本与实际对比
3. 测试基础设施与状态机测试
4. 履约成本分析
5. 性能收口
6. 运营报表
7. 财务报表

### P2

1. 打样辅助之外的内部生产支持
2. 复杂制造对象

## 当前审查后的下一步研发计划

1. `独立维修工单闭环`

## 后续承接

具体任务拆分见：

- [fashion-erp-phase3-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-task-list.md)
