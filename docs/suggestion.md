# Suggestion 已答复版

本文档保留原建议，并补充项目当前口径下的正式答复、优先级判断和是否纳入计划。

当前判断基线：

- 当前项目主线是：`款式录入 -> 打样 -> 工艺单 -> 外包下单 -> 外包到货 -> 入库 -> 履约 -> 售后 -> 报表`
- 平台 API 同步及平台状态自动回写当前统一按 `外部依赖阻塞/暂停` 处理
- 大货主链由 `外包供应链` 驱动，不由 `Production Ticket` 驱动
- `Production Ticket` 当前只保留为打样辅助，不作为大货供料主轴

---

# 一、项目没有测试方案

## 你的建议

### 1. 补充各种测试方案

建议优先覆盖：

- `style_service.py`
  - `normalize_select()`：测正常值、别名映射、非法值抛错、空值回退默认值
  - `normalize_business_code()`：测大写转换、非法字符拒绝
  - `coerce_non_negative_int()/coerce_non_negative_float()`：测边界值（0、负数、字符串）

### 2. 状态机测试

建议重点覆盖：

- `validate_inventory_status_transition()`：遍历所有合法/非法转移
- `_determine_after_sales_decision_status()`：6 种工单类型对应的目标状态
- `_get_after_sales_final_entry_qty()`：复杂数量计算逻辑

### 3. 需要 mock 的服务函数

建议通过 mock `frappe.throw` 和 `frappe.db.get_value` 覆盖：

- `ensure_link_exists()` / `ensure_enabled_link()`
- `validate_location_type()`
- 各 DocType `validate()` 中的字段归一化与业务规则

### 4. 集成测试

建议通过 Frappe test runner 覆盖：

- `seed_master_data()` 幂等性
- `generate_variants_for_style()` 的 SKU 生成流程
- 售后工单完整状态流转

## 答复结论

### 结论

这部分建议整体合理，而且当前项目确实缺少正式测试方案，应纳入计划。

### 具体判断

- 我认同“纯函数测试 + 状态机测试 + mock 服务层测试 + 集成测试”的四层结构
- 首批最值得补的测试对象是：
  - `style_service.py`
  - `stock_service.py`
  - `after_sales_service.py`
  - `outsource_service.py`
  - `outsource_receipt_service.py`

### 优先级判断

- 应纳入计划：`是`
- 当前优先级：`高`
- 是否立刻打断业务主线：`否`

### 计划建议

建议把测试工作作为单独的“质量保障轨道”，而不是塞进业务阶段任务编号里。

建议顺序：

1. 先完成 `T421` 的业务主线闭环
2. 再补第一轮测试基础设施
3. 然后优先覆盖：
   - 核心工具函数
   - 库存状态流转
   - 售后状态流转
   - 外包单 / 到货单状态流转

---

# 二、性能优化方案

## 你的建议

### 问题 1：SKU 生成的 N+1 查询

当前：

- 10 色 × 10 码 = 100 次循环
- 每次 4 次查询
- 约 400 次 DB 往返

建议方案：

- 预加载所有已有 SKU
- 循环内只做字典查找

### 问题 2：style_matrix 的 N+1 查询

当前：

- 每个 SKU 调用 `_get_item_snapshot()`
- 造成 `frappe.db.get_value()` + `_get_stock_qty()` 的重复查询

建议方案：

- 用一条批量查询或 SQL JOIN 替代逐条查询

### 问题 3：API 层重复加载 Style

当前：

- API 层 `_get_style()` 加载一次
- Service 层内部又加载一次

建议方案：

- API 层验证后直接把 `style_doc` 传入 Service 函数

### 低优先级

- Seed upsert 暂不优化
- Color/Size 元数据缓存后续再考虑

## 答复结论

### 结论

这 3 个性能点判断是对的，应记录为技术债，但当前不应排在业务主线前面。

### 具体判断

- `SKU 生成 N+1`：认同，后续应改成批量预加载
- `style_matrix N+1`：认同，但实现上我优先考虑“批量 `get_all()` + 字典映射”，不急着一开始就写重 SQL
- `API 重复加载 Style`：认同，但收益小于前两个

### 优先级判断

- 应纳入计划：`是`
- 当前优先级：`中`
- 当前归类：`技术债 / 收口项`

### 计划建议

建议不要现在插队，而是在以下时点统一处理：

1. `T421` 完成后
2. 或 `T433/T435` 之后做一次“性能与测试收口”

### 备注

这部分更适合作为一次集中优化任务，而不是分散插入每个业务阶段。

---

# 三、采购管理规划

## 你的建议

### 第 1 步：BOM 驱动的物料需求计算

你的建议是：

- 由 `Production Ticket` 驱动需求计算
- 读取 BOM components
- 按数量展开需求
- 减库存得到净需求
- 可进一步生成 `Material Request`

### 第 2 步：发料到外包工厂

你的建议是：

- 使用 `Stock Entry (Material Transfer)` 发料
- 建立工厂虚拟仓
- 跟踪工厂手上还有多少原料

### 第 3 步：新建轻量级 Supply Plan

你的建议是：

- 新建 `Supply Plan`
- 串联：
  - BOM 需求
  - 库存检查
  - 采购下单
  - 收货入库
  - 发料到工厂

### 第 4 步：Client Script 自动化

你的建议是：

- 采购单自动带入业务引用
- 收货自动更新 Supply Plan
- 发料自动更新 Supply Plan

## 答复结论

### 总结结论

这部分建议“方向有价值，但不能原样进入当前计划”，原因是驱动对象和当前项目主线不一致。

当前项目真实主线已经冻结为：

- 大货主线：`工艺单 -> 外包单 -> 外包到货单 -> 入库`
- 非主线对象：`Production Ticket`

所以这部分必须改写成：

- 不是 `Production Ticket` 驱动
- 而是 `Outsource Order` 驱动

### 第 1 步答复：BOM 驱动需求计算

结论：

- `思路有价值`
- `当前不按 Production Ticket 实现`
- `后续如做，应改成 Outsource Order 驱动`

也就是说，未来更合理的方向是：

- `Outsource Order + Craft Sheet/BOM + 原辅料明细`
- 而不是 `Production Ticket + BOM`

### 第 2 步答复：发料到外包工厂

结论：

- 目前 `不纳入主计划`

原因：

- 当前已冻结口径是：
  - 外包订单与原料只做人工可追踪关联
  - 不做自动原料出库联动
- 因此：
  - `工厂虚拟仓`
  - `自动发料追踪`
  - `工厂在手库存`
  这些都不进入当前主线

后续定位：

- 可作为 `P2` 备选扩展
- 当前不进入实施计划

### 第 3 步答复：Supply Plan DocType

结论：

- `概念合理`
- `当前不建议立即上完整 Supply Plan`

更合适的当前做法是：

1. 先把 `Outsource Order.materials` 做深
2. 先补：
   - 计划用量
   - 已备货数量
   - 人工登记已发数量
   - 待采购视图
   - 占用视图
3. 等复杂度确实上来，再升级成独立 `Supply Plan`

也就是说：

- 我认同“需要供料计划视图”
- 但当前不认同“马上单独建完整 Supply Plan DocType”

### 第 4 步答复：自动化联动

结论：

- 方向对
- 但真正关键的联动不能只放在 Client Script

当前更合理的原则是：

- 前端只做默认值和便利交互
- 状态更新、数量更新、关联回写必须落在服务端 / hook

同时，这部分也要改写成：

- `Outsource Order` 驱动
- 而不是 `Production Ticket` 驱动

## 最终归类

### 应纳入计划

- 测试方案
- 性能优化技术债
- 外包单驱动的轻量供料视图

### 需要改写后再纳入

- BOM/需求计算
- 采购执行追踪
- 自动化联动

改写原则：

- 统一改成 `Outsource Order` 驱动
- 不再以 `Production Ticket` 为大货供料主轴

### 暂不纳入

- 工厂虚拟仓
- 自动发料到外包工厂的库存联动

---

# 四、最终答复摘要

1. 测试建议：`认同，且应纳入计划`
2. 性能优化建议：`认同，记录为技术债，不插队当前业务主线`
3. 采购管理建议：`方向有价值，但必须改写为 Outsource Order 驱动，不能按 Production Ticket 原样进入计划`
4. 当前不纳入主计划的内容：
   - 工厂虚拟仓
   - 自动发料到工厂
   - 以 Production Ticket 为主轴的供料计划
