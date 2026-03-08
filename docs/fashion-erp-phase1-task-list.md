# Fashion ERP 第一期开发任务清单

本文档是 `fashion_erp` 第一阶段的任务级执行清单。

关联文档：

- 总体字段设计：[fashion-erp-doctype-design.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-doctype-design.md)
- 第一期实施版：[fashion-erp-phase1-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-implementation.md)
- 第一期文件级实现清单：[fashion-erp-phase1-file-map.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-file-map.md)

用途：

- 把第一期方案拆成可执行任务
- 明确任务先后顺序、依赖、交付物和验收标准
- 后续开发排期、分工、验收以本文件为准

## 使用方式

建议按以下节奏推进：

1. 先完成 `准备阶段`
2. 再完成 `Phase 1A 主数据与 SKU`
3. 最后完成 `Phase 1B 轻量生产跟踪`

任务状态建议统一使用：

- `TODO`
- `DOING`
- `DONE`
- `BLOCKED`

## 里程碑

| 里程碑 | 目标 | 完成标准 |
|---|---|---|
| `M0` | 需求冻结 | 一期字段、编码、对象范围冻结 |
| `M1` | 主数据可维护 | 能维护颜色、尺码、款号基础数据 |
| `M2` | SKU 可自动生成 | `Style` 可一键生成 SKU 到 `Item` |
| `M3` | 矩阵可视化 | 能用矩阵查看某款颜色尺码覆盖情况 |
| `M4` | 生产轻量跟踪 | 可建立 `Production Ticket` 并记录流转 |

## 当前进度盘点

截至当前代码状态：

- `M0` 已完成
- `M1` 已完成
- `M2` 已完成
- `M3` 已完成
- `M4` 已基本完成

当前阻塞点已经不在一期骨架，而在两类事项：

1. 服务器侧还需要持续做真实业务流验证，而不是只看结构和安装结果
2. 二阶段仍有后续待做项，但当前范围已冻结为仓储与状态流转

## 准备阶段

### T000 需求冻结

| 项目 | 内容 |
|---|---|
| 任务编号 | `T000` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 需求确认 |
| 目标 | 冻结第一期字段和范围 |
| 依赖 | 无 |
| 交付物 | 更新后的三份文档 |
| 验收标准 | 文档中不再存在一阶段对象定义冲突 |

已冻结结论：

1. `category / sub_category` 业务口径冻结为字典表
2. `default_location` 业务口径冻结为字典表
3. `Production Ticket` 继续归在 `1B`

补充说明：

- 当前代码已落地 `Style Category`、`Style Sub Category`、`Warehouse Location`
- `Style.category / sub_category` 已切换为 `Link`
- `Item.default_location` 已切换为 `Link`
- `migrate_phase1_dictionary_links.py` 会把历史文本值迁移到字典表

### 2026-03-08 Style 验收收口补充

- `Style.brand` 已改为必填，并在保存时做服务端校验。
- `Style.category / sub_category` 退居为隐藏兼容字段；当前正式使用的是 `product_category -> Style Category Template`。
- 新增 `Style Category Template`，按 `一级/二级/三级/四级/全路径` 建档，种子数据直接读取 `docs/抖音抖店女装服饰内衣类目.csv`。
- `Style.season` 已改成 `Link -> Style Season`。
- `Style.year` 已改成 `Link -> Style Year`。
- `Style.fabric_main / fabric_lining` 已改成 `Link -> Fabric Master`。
- `Style.item_group` 的界面口径已改成 `成品物料组`，用于和原辅料语义区分。
- `Style Category Template` 已增加 `默认尺码体系 + 允许尺码体系` 规则字段。
- `Style` 已增加 `Style Size` 子表，SKU 与矩阵只按本款已选尺码生成。
- 一旦款号已经生成 SKU，系统会锁定 `size_system` 和 `本款尺码`，不能再直接修改。
- `Style` 验收剩余中文化项已收口，补齐了 `Style Color` 等翻译，并把 `Fabric Master.MOQ` 改为中文显示 `起订量(MOQ)`。
- `Style.launch_status / sales_status` 已补新增量 patch，站点 `migrate` 后会把历史英文值统一清洗为中文。
- `Style Category Template` 已关闭 `quick_entry`，并支持“同步内置抖音类目模板”；抖音模板口径下不再允许只建一级类目。
- `Style` 模块主数据 Doctype 已补充 `Stock Manager` 权限，避免业务验收继续被 `System Manager` 权限卡住。

### T001 应用骨架初始化

| 项目 | 内容 |
|---|---|
| 任务编号 | `T001` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 应用初始化 |
| 目标 | 创建 `fashion_erp` 应用骨架 |
| 依赖 | `T000` |
| 交付物 | app 目录、模块目录、基础 hooks |
| 验收标准 | 应用可安装到开发站点 |

建议输出：

- `fashion_erp/style`
- `fashion_erp/channel`
- `fashion_erp/garment_mfg`
- `fashion_erp/reporting`
- `fashion_erp/setup`

### T002 命名与字典预置策略

| 项目 | 内容 |
|---|---|
| 任务编号 | `T002` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 规则设计 |
| 目标 | 固定编码规则和初始字典导入方式 |
| 依赖 | `T000` |
| 交付物 | fixture 或 patch 方案 |
| 验收标准 | 主颜色、颜色、尺码体系、尺码代码可被初始化导入 |

输出建议：

- `Color Group` 初始数据
- `Color` 初始数据
- `Size System` 初始数据
- `Size Code` 初始数据

## Phase 1A 主数据与 SKU

### T100 Color Group DocType

| 项目 | 内容 |
|---|---|
| 任务编号 | `T100` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 自定义 DocType |
| 目标 | 建立主颜色代码字典 |
| 依赖 | `T002` |
| 交付物 | `Color Group` DocType |
| 验收标准 | 可维护 `WHT/BLK/RED...` 等主颜色代码 |

需要实现：

- `color_group_code`
- `color_group_name`
- `sort_order`
- `enabled`
- `remark`

### T101 Color DocType

| 项目 | 内容 |
|---|---|
| 任务编号 | `T101` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 自定义 DocType |
| 目标 | 建立具体颜色字典 |
| 依赖 | `T100` |
| 交付物 | `Color` DocType |
| 验收标准 | 具体颜色必须归属一个主颜色 |

需要实现：

- `color_name`
- `color_group`
- `enabled`
- `remark`

### T102 Size System DocType

| 项目 | 内容 |
|---|---|
| 任务编号 | `T102` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 自定义 DocType |
| 目标 | 建立尺码体系字典 |
| 依赖 | `T002` |
| 交付物 | `Size System` DocType |
| 验收标准 | 可维护 `TOP/DRESS/BOTTOM/FREE` 等体系 |

### T103 Size Code DocType

| 项目 | 内容 |
|---|---|
| 任务编号 | `T103` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 自定义 DocType |
| 目标 | 建立尺码代码字典 |
| 依赖 | `T102` |
| 交付物 | `Size Code` DocType |
| 验收标准 | 同一尺码体系下，尺码代码唯一 |

需要实现：

- `size_system`
- `size_code`
- `size_name`
- `sort_order`
- `enabled`

### T104 Style Category DocType

| 项目 | 内容 |
|---|---|
| 任务编号 | `T104` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 类型 | 自定义 DocType |
| 目标 | 把 `Style.category` 从文本升级为字典表 |
| 依赖 | `T000` |
| 交付物 | `Style Category` DocType |
| 验收标准 | `Style.category` 可引用受控分类，而不是自由文本 |

当前实现说明：

- 已新增 `Style Category` DocType
- `Style.category` 已改为 `Link`
- 已在 Workspace 中增加入口

### T105 Style Sub Category DocType

| 项目 | 内容 |
|---|---|
| 任务编号 | `T105` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 类型 | 自定义 DocType |
| 目标 | 把 `Style.sub_category` 从文本升级为字典表 |
| 依赖 | `T000`, `T104` |
| 交付物 | `Style Sub Category` DocType |
| 验收标准 | `Style.sub_category` 可引用受控二级分类，并受一级分类约束 |

当前实现说明：

- 已新增 `Style Sub Category` DocType
- `Style.sub_category` 已改为 `Link`
- `Style` 表单已增加按 `category` 过滤 `sub_category` 的查询逻辑
- 服务端保存时会校验二级分类必须归属当前一级分类

### T110 Style DocType

| 项目 | 内容 |
|---|---|
| 任务编号 | `T110` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 自定义 DocType |
| 目标 | 建立女装行业化款号主档 |
| 依赖 | `T100`, `T101`, `T102` |
| 交付物 | `Style` DocType |
| 验收标准 | 可维护款号、分类、状态、面料摘要、颜色和尺码体系 |

必须字段：

- `style_code`
- `style_name`
- `brand`
- `category`
- `sub_category`
- `item_group`
- `season`
- `year`
- `gender`
- `design_owner`
- `size_system`
- `item_template`
- `fabric_main`
- `fabric_lining`
- `target_cost`
- `tag_price`
- `launch_status`
- `sales_status`
- `cover_image`
- `description`

### T111 Style Color 子表

| 项目 | 内容 |
|---|---|
| 任务编号 | `T111` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 子表 |
| 目标 | 定义款式允许颜色 |
| 依赖 | `T101`, `T110` |
| 交付物 | `Style Color` 子表 |
| 验收标准 | 同一款下不可重复选择颜色 |

必须字段：

- `color`
- `color_name`
- `color_code`
- `sort_order`
- `enabled`

### T120 Item 扩展字段

| 项目 | 内容 |
|---|---|
| 任务编号 | `T120` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | `Custom Field` |
| 目标 | 把标准 `Item` 扩展成 SKU 载体 |
| 依赖 | `T110`, `T111`, `T102`, `T103` |
| 交付物 | `Item` 自定义字段 |
| 验收标准 | `Item` 可承载款色码和运营字段 |

必须新增字段：

- `style`
- `style_code`
- `color_code`
- `color_name`
- `size_system`
- `size_code`
- `size_name`
- `safe_stock`
- `default_location`
- `sellable`
- `sku_status`
- `remark`

复用标准字段：

- `item_code` 作为 `sku_code`
- 标准条码字段
- 标准重量字段
- 标准批次开关字段

### T121 SKU 编码服务

| 项目 | 内容 |
|---|---|
| 任务编号 | `T121` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 服务端逻辑 |
| 目标 | 生成标准 SKU 编码 |
| 依赖 | `T110`, `T111`, `T120` |
| 交付物 | SKU 编码函数 |
| 验收标准 | 输入款号、颜色、尺码后能稳定生成唯一 SKU 编码 |

规则：

`RL-款式-主颜色-尺码代码`

示例：

`RL-RS26S001-BLK-M`

补充：

- `RL` 是 `Rosalyth` 当前配置值
- 系统正式读取 `Brand.brand_abbr`
- 新品牌上线时可在系统内自定义维护对应简写

### T122 Generate Variants 服务

| 项目 | 内容 |
|---|---|
| 任务编号 | `T122` |
| 优先级 | `P0` |
| 状态 | `DONE` |
| 类型 | 服务端逻辑 |
| 目标 | 从 `Style` 自动生成 SKU 到 `Item` |
| 依赖 | `T110`, `T111`, `T120`, `T121`, `T103` |
| 交付物 | `Generate Variants` 方法 |
| 验收标准 | 一次操作可批量生成缺失 SKU，且不会重复生成 |

必须实现：

- 按 `Style.colors` 遍历颜色
- 按 `Style.size_system` 对应的 `Size Code` 遍历尺码
- 自动创建或补全 `Item`
- 自动写入扩展字段
- 自动写入 `item_code`
- 已存在 SKU 时跳过

### T123 Style 表单按钮

| 项目 | 内容 |
|---|---|
| 任务编号 | `T123` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 类型 | 表单交互 |
| 目标 | 在 `Style` 上提供关键动作入口 |
| 依赖 | `T122` |
| 交付物 | 表单按钮与调用逻辑 |
| 验收标准 | 用户可从 `Style` 表单发起生成动作 |

第一期必须按钮：

- `Create Template Item`
- `Generate Variants`
- `Open Matrix`
- `Create Production Ticket`

### T130 Style Matrix 页面

| 项目 | 内容 |
|---|---|
| 任务编号 | `T130` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 类型 | 页面 |
| 目标 | 可视化查看某款颜色尺码覆盖情况 |
| 依赖 | `T110`, `T111`, `T122` |
| 交付物 | `Style Matrix` 页面 |
| 验收标准 | 能直观看到某款颜色 x 尺码是否齐全 |

一期最小要求：

- 选择一个 `Style`
- 行展示颜色
- 列展示尺码
- 单元格展示 `SKU编码 / 是否存在 / 是否可售 / 简单库存`
- 可一键补齐缺失 SKU

当前实现说明：

- 先通过 `Style` 表单上的 `Open Matrix` 弹窗提供矩阵视图
- 后续如需要独立工作台，再升级为专门的 Desk Page

### T140 销售与库存引用字段

| 项目 | 内容 |
|---|---|
| 任务编号 | `T140` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 类型 | `Custom Field` |
| 目标 | 在业务单据中追踪款色码 |
| 依赖 | `T120` |
| 交付物 | 标准单据扩展字段 |
| 验收标准 | 销售和库存相关单据能追踪款号、颜色、尺码 |

第一期要补的字段：

- `Sales Order.channel`
- `Sales Order.channel_store`
- `Sales Order.external_order_id`
- `Sales Order.biz_type`
- `Sales Order Item.style`
- `Sales Order Item.color_code`
- `Sales Order Item.color_name`
- `Sales Order Item.size_code`
- `Sales Order Item.size_name`
- `Sales Order Item.platform_sku`
- `Sales Order Item.is_presale`
- `Stock Entry Detail.style`
- `Stock Entry Detail.color_code`
- `Stock Entry Detail.size_code`

### T141 Warehouse Location 字典与默认库位迁移

| 项目 | 内容 |
|---|---|
| 任务编号 | `T141` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 类型 | 自定义 DocType + 字段迁移 |
| 目标 | 把 `Item.default_location` 从文本升级为库位字典关联 |
| 依赖 | `T000`, `T120` |
| 交付物 | `Warehouse Location` 字典、`Item.default_location` 迁移方案 |
| 验收标准 | `Item.default_location` 改为 `Link`，引用受控库位主档 |

当前实现说明：

- 已新增 `Warehouse Location` DocType
- `Item.default_location` 已改为 `Link -> Warehouse Location`
- 已新增 `migrate_phase1_dictionary_links.py` 迁移 patch
- `Fashion ERP` Workspace 已增加 `Warehouse Locations` 入口

## Phase 1B 轻量生产跟踪

### T200 Production Ticket

| 项目 | 内容 |
|---|---|
| 任务编号 | `T200` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 类型 | 自定义 DocType |
| 目标 | 建立轻量生产批次卡 |
| 依赖 | `T110`, `T120` |
| 交付物 | `Production Ticket` DocType |
| 验收标准 | 可按款号和颜色发起生产跟踪 |

### T201 Production Stage Log

| 项目 | 内容 |
|---|---|
| 任务编号 | `T201` |
| 优先级 | `P1` |
| 状态 | `DONE` |
| 类型 | 子表 |
| 目标 | 记录工序日志 |
| 依赖 | `T200` |
| 交付物 | `Production Stage Log` 子表 |
| 验收标准 | 能记录投入、产出、不良和时间 |

### T202 Work Order 扩展

| 项目 | 内容 |
|---|---|
| 任务编号 | `T202` |
| 优先级 | `P2` |
| 状态 | `DONE` |
| 类型 | `Custom Field` |
| 目标 | 在工单中追踪款号和生产卡，并从 `Production Ticket` 预填工单草稿 |
| 依赖 | `T200` |
| 交付物 | `Work Order` 扩展字段 |
| 验收标准 | 工单能关联款号和生产卡，且可由 `Production Ticket` 生成预填草稿并自动回写关联 |

### T203 Stock Entry Detail 扩展

| 项目 | 内容 |
|---|---|
| 任务编号 | `T203` |
| 优先级 | `P2` |
| 状态 | `DONE` |
| 类型 | `Custom Field` |
| 目标 | 在库存凭证明细中追踪款色码与生产卡，并从 `Production Ticket` 预填库存草稿 |
| 依赖 | `T200` |
| 交付物 | `Stock Entry Detail` 扩展字段 |
| 验收标准 | 库存凭证明细可追踪生产来源，且可由 `Production Ticket` 生成预填草稿 |

当前实现说明：

- `Production Ticket` 已支持 `Create BOM`
- `Production Ticket` 已支持 `Sync BOM`
- `Create BOM` 已支持可选 `Source BOM`，会复制原 `BOM Item / Operation` 到新草稿
- `BOM` 保存后会自动回写 `Production Ticket.bom_no`
- `Production Ticket` 已支持 `Create Work Order`
- `Production Ticket` 已支持 `Create Stock Entry`
- `Production Ticket` 保存时会自动同步已关联 `Work Order`
- `Work Order` 保存时会自动反写 `Production Ticket.work_order`
- `Stock Entry Detail`、`Work Order` 在手工选择 `production_ticket` 时会自动带出关键字段

### T204 BOM 扩展与辅助创建

| 项目 | 内容 |
|---|---|
| 任务编号 | `T204` |
| 优先级 | `P2` |
| 状态 | `DONE` |
| 类型 | `Custom Field` + 服务逻辑 |
| 目标 | 在 `BOM` 中追踪款号和生产卡，并从 `Production Ticket` 预填 BOM 草稿 |
| 依赖 | `T200` |
| 交付物 | `BOM` 扩展字段、客户端自动带值、回写事件 |
| 验收标准 | `BOM` 可关联款号与生产卡，且可由 `Production Ticket` 生成预填草稿并自动回写关联 |

## 推荐实现顺序

建议严格按下面顺序推进：

1. `T000`
2. `T001`
3. `T002`
4. `T100`
5. `T101`
6. `T102`
7. `T103`
8. `T104`
9. `T105`
10. `T110`
11. `T111`
12. `T120`
13. `T121`
14. `T122`
15. `T123`
16. `T130`
17. `T140`
18. `T141`
19. `T200`
20. `T201`
21. `T202`
22. `T203`
23. `T204`

## 一期验收清单

满足以下条件即可认定一期达到可用状态：

- 可以维护 `Color Group`
- 可以维护 `Color`
- 可以维护 `Size System`
- 可以维护 `Size Code`
- 可以维护 `Style`
- `Style` 能定义允许颜色
- `Style` 能选择尺码体系
- 可以自动生成 SKU 到 `Item`
- 生成后的 `Item` 符合 SKU 编码规则
- `Item` 上能看到款号、颜色、尺码、自定义状态字段
- `Style Matrix` 能展示颜色尺码覆盖情况
- 销售明细能追踪款色码

## 当前建议的开发分工

如果后续要分工，建议按下面拆：

- 模型与后端：`T100-T123`
- 页面与交互：`T130`
- 单据扩展：`T140`, `T202`, `T203`
- 生产轻量跟踪：`T200-T201`

## 下一步建议

现在最适合继续做的是以下两件事之一：

1. 继续第二阶段：仓储状态、库位流转、退货字典
2. 在仓储状态稳定后，再恢复渠道同步专题

第二阶段规划文档：

- [fashion-erp-phase2-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase2-implementation.md)
- [fashion-erp-phase2-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase2-task-list.md)
