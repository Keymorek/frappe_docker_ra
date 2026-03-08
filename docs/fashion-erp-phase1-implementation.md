# Fashion ERP 第一期实施版

本文档是 `fashion_erp` 的第一期实施方案，基于
[fashion-erp-doctype-design.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-doctype-design.md)
中的评审结论进一步收敛而成。

相关文档：

- 总体字段设计：[fashion-erp-doctype-design.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-doctype-design.md)
- 第一期任务清单：[fashion-erp-phase1-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-task-list.md)
- 第一期文件级实现清单：[fashion-erp-phase1-file-map.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-file-map.md)

定位：

- 这不是总蓝图文档
- 这是“当前要做什么、不做什么、先做什么”的实施文档
- 后续开发、建表、排期、验收，以本文件为准

## 一期目标

第一期目标不是一次性做完整 ERP，而是先把最关键的行业主数据和 SKU 逻辑跑通：

`Style -> Color -> Size -> SKU(Item) -> 销售/库存/生产引用`

第一期完成后，你应该能做到：

- 建立女装行业化的 `Style` 主档
- 为每个款式定义允许颜色
- 定义尺码体系和尺码代码
- 按规则自动生成 SKU
- 在 ERPNext 的 `Item` 上承载 SKU
- 在订单、库存、工单中追踪款色码
- 为下一期仓储、渠道、电商同步做准备

## 一期分阶段

### Phase 1A：主数据与 SKU

本阶段必须完成：

1. `Style`
2. `Style Color`
3. `Color Group`
4. `Color`
5. `Size System`
6. `Size Code`
7. `Item` 自定义字段扩展
8. SKU 编码规则
9. `Generate Variants` 服务逻辑
10. `Style Matrix` 页面

### Phase 1B：轻量生产跟踪

本阶段建议完成，但不应阻塞 1A：

1. `Production Ticket`
2. `Production Stage Log`
3. `BOM` 扩展字段
4. `Work Order` 扩展字段
5. `Stock Entry Detail` 扩展字段
6. `Production Ticket -> Work Order / Stock Entry` 草稿联动
7. `Production Ticket -> BOM` 草稿联动

## 一期明确不做

以下内容不进入第一期开发范围：

- 独立 `SKU` 主表
- 完整库位主档和库位分配逻辑
- 电商平台接口
- 订单自动同步
- 库存状态机
- 售后状态机
- 退货原因与退货结果自动化
- 完整 BOM 自动生成
- 完整面辅料精细化管理
- 高级排产 / APS / MES

## 一期核心技术决策

### 0. T000 已冻结

以下 3 个业务口径已冻结，不再继续讨论：

1. `category / sub_category` 最终口径为字典表
2. `default_location` 最终口径为字典表
3. `Production Ticket` 继续归在 `1B`

补充说明：

- 当前代码已把 `category / sub_category` 落成字典表
- 当前代码已把 `default_location` 落成字典表
- 历史文本值通过 `migrate_phase1_dictionary_links.py` 迁移进入字典对象

### 2026-03-08 Style 验收补充实现

本轮已按 `Style` 验收意见完成第一批基础模型重构：

- `brand` 改为保存前必填。
- 新增 `Style Category Template`，用于承载 `1-4` 级类目路径；`Style` 只选择最终类目，同时回显一级到四级与全路径。
- `season` 改为 `Style Season` 主数据引用。
- `year` 改为 `Style Year` 主数据引用。
- 新增 `Fabric Master`，`Style` 上的 `主面料 / 里料` 改为引用同一张面料档案。
- `item_group` 保留，但界面文案改为 `成品物料组`。

这一批没有处理 `Style Size / 尺码选择 / 更换 size system 锁定`，该部分留给下一批 `9 + 10` 收口。

### 2026-03-08 Style 尺码批次收口

第二批已完成，核心口径如下：

- `Style Category Template` 负责给 `Style` 提供 `default_size_system / allowed_size_systems`。
- `Style` 不再按整个 `size_system` 全量生成 SKU，而是通过 `Style Size` 子表维护“本款实际尺码”。
- `款色码矩阵`、`SKU 生成`、`生产跟踪单尺码范围` 已改为读取 `Style Size`。
- 当款号下已经存在生成出的 SKU 时，`size_system` 与 `Style Size` 都会被锁定，防止同一款号下出现两套尺码语义。
- `Style` 相关中文化已补齐剩余缺口，新增 `Style Color` 翻译，并将 `Fabric Master` 的 `MOQ` 标签改为 `起订量(MOQ)`。
- 为了收口 `Launch Status` 中英混用，新增了样式状态清洗 patch；站点执行 `migrate` 后会把 `launch_status / sales_status / season / gender` 的历史英文值统一转换成中文。
- `Style Category Template` 现已按真实抖音数据集收口导入链：支持读取 `平台 / 原始模版文本` 列，支持从表单直接“同步内置抖音类目模板”，并关闭 `quick_entry`，避免误把一级类目当成唯一节点维护。
- `Style` 模块主数据权限已从仅 `System Manager` 扩展到 `Stock Manager`，便于业务验收账号直接维护类目、季节、年份、面料、尺码和款号主档。

### 1. SKU 不单独建主表

第一期不创建独立 `SKU` DocType。

原因：

- ERPNext 已有标准 `Item`
- 库存、条码、价格、物料交易都围绕 `Item`
- 如果重复做一个 `SKU` 主表，会产生双主档问题

结论：

- 业务上继续使用“SKU 层”这个概念
- 技术实现上，第一期由 `Item` 承载 SKU

### 2. `item_group` 不删除

虽然业务上会新增 `category / sub_category`，但 `Item Group` 仍保留为 ERPNext 系统映射字段。

结论：

- 业务分类：`category + sub_category`，且最终应为字典表
- 系统映射：`item_group`

### 3. `item_template` 保留

`Style` 上保留 `item_template`。

原因：

- 未来 Variant、价格、标准 ERPNext 逻辑仍可能依赖模板货品
- 便于和标准物料体系对接

### 4. `Style` 保留“允许颜色”层

即使 SKU 上也有颜色，`Style` 仍保留颜色子表。

原因：

- 款式规划需要知道“这个款允许哪些颜色”
- SKU 生成逻辑需要有来源
- 颜色矩阵也依赖这一层

## 一期最终对象清单

### 自定义 DocType

| 对象 | 期次 | 说明 |
|---|---|---|
| `Style` | 1A | 款号主档 |
| `Style Color` | 1A | 款式允许颜色子表 |
| `Color Group` | 1A | 主颜色代码字典 |
| `Color` | 1A | 具体颜色字典 |
| `Size System` | 1A | 尺码体系字典 |
| `Size Code` | 1A | 尺码代码字典 |
| `Channel Store` | 1A | 渠道店铺主档 |
| `Production Ticket` | 1B | 轻量生产卡 |
| `Production Stage Log` | 1B | 生产日志子表 |

### 扩展标准 DocType

| 对象 | 期次 | 说明 |
|---|---|---|
| `Item` | 1A | 承载 SKU |
| `Sales Order` | 1A | 渠道来源信息 |
| `Sales Order Item` | 1A | 款色码明细 |
| `BOM` | 1B | 款号、生产卡关联与辅助创建 |
| `Work Order` | 1B | 款号和生产卡扩展 |
| `Purchase Order` | 1B | 款号和预计使用信息 |
| `Stock Entry Detail` | 1B | 款色码与生产卡追踪 |

## 一期数据模型

### 1. Style

第一期 `Style` 最终保留字段：

| 字段代码 | 是否一期实现 | 说明 |
|---|---|---|
| `style_code` | 是 | 款号 |
| `style_name` | 是 | 款名 |
| `brand` | 是 | 品牌 |
| `category` | 是 | 一级品类，最终口径为字典表 |
| `sub_category` | 是 | 二级品类，最终口径为字典表 |
| `item_group` | 是 | ERPNext 品类映射 |
| `season` | 是 | 季节 |
| `year` | 是 | 年份 |
| `gender` | 是 | 性别 |
| `design_owner` | 是 | 设计负责人 |
| `size_system` | 是 | 尺码体系 |
| `item_template` | 是 | 模板货品 |
| `fabric_main` | 是 | 主面料摘要 |
| `fabric_lining` | 是 | 里料摘要 |
| `target_cost` | 是 | 目标成本 |
| `tag_price` | 是 | 吊牌价 |
| `launch_status` | 是 | 上市状态 |
| `sales_status` | 是 | 销售状态 |
| `cover_image` | 是 | 主图 |
| `description` | 是 | 款式说明 |
| `colors` | 是 | 款式允许颜色 |
| `wave` | 否 | 降级为可选规划字段 |
| `materials` | 否 | 不作为一期核心 |

### 2. Color Group

第一期预置主颜色代码：

| 主颜色名称 | 代码 |
|---|---|
| 白色系 | `WHT` |
| 黑色系 | `BLK` |
| 灰色系 | `GRY` |
| 蓝色系 | `BLU` |
| 红色系 | `RED` |
| 粉色系 | `PNK` |
| 绿色系 | `GRN` |
| 棕色系 | `BRN` |
| 卡其色系 | `KHK` |
| 黄色系 | `YLW` |

### 3. Color

第一期至少支持：

| 具体颜色 | 主颜色 |
|---|---|
| 奶油白 | `WHT` |
| 米白 | `WHT` |
| 象牙白 | `WHT` |
| 本白 | `WHT` |
| 冷白 | `WHT` |

说明：

- 这个字典后续继续扩
- 先不要用自由文本随便填

### 4. Size System

第一期预置尺码体系：

| 尺码体系名称 | 代码 | 适用商品 |
|---|---|---|
| 上装尺码 | `TOP` | T恤、衬衫、针织衫、卫衣、外套 |
| 连衣裙尺码 | `DRESS` | 连衣裙 |
| 裤装尺码 | `BOTTOM` | 牛仔裤、休闲裤 |
| 半裙尺码 | `SKIRT` | 短裙、长裙 |
| 鞋类尺码 | `SHOE` | 女鞋 |
| 均码体系 | `FREE` | 均码商品 |
| 内衣尺码 | `BRA` | 内衣 |
| 配饰尺码 | `ACC` | 帽子、围巾、腰带等 |

### 5. Size Code

第一期建议预置的基础尺码代码：

通用服装尺码：

| `size_code` | `size_name` |
|---|---|
| `XXS` | `XXS` |
| `XS` | `XS` |
| `S` | `S` |
| `M` | `M` |
| `L` | `L` |
| `XL` | `XL` |
| `XXL` | `2XL` |
| `XXXL` | `3XL` |
| `F` | `F` |

裤装尺码：

| `size_code` | `size_name` |
|---|---|
| `24` | `24` |
| `25` | `25` |
| `26` | `26` |
| `27` | `27` |
| `28` | `28` |
| `29` | `29` |
| `30` | `30` |
| `31` | `31` |
| `32` | `32` |

均码：

| `size_code` | `size_name` |
|---|---|
| `ONE` | `OneSize` |

### 6. Item 作为 SKU 层

第一期 `Item` 必须承载这些业务字段：

| 业务概念 | 落地位置 | 说明 |
|---|---|---|
| `sku_code` | `Item.item_code` | SKU 编码本体 |
| `style` | 自定义字段 | 关联 `Style` |
| `style_code` | 自定义字段 | 冗余款号编码 |
| `color_code` | 自定义字段 | 主颜色代码 |
| `color_name` | 自定义字段 | 具体颜色名 |
| `size_system` | 自定义字段 | 尺码体系 |
| `size_code` | 自定义字段 | 尺码代码 |
| `size_name` | 自定义字段 | 尺码名 |
| `barcode` | 标准字段 | 复用 ERPNext 条码 |
| `weight` | 标准字段 | 复用 ERPNext 重量 |
| `safe_stock` | 自定义字段 | 安全库存 |
| `default_location` | 自定义字段 | 已切换为 `Link -> Warehouse Location` |
| `sellable` | 自定义字段 | 是否可售 |
| `sku_status` | 自定义字段 | SKU 状态 |
| `batch_enable` | 标准字段 | 复用 ERPNext 批次开关 |
| `remark` | 自定义字段 | 备注 |

## 一期编码规则

### Style 编码

建议格式：

`品牌简称-YY季-品类-流水号`

示例：

`RS-26SS-DR-0001`

### SKU 编码

建议格式：

`RL-款式-主颜色-尺码代码`

示例：

`RL-RS26S001-BLK-M`

实现建议：

- 直接作为 `Item.item_code`
- 自动生成，不允许手工随意修改
- 品牌简写来自 `Brand.brand_abbr`

### 库位编码

库位编码不进入第一期主开发范围，但编码规则先冻结：

`地区-仓库编号-区域-货架-层-位`

示例：

`SH-A01-FG-A03-02-01`

## 一期页面

### Style Matrix

必须实现：

- 以 `Style` 为主入口
- 按颜色 x 尺码展示 SKU
- 显示是否已生成 SKU
- 显示库存概览
- 提供批量生成缺失 SKU 的入口

一期最小字段展示：

- 行：颜色
- 列：尺码
- 单元格：SKU 编码 / 是否可售 / 简单库存数

### Style 表单按钮

必须保留：

- `Create Template Item`
- `Generate Variants`
- `Open Matrix`

可以延后：

- `Create BOM`
- 独立 `Style Matrix` Desk Page

当前已落地的表单入口：

- `Create Template Item`
- `Generate Variants`
- `Open Matrix`
- `Create Production Ticket`

Desk 入口策略：

- 保留 `desktop.py` 模块定义
- 增加标准 `Workspace`，让 `Fashion ERP` 在 Desk 侧边栏更稳定可见

## 一期开发顺序

### 第 1 步：主数据字典

先建：

1. `Color Group`
2. `Color`
3. `Size System`
4. `Size Code`

原因：

- 没有主数据字典，`Style` 和 SKU 都不稳定

### 第 2 步：Style

完成：

1. `Style` 主表
2. `Style Color` 子表
3. `launch_status / sales_status`
4. `category / sub_category / item_group`

### 第 3 步：Item 扩展

完成：

1. `Item` 自定义字段
2. SKU 编码规则
3. `Style -> Item` 的数据映射规则

### 第 4 步：Generate Variants

完成：

1. 从 `Style.colors + size_system` 生成 SKU
2. 自动写入 `Item.item_code`
3. 自动带出款号、颜色、尺码、自定义字段
4. 避免重复生成

### 第 5 步：Style Matrix

完成：

1. 矩阵展示
2. 缺失 SKU 检查
3. 一键补齐 SKU

### 第 6 步：Production Ticket

在 1A 稳定后做：

1. `Production Ticket`
2. `Production Stage Log`
3. 与 `BOM` 的轻量关联
4. 与 `Work Order` 的轻量关联
5. 从 `Production Ticket` 预填 `BOM` 草稿
6. 从 `Production Ticket` 预填 `Work Order` 草稿
7. 从 `Production Ticket` 预填 `Stock Entry` 草稿
8. `BOM` 保存后自动回写 `Production Ticket.bom_no`
9. `Work Order` 保存后自动回写 `Production Ticket.work_order`
10. `Create BOM` 支持从已有 `Source BOM` 复制 `BOM Item / Operation`

## 一期验收标准

当以下条件全部满足时，视为一期完成：

1. 可以录入 `Style`
2. `Style` 可以选择颜色和尺码体系
3. 系统可按规则生成 SKU
4. SKU 正确落在 `Item`
5. SKU 编码符合命名规则
6. `Item` 上能看到款号、颜色、尺码、自定义状态字段
7. 销售订单明细能带出款号、颜色、尺码信息
8. 可以通过矩阵页面检查某款颜色尺码是否齐全
9. 不依赖手工逐个创建 SKU

如果 `1B` 同步验收，则还应满足：

10. 可以从 `Production Ticket` 生成预填 `Work Order` 草稿
11. 可以从 `Production Ticket` 生成预填 `Stock Entry` 草稿
12. 可以从 `Production Ticket` 生成预填 `BOM` 草稿
13. `BOM / Work Order` 和 `Production Ticket` 关联会自动回写和同步
14. 需要时可以从现有 `BOM` 复制材料行和工序到新 `BOM` 草稿

## 一期后续衔接

第一期完成后，下一阶段优先进入：

1. 仓储与库位
2. 库存状态流转
3. 手工订单同步与履约状态
4. 外包来货入库与质检
5. 售后与退货字典

补充说明：

- 电商订单同步及平台状态自动回写当前统一按 `外部依赖阻塞/暂停` 处理，现阶段只保留手工同步
- 当前二阶段已完成仓储与状态流转基础
- 当前主路线已切换为电商运营履约与第三方外包入库
- 详见 [fashion-erp-product-analysis.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-product-analysis.md)
- 详见 [fashion-erp-phase3-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-implementation.md)

## 冻结项落地结果

`T000` 已完成，且冻结结论已落到代码：

1. 已增加 `Style Category`
2. 已增加 `Style Sub Category`
3. 已增加 `Warehouse Location`
4. 已把 `Style.category / sub_category` 改为 `Link`
5. 已把 `Item.default_location` 改为 `Link`
6. 已增加历史数据迁移 patch
