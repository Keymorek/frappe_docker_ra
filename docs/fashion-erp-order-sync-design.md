# Fashion ERP 手工订单同步设计

本文档用于承接第三阶段 `T430/T431`：

`手工订单同步策略 -> 导入批次留痕 -> 去重校验 -> 销售订单落地`

相关文档：

- 产品需求分析：[fashion-erp-product-analysis.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-product-analysis.md)
- 第三阶段实施版：[fashion-erp-phase3-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-implementation.md)
- 第三阶段任务清单：[fashion-erp-phase3-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-task-list.md)
- 标准导入模板：[fashion-erp-order-sync-template.csv](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-order-sync-template.csv)

当前文档状态：

- 仓库内已存在 `T430/T431` 的基础实现
- 但因暂时没有抖音官方稳定数据来源结构，`T430/T431` 当前统一按 `外部依赖阻塞/暂停` 处理
- 本文档保留为已有基础实现和未来恢复研发时的结构参考

## 一、范围冻结

当前手工订单同步只解决以下问题：

1. 把平台导出的订单明细手工导入 ERP
2. 在系统里保留每次导入批次和处理结果
3. 以 `channel_store + external_order_id` 作为订单级去重主键
4. 让导入结果稳定落到标准 `Sales Order / Sales Order Item`
5. 为后续 `T432-T435` 的履约状态、仓储动作和履约成本提供干净入口

当前因外部依赖阻塞/暂停：

1. 平台 API 自动拉单
2. 平台商品编码自动映射内部 SKU
3. 自动回写平台发货状态
4. 自动退款回写

当前仍不纳入本轮范围：

1. 自动创建或同步客户主数据
2. 自动拆单、合单

## 二、第一版输入前提

第一版不直接处理平台差异，先统一成“订单明细行导入”口径。

每一行代表一条订单明细，系统按 `external_order_id` 聚合成一个 `Sales Order`。

### 必填前提

1. 导入按 `Channel Store` 分批执行
2. `Channel Store` 必须先配置默认仓库、价格表
3. 第一版建议补 `Channel Store.default_company / default_customer`
4. 第一版导入必须提供内部 `item_code`，不依赖 `platform_sku` 做自动匹配

说明：

- `platform_sku` 可以保留在订单明细上，作为渠道留痕
- 但第一版不把 `platform_sku -> Item` 映射纳入主线，否则会把任务膨胀成“商品映射中心”

## 三、建议对象方案

### 1. 复用对象

- `Channel Store`
- `Sales Order`
- `Sales Order Item`

### 2. 新增对象

#### `Order Sync Batch`

用途：

- 记录一次手工导入批次
- 保存来源文件、默认上下文、统计结果和执行状态

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `batch_no` | `Data` / 命名字段 | 批次号 |
| `channel_store` | `Link -> Channel Store` | 当前导入店铺 |
| `channel` | `Data` | 从店铺回填的渠道快照 |
| `default_company` | `Link -> Company` | 默认公司 |
| `default_customer` | `Link -> Customer` | 默认客户 |
| `default_warehouse` | `Link -> Warehouse` | 默认发货仓 |
| `default_price_list` | `Link -> Price List` | 默认价格表 |
| `template_version` | `Select` | 导入模板版本 |
| `source_file_name` | `Data` | 来源文件名 |
| `source_hash` | `Data` | 文件内容摘要，用于辅助排查重复导入 |
| `batch_status` | `Select` | `草稿 / 待校验 / 待导入 / 部分导入 / 已完成 / 已取消` |
| `total_rows` | `Int` | 总行数 |
| `valid_rows` | `Int` | 校验通过行数 |
| `imported_orders` | `Int` | 成功生成订单数 |
| `duplicate_orders` | `Int` | 因重复跳过的订单数 |
| `failed_rows` | `Int` | 校验失败行数 |
| `last_import_at` | `Datetime` | 最近执行时间 |
| `remark` | `Small Text` | 备注 |
| `items` | `Table` | 导入明细行 |

#### `Order Sync Batch Item`

用途：

- 保存一条导入明细行
- 记录该行是否通过校验、是否已导入、关联到了哪张销售订单

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `row_no` | `Int` | 原始行号 |
| `external_order_id` | `Data` | 外部订单号 |
| `line_no` | `Data` | 平台行号，可选 |
| `order_date` | `Date` | 下单日期 |
| `customer` | `Link -> Customer` | 行级客户，可覆盖批次默认客户 |
| `item_code` | `Link -> Item` | 内部 SKU |
| `platform_sku` | `Data` | 平台 SKU 留痕 |
| `qty` | `Float` | 数量 |
| `rate` | `Currency` | 成交单价 |
| `biz_type` | `Select` | `零售 / 批发 / 预售 / 换货` |
| `delivery_date` | `Date` | 计划交期，可选 |
| `warehouse` | `Link -> Warehouse` | 行级仓库，可覆盖默认仓 |
| `row_status` | `Select` | `草稿 / 待导入 / 已导入 / 重复跳过 / 校验失败` |
| `sales_order` | `Link -> Sales Order` | 导入结果关联订单 |
| `sales_order_item_ref` | `Data` | 关联 `Sales Order Item.name` |
| `message` | `Small Text` | 校验或导入结果说明 |

## 四、模板字段映射

第一版模板建议固定为以下列：

| 模板列 | 是否必填 | 落点 | 说明 |
|---|---:|---|---|
| `external_order_id` | 是 | `Sales Order.external_order_id` | 订单主键的一部分 |
| `order_date` | 是 | `Sales Order.transaction_date` | 订单日期 |
| `item_code` | 是 | `Sales Order Item.item_code` | 必须是内部 SKU |
| `qty` | 是 | `Sales Order Item.qty` | 非负数且大于 0 |
| `rate` | 否 | `Sales Order Item.rate` | 默认可为 `0` |
| `biz_type` | 否 | `Sales Order.biz_type` | 默认 `零售` |
| `delivery_date` | 否 | `Sales Order.delivery_date` / Item `delivery_date` | 默认取 `order_date` |
| `warehouse` | 否 | `Sales Order Item.warehouse` | 默认取店铺仓库 |
| `platform_sku` | 否 | `Sales Order Item.platform_sku` | 仅留痕 |
| `line_no` | 否 | `Order Sync Batch Item.line_no` | 排查重复行用 |
| `customer` | 否 | `Sales Order.customer` | 默认取批次或店铺默认客户 |

当前仓库已提供标准模板文件：

- [fashion-erp-order-sync-template.csv](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-order-sync-template.csv)

使用说明：

1. 第一行保留字段名，不要改列顺序
2. 第二行只是示例值，正式导入前应替换成真实数据
3. `item_code` 必须填写内部 SKU，不接受平台 SKU 直导

当前已落地入口：

1. 可在 `Order Sync Batch` 表单使用“导入 CSV”动作粘贴模板内容
2. 支持 `覆盖现有明细 / 追加明细` 两种模式
3. 导入后会回写 `source_file_name / source_hash`

第一版字段映射原则：

1. 优先复用店铺默认值，不在模板里强塞大量 ERP 字段
2. 第一版模板只接最小必要列，不承接地址、物流、平台备注等扩展字段
3. `Sales Order Item.style / color_code / color_name / size_code / size_name` 由服务端按 `Item` 自动补齐

## 五、去重与分组规则

### 1. 订单级主键

订单级去重主键冻结为：

`channel_store + external_order_id`

说明：

- 同一平台单号在不同店铺可以共存
- 同一店铺下，不允许存在两张未取消的相同外部订单号

### 2. 批次内分组规则

同一批次中：

1. 相同 `external_order_id` 的多行，视为同一张订单的多条明细
2. 如果同一订单号下出现不同 `customer / order_date / biz_type`，视为批次数据冲突，整单校验失败
3. `line_no` 仅用于问题排查，不作为订单分组主键

### 3. 与现有订单的去重规则

1. 若已存在 `docstatus < 2` 且 `channel_store + external_order_id` 相同的 `Sales Order`，整单标记为 `重复跳过`
2. 若仅存在已取消订单，可允许重新导入
3. 去重判断必须走服务端，不只依赖前端提示

### 4. 后续建议

后续实现时应补：

1. `Sales Order(channel_store, external_order_id)` 组合索引
2. 保存前的服务端重复校验

当前状态：

- 服务端重复校验已落在 `Sales Order.validate`
- 数据库组合索引已补 patch，待站点执行 migrate 后落库
- 批次已支持站内粘贴 CSV 内容导入
- 附件上传式导入仍待后续增强

## 六、导入动作设计

第一版建议拆成两个动作：

### A. 校验批次

目标：

- 不创建销售订单
- 只做标准化、字段校验、分组检查和重复预判

输出：

1. 回写批次统计字段
2. 回写每行 `row_status / message`
3. 把批次推进到 `待导入` 或保留在 `草稿`

### B. 执行导入

目标：

- 按已通过校验的订单分组创建 `Sales Order`
- 每张订单创建成功后，回写对应行和批次统计

输出：

1. 更新 `sales_order / sales_order_item_ref`
2. 将对应行推进到 `已导入`
3. 批次按结果推进到 `已完成 / 部分导入`

## 七、服务端分层建议

建议把主逻辑放在服务层，不把导入逻辑写死在 DocType 控制器里。

### 建议文件

1. `fashion_erp/channel/services/order_sync_service.py`
2. `fashion_erp/channel/doctype/order_sync_batch/order_sync_batch.py`
3. `fashion_erp/channel/doctype/order_sync_batch_item/order_sync_batch_item.json`

### 服务层建议函数

1. `validate_order_sync_batch(doc)`
   - 标准化批次和行数据
   - 回填店铺默认值
   - 计算统计字段
2. `preview_order_sync_batch(batch_name)`
   - 输出按订单聚合后的预览结果
   - 给前端或按钮动作使用
3. `execute_order_sync_batch(batch_name)`
   - 创建销售订单
   - 回写行状态和批次统计
4. `_build_sales_order_payload(order_group, batch_doc)`
   - 生成标准 `Sales Order` payload
5. `_enrich_sales_order_item_from_item(item_code)`
   - 自动补齐 `style / color / size`

## 八、与后续任务的边界

### 本任务负责

1. 订单导入
2. 批次留痕
3. 去重
4. 销售订单落地

### 本任务不负责

1. 履约状态字段
2. 拣货、打包、发货动作
3. 包装耗材挂单
4. 快递费与履约成本
5. 售后回写订单闭环

这些分别留给：

- `T432`
- `T433`
- `T434`
- `T435`
- `T440`

## 九、建议实现切片

### Slice 1：批次对象与默认值

交付：

1. `Order Sync Batch / Item`
2. `Channel Store` 默认导入上下文字段
3. 批次基础校验

### Slice 2：校验与去重预览

交付：

1. 批次校验动作
2. 订单分组
3. 重复订单识别
4. 行级错误信息

### Slice 3：执行导入

交付：

1. 创建 `Sales Order`
2. 自动补齐订单行款色码
3. 回写批次与行结果

### Slice 4：入口与可用性

交付：

1. Workspace 入口
2. 批次表单按钮
3. 导入结果摘要视图

## 十、第一版验收标准

完成后应至少满足：

1. 可以创建一张手工订单同步批次
2. 批次能记录来源店铺、来源文件和导入明细
3. 系统能按 `channel_store + external_order_id` 做服务端去重
4. 同一订单号的多行能聚合成一张 `Sales Order`
5. 创建出的订单明细能自动带出 `style / color_code / color_name / size_code / size_name`
6. 重复订单不会重复创建，批次中能看到“重复跳过”结果
7. 校验失败行不会阻塞其它有效订单导入
8. 批次能看到总行数、成功数、重复数、失败数

## 十一、当前建议结论

`T430/T431` 的正确实现方式不是直接往 `Sales Order` 上继续堆字段，
而是先补一层 `Order Sync Batch` 作为导入留痕和校验入口，
再由服务端把干净数据稳定落入标准销售订单。
