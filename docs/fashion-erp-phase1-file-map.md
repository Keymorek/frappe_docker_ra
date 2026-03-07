# Fashion ERP 第一期文件级实现清单

本文档把 `fashion_erp` 第一期方案继续下钻到“文件级实现”。

关联文档：

- 总体字段设计：[fashion-erp-doctype-design.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-doctype-design.md)
- 第一期实施版：[fashion-erp-phase1-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-implementation.md)
- 第一期任务清单：[fashion-erp-phase1-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-task-list.md)

定位：

- 这不是字段字典
- 这不是任务排期
- 这是“每个功能应该落在哪些文件里”的实现清单

使用方式：

1. 先按本文建立应用目录结构
2. 再按任务编号逐批创建文件
3. 实际开发时，以“最小可运行文件集合”为原则，不先铺太多空文件

当前仓库中的实际源码路径：

- [custom_apps/fashion_erp](E:\Dropbox\Syn\Project\frappe_docker_ra\custom_apps\fashion_erp)
- 进入 bench 后对应路径仍为 `apps/fashion_erp`

## 实现原则

### 1. 第一期仍以 `Item` 承载 SKU

因此不会创建独立 `sku` DocType 目录。

SKU 相关逻辑主要分布在：

- `Style` 表单动作
- `sku_service.py`
- `Item` 的 `Custom Field`

### 2. 优先使用 Frappe 标准生成结构

DocType、Page、Report 尽量使用标准生成目录，不做非标准散落文件。

### 3. 服务逻辑与 DocType 控制器分离

建议：

- `doctype/*.py` 只保留校验、轻量生命周期逻辑
- 批量生成、命名、字典初始化等放到 `services/`

### 4. 标准对象扩展统一走 fixtures

第一期对 `Item`、`Sales Order`、`Sales Order Item`、`Work Order`、`Stock Entry Detail` 的扩展，
统一通过：

- `fixtures/custom_field.json`
- `fixtures/property_setter.json`
- `fixtures/client_script.json`

不要手工在生产库里零散配置。

## 目标目录结构

以下目录是建议的第一期目标结构。

```text
<bench>/apps/fashion_erp/
- fashion_erp/
  - __init__.py
  - hooks.py
  - modules.txt
  - patches.txt
  - fixtures/
    - custom_field.json
    - property_setter.json
    - client_script.json
  - patches/
    - v1_0/
      - __init__.py
      - seed_phase1_master_data.py
      - backfill_item_fields.py
  - style/
    - __init__.py
    - api.py
    - workspace/
      - fashion_erp/
        - fashion_erp.json
    - services/
      - __init__.py
      - style_service.py
      - sku_service.py
    - doctype/
      - color_group/
        - color_group.json
        - color_group.py
      - color/
        - color.json
        - color.py
      - size_system/
        - size_system.json
        - size_system.py
      - size_code/
        - size_code.json
        - size_code.py
      - style/
        - style.json
        - style.py
        - style.js
      - style_color/
        - style_color.json
        - style_color.py
    - page/
      - style_matrix/
        - style_matrix.json
        - style_matrix.js
        - style_matrix.py
  - channel/
    - __init__.py
    - doctype/
      - channel_store/
        - channel_store.json
        - channel_store.py
  - stock/
    - __init__.py
    - doctype/
      - warehouse_location/
        - warehouse_location.json
        - warehouse_location.py
  - garment_mfg/
    - __init__.py
    - services/
      - __init__.py
      - production_service.py
    - doctype/
      - production_ticket/
        - production_ticket.json
        - production_ticket.py
        - production_ticket.js
      - production_stage_log/
        - production_stage_log.json
        - production_stage_log.py
```

说明：

- `channel/`、`reporting/` 可以先建模块目录，但第一期不强制落文件
- `BOM`、`Purchase Order` 的扩展在第一期不是主路径，可放到二阶段或 `1B` 后段

## 根级文件清单

| 文件 | 是否一期必须 | 作用 |
|---|---|---|
| `fashion_erp/hooks.py` | 是 | 注册 fixtures、桌面模块、文档事件、安装钩子 |
| `fashion_erp/modules.txt` | 是 | 注册模块名称 |
| `fashion_erp/patches.txt` | 是 | 注册 patch 执行顺序 |
| `fashion_erp/fixtures/custom_field.json` | 是 | 标准 DocType 扩展字段 |
| `fashion_erp/fixtures/property_setter.json` | 否 | 标准字段属性调整 |
| `fashion_erp/fixtures/client_script.json` | 视情况 | 表单端轻量联动 |

建议 `hooks.py` 第一批至少包含：

- `fixtures = ["Custom Field", "Property Setter", "Client Script"]`
- 安装后字典初始化入口
- 可能的 `override_whitelisted_methods` 留空占位

## 任务编号到文件映射

### M0 准备阶段

| 任务 | 主要文件 | 说明 |
|---|---|---|
| `T001` 应用骨架初始化 | `fashion_erp/hooks.py` | 建立 app 基础配置 |
| `T001` 应用骨架初始化 | `fashion_erp/modules.txt` | 注册 `Style`、`Garment Mfg`、`Stock` 等模块 |
| `T001` 应用骨架初始化 | `fashion_erp/patches.txt` | 注册 patch 执行顺序 |
| `T002` 命名与字典预置策略 | `fashion_erp/patches/v1_0/seed_phase1_master_data.py` | 首次安装时导入颜色和尺码字典 |
| `T002` 命名与字典预置策略 | `fashion_erp/style/services/style_service.py` | 存放命名规则与字典辅助方法 |

### M1 主数据

| 任务 | 主要文件 | 说明 |
|---|---|---|
| `T100` `Color Group` | `fashion_erp/style/doctype/color_group/color_group.json` | 定义字段、权限、命名规则 |
| `T100` `Color Group` | `fashion_erp/style/doctype/color_group/color_group.py` | 校验代码唯一性和启用状态 |
| `T101` `Color` | `fashion_erp/style/doctype/color/color.json` | 定义字段与索引 |
| `T101` `Color` | `fashion_erp/style/doctype/color/color.py` | 校验必须归属主颜色 |
| `T102` `Size System` | `fashion_erp/style/doctype/size_system/size_system.json` | 定义尺码体系主档 |
| `T102` `Size System` | `fashion_erp/style/doctype/size_system/size_system.py` | 控制启用状态与命名规则 |
| `T103` `Size Code` | `fashion_erp/style/doctype/size_code/size_code.json` | 定义尺码代码与排序 |
| `T103` `Size Code` | `fashion_erp/style/doctype/size_code/size_code.py` | 校验同体系下唯一 |
| `T104` `Style Category` | `fashion_erp/style/doctype/style_category/style_category.json` | 定义一级品类字典 |
| `T104` `Style Category` | `fashion_erp/style/doctype/style_category/style_category.py` | 校验编码与启用状态 |
| `T105` `Style Sub Category` | `fashion_erp/style/doctype/style_sub_category/style_sub_category.json` | 定义二级品类字典 |
| `T105` `Style Sub Category` | `fashion_erp/style/doctype/style_sub_category/style_sub_category.py` | 校验与一级品类的关联 |
| `T140` `Channel Store` 依赖主档 | `fashion_erp/channel/doctype/channel_store/channel_store.json` | 为 `Sales Order.channel_store` 提供链接对象 |
| `T140` `Channel Store` 依赖主档 | `fashion_erp/channel/doctype/channel_store/channel_store.py` | 校验渠道、仓库与状态 |
| `T110` `Style` | `fashion_erp/style/doctype/style/style.json` | 定义款号主档字段与按钮 |
| `T110` `Style` | `fashion_erp/style/doctype/style/style.py` | 校验主数据、驱动按钮动作 |
| `T110` `Style` | `fashion_erp/style/doctype/style/style.js` | 表单端按钮、联动与提示 |
| `T111` `Style Color` | `fashion_erp/style/doctype/style_color/style_color.json` | 定义允许颜色子表 |
| `T111` `Style Color` | `fashion_erp/style/doctype/style_color/style_color.py` | 一般可保持轻量或留空 |

### M2 SKU 自动生成

| 任务 | 主要文件 | 说明 |
|---|---|---|
| `T120` `Item` 扩展字段 | `fashion_erp/fixtures/custom_field.json` | 新增 `style/color_code/size_code/...` |
| `T120` `Item` 扩展字段 | `fashion_erp/patches/v1_0/backfill_item_fields.py` | 历史数据补齐或默认值回填 |
| `T140` `销售与库存引用字段` | `fashion_erp/fixtures/custom_field.json` | 增加 `Sales Order`、`Sales Order Item`、`Stock Entry Detail` 字段 |
| `T141` `Warehouse Location` | `fashion_erp/stock/doctype/warehouse_location/warehouse_location.json` | 定义库位字典 |
| `T141` `Warehouse Location` | `fashion_erp/stock/doctype/warehouse_location/warehouse_location.py` | 校验库位名称、仓库与启用状态 |
| `T141` `default_location` 迁移 | `fashion_erp/fixtures/custom_field.json` | 把 `Item.default_location` 从 `Data` 改为 `Link` |
| `T141` `default_location` 迁移 | `fashion_erp/patches/v1_0/migrate_phase1_dictionary_links.py` | 历史分类和库位文本值迁移到字典主档 |
| `T121` SKU 编码服务 | `fashion_erp/style/services/sku_service.py` | 生成 `item_code`、条码、显示名 |
| `T121` SKU 编码服务 | `fashion_erp/style/api.py` | 对外暴露 whitelisted 方法 |
| `T122` Generate Variants | `fashion_erp/style/services/sku_service.py` | 根据 `Style + Color + Size` 批量生成 `Item` |
| `T122` Generate Variants | `fashion_erp/style/doctype/style/style.py` | 调用服务层执行生成 |
| `T123` Style 表单按钮 | `fashion_erp/style/doctype/style/style.js` | 前端按钮入口 |
| `T123` Style 表单按钮 | `fashion_erp/style/api.py` | 表单调用的服务方法 |
| `Desk` 入口 | `fashion_erp/style/workspace/fashion_erp/fashion_erp.json` | 提供 `Fashion ERP` 标准 Workspace |

### M3 矩阵视图

| 任务 | 主要文件 | 说明 |
|---|---|---|
| `T130` `Style Matrix` 页面 | `fashion_erp/style/page/style_matrix/style_matrix.json` | 注册页面 |
| `T130` `Style Matrix` 页面 | `fashion_erp/style/page/style_matrix/style_matrix.js` | 前端矩阵渲染 |
| `T130` `Style Matrix` 页面 | `fashion_erp/style/page/style_matrix/style_matrix.py` | 聚合 `Item` 与库存数据 |
| `T130` `Style Matrix` 页面 | `fashion_erp/style/services/style_service.py` | 复用矩阵数据组装逻辑 |

### M4 轻量生产跟踪

| 任务 | 主要文件 | 说明 |
|---|---|---|
| `T200` `Production Ticket` | `fashion_erp/garment_mfg/doctype/production_ticket/production_ticket.json` | 定义生产卡字段 |
| `T200` `Production Ticket` | `fashion_erp/garment_mfg/doctype/production_ticket/production_ticket.py` | 阶段流转、状态校验 |
| `T200` `Production Ticket` | `fashion_erp/garment_mfg/doctype/production_ticket/production_ticket.js` | 表单按钮、草稿生成入口 |
| `T201` `Production Stage Log` | `fashion_erp/garment_mfg/doctype/production_stage_log/production_stage_log.json` | 定义子表字段 |
| `T204` `BOM` 扩展 | `fashion_erp/fixtures/custom_field.json` | 追加 `style/production_ticket/color_code` 字段 |
| `T204` `BOM` 扩展 | `fashion_erp/fixtures/client_script.json` | 手工选择生产卡时自动带出 BOM 关键字段 |
| `T204` `BOM` 扩展 | `fashion_erp/garment_mfg/events/bom.py` | `BOM` 保存后回写 `Production Ticket.bom_no` |
| `T204` `BOM` 扩展 | `fashion_erp/garment_mfg/services/production_service.py` | 从 `Source BOM` 复制 `BOM Item / Operation` 到新草稿 |
| `T202` `Work Order` 扩展 | `fashion_erp/fixtures/custom_field.json` | 追加 `style/production_ticket` 等字段 |
| `T202` `Work Order` 扩展 | `fashion_erp/fixtures/client_script.json` | 手工选择生产卡时自动带出工单关键字段 |
| `T202` `Work Order` 扩展 | `fashion_erp/garment_mfg/events/work_order.py` | `Work Order` 保存后回写 `Production Ticket.work_order` |
| `T203` `Stock Entry Detail` 扩展 | `fashion_erp/fixtures/custom_field.json` | 追加 `style/color_code/size_code` 等字段 |
| `T203` `Stock Entry Detail` 扩展 | `fashion_erp/fixtures/client_script.json` | 手工选择生产卡时自动带出库存明细关键字段 |
| `T200-T204` 服务逻辑 | `fashion_erp/garment_mfg/services/production_service.py` | 生产卡、日志、BOM 草稿、工单草稿、库存草稿联动服务 |
| `T200-T204` 标准对象事件 | `fashion_erp/hooks.py` | 注册 `BOM / Work Order` 回写事件 |

## 每个对象的最小文件集合

以下是第一期建议的最小实现标准。

### 1. 字典类 DocType

适用对象：

- `Color Group`
- `Color`
- `Size System`
- `Size Code`

最小文件集合：

```text
doctype_name/
- doctype_name.json
- doctype_name.py
```

说明：

- 第一批不强制写 `doctype_name.js`
- 如果表单行为只涉及字段校验，优先放服务端

### 2. 主档类 DocType

适用对象：

- `Style`
- `Production Ticket`

最小文件集合：

```text
doctype_name/
- doctype_name.json
- doctype_name.py
- doctype_name.js
```

说明：

- 因为需要表单按钮和前端交互，所以建议同步创建 `js`

### 3. 子表类 DocType

适用对象：

- `Style Color`
- `Production Stage Log`

最小文件集合：

```text
doctype_name/
- doctype_name.json
- doctype_name.py
```

说明：

- 如果子表没有复杂逻辑，`py` 可以保持极简

### 4. 页面类对象

适用对象：

- `Style Matrix`

最小文件集合：

```text
page_name/
- page_name.json
- page_name.js
- page_name.py
```

说明：

- `js` 负责矩阵展示和交互
- `py` 负责查询和聚合数据

## 服务文件职责建议

### `fashion_erp/style/services/style_service.py`

建议放：

- `Style` 相关校验辅助
- `Style Matrix` 数据组装
- 颜色与尺码字典查询
- `item_template` 辅助创建逻辑

### `fashion_erp/style/services/sku_service.py`

建议放：

- SKU 编码生成
- 条码生成或占位规则
- 批量生成 `Item`
- 避免重复创建的去重逻辑
- `Style + Color + Size` 组合展开逻辑

### `fashion_erp/garment_mfg/services/production_service.py`

建议放：

- `Production Ticket` 阶段流转
- 生产日志写入
- 产量累计
- 与 `Work Order` / `Stock Entry` 的轻量联动

## Fixtures 与 Patch 策略

### 1. Fixtures 负责标准对象扩展

第一期建议通过 fixtures 管理：

- `Custom Field`
- `Property Setter`
- `Client Script`

推荐首批覆盖对象：

- `Item`
- `Sales Order`
- `Sales Order Item`
- `Work Order`
- `Stock Entry Detail`

### 2. Patch 负责初始化与回填

建议第一期至少准备三个 patch：

| 文件 | 作用 |
|---|---|
| `fashion_erp/patches/v1_0/seed_phase1_master_data.py` | 导入主颜色、颜色、尺码体系、尺码代码 |
| `fashion_erp/patches/v1_0/migrate_phase1_dictionary_links.py` | 迁移 `Style.category / sub_category` 与 `Item.default_location` 到字典表 |
| `fashion_erp/patches/v1_0/backfill_item_fields.py` | 为已有 `Item` 填充默认值或补齐新字段 |

`patches.txt` 推荐顺序：

```text
fashion_erp.patches.v1_0.seed_phase1_master_data.execute
fashion_erp.patches.v1_0.migrate_phase1_dictionary_links.execute
fashion_erp.patches.v1_0.backfill_item_fields.execute
```

## 建议的开发批次

### 批次 A：应用与字典

交付文件：

- `hooks.py`
- `modules.txt`
- `patches.txt`
- `Color Group`
- `Color`
- `Size System`
- `Size Code`
- `seed_phase1_master_data.py`

完成标准：

- 字典能安装、能录入、能初始化

### 批次 B：款号主档

交付文件：

- `Style`
- `Style Color`
- `style_service.py`

完成标准：

- 能维护 `Style`
- 能维护允许颜色
- 能通过表单按钮触发服务方法

### 批次 C：SKU 生成

交付文件：

- `custom_field.json`
- `sku_service.py`
- `style/api.py`
- `Style` 按钮联动

完成标准：

- 能按 `Style + Color + Size` 生成 `Item`
- 重复生成不会产生重复 SKU

### 批次 D：矩阵页

交付文件：

- `style_matrix.json`
- `style_matrix.js`
- `style_matrix.py`

完成标准：

- 能按款查看颜色尺码覆盖和 SKU 缺口

### 批次 E：轻量生产卡

交付文件：

- `Production Ticket`
- `Production Stage Log`
- `production_service.py`
- `Work Order / Stock Entry Detail` 扩展字段
- `BOM` 扩展字段
- `fixtures/client_script.json`
- `garment_mfg/events/bom.py`
- `garment_mfg/events/work_order.py`

完成标准：

- 能建立生产卡
- 能记录阶段流转
- 能在标准单据里回写款色码引用
- 能从生产卡打开预填的 `BOM` 草稿
- 能按需从已有 `BOM` 复制材料行和工序
- 能从生产卡打开预填的 `Work Order / Stock Entry` 草稿

## 当前最建议先落的文件

如果你现在就准备开始写代码，建议第一批只创建这些：

```text
fashion_erp/hooks.py
fashion_erp/modules.txt
fashion_erp/patches.txt
fashion_erp/style/doctype/color_group/color_group.json
fashion_erp/style/doctype/color_group/color_group.py
fashion_erp/style/doctype/color/color.json
fashion_erp/style/doctype/color/color.py
fashion_erp/style/doctype/size_system/size_system.json
fashion_erp/style/doctype/size_system/size_system.py
fashion_erp/style/doctype/size_code/size_code.json
fashion_erp/style/doctype/size_code/size_code.py
fashion_erp/patches/v1_0/seed_phase1_master_data.py
```

原因：

- 这批文件最稳定
- 几乎不依赖 UI
- 能最快沉淀第一批主数据基础

## 下一步建议

本文档完成后，后续可以直接进入两条路径之一：

1. 先生成 `fashion_erp` 应用骨架和第一批 Doctype
2. 继续把第二阶段的仓储和订单状态对象补进文件地图
