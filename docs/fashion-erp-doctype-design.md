# 用户修改建议
1. 款式层命名为Style SKU层命名为sku
2. Style 增加 category、sub_category 解决品类细分的问题。替换原有的item_group 用两个表来解决
3. Style 增加 fabric_main、fabric_lining 解决面料细分的问题 替换掉materials
4. Style 增加 design_owner
5. Style层 为什么需要 item_template、wave
6. 在 Style层不需要colors，sku层中会解决这个问题
7. Style层的status改为launch_status，新增一个sales_status
8. Style 层增加一个size_system 用于定义这个款式会使用什么尺码系统
尺码体系	code	适用商品
上装尺码	TOP	T恤、衬衫、针织衫、卫衣、外套
连衣裙尺码	DRESS	连衣裙
裤装尺码	BOTTOM	牛仔裤、休闲裤
半裙尺码	SKIRT	短裙、长裙
鞋类尺码	SHOE	女鞋
均码体系	FREE	均码商品
内衣尺码	BRA	内衣
配饰尺码	ACC	帽子、围巾、腰带等
尺码代码表 size_code size_name
size_code	size_name
XXS	XXS
XS	XS
S	S
M	M
L	L
XL	XL
XXL	2XL
XXXL	3XL
F	F
size_code	size_name
24	24
25	25
26	26
27	27
28	28
29	29
30	30
31	31
32	32
size_code	size_name
ONE	OneSize
9. sku层字段表：
字段名	中文名	类型	必填	示例	说明
sku_code	SKU编码	文本	是	RS26S001-BLK-M	唯一SKU
style_code	所属款号	关联	是	RS26S001	关联款式
color_code	颜色代码	枚举	是	BLK	固定字典
color_name	颜色名	文本	是	黑色	给员工看
size_code	尺码代码	枚举	是	M	固定字典
size_name	尺码名	文本	是	M	可和代码一致
barcode	条码	文本	是	690xxxx	可等于SKU或独立
weight	重量	数值	否	0.42	快递计费可用
safe_stock	安全库存	数值	否	8	低于此提醒
default_location	默认库位	关联	否	A01-02	常用上架位
sellable	是否可售	布尔	是	是	有些SKU停卖
sku_status	SKU状态	枚举	是	正常	正常/停产/停售/冻结
batch_enable	是否批次管理	布尔	否	否	第一版可不强开
remark	备注	长文本	否	直播爆款尺码	可选
10. sku编码规则
品牌简写 - 款式 - 主颜色 - 尺码代码
RL-RS26S001-BLK-M
11. 主颜色代码词典 color_group 
主颜色	代码
白色系	WHT
黑色系	BLK
灰色系	GRY
蓝色系	BLU
红色系	RED
粉色系	PNK
绿色系	GRN
棕色系	BRN
卡其色系	KHK
黄色系	YLW
12. 具体颜色 color_name
颜色名	主颜色
奶油白	WHT
米白	WHT
象牙白	WHT
本白	WHT
冷白	WHT
13 增加仓库、库位编码
区域代码	区域名称	用途
IN	收货区	新货/退货签收
QC	待检区	质检前暂存
FG	成衣可售区	正常可售库存
PK	打包区	打包复核、待出货
RT	退货待检区	售后退回暂存
RF	返修区	可修复问题件
DP	次品区	不可售或待处理
SM	样衣区	样衣、直播样板
FR	冻结区	异常库存冻结
库位编码规则
地区-仓库编号-区域-货架-层-位
SH-A01-FG-A03-02-01 
上海-A01仓-成衣区-A03货架-第2层-第1格
字段	含义	示例
地区	城市或地区	SH
仓库	仓库编号	A01
区域	功能区域	FG
货架	货架编号	A03
层	层数	2
位	具体位置	1
库位表字段
 字段名	中文名	类型	必填	示例
location_code	库位编码	文本	是	SH-A01-FG-A03-02-01
warehouse_zone	所属区域	枚举/关联	是	FG
rack_no	货架号	文本	是	A01
level_no	层号	文本	是	1
bin_no	位置号	文本	是	1
location_type	库位类型	枚举	是	正常拣货位
enabled	是否启用	布尔	是	是
remark	备注	文本	否	爆款黄金位
字段	用途
location_type	库位类型
priority	拣货优先级
类型	说明
PICK	拣货位
STORAGE	储存位
BUFFER	缓冲位
库位	priority
FG-A01-01-01	1
FG-A02-01-01	2
14 库存状态定义
状态代码	状态名称	是否可售	说明
SELLABLE	可售	是	正常可销售库存
RESERVED	已预留	否	已被订单占用
QC_PENDING	待质检	否	未检验
RETURN_PENDING	退货待检	否	售后退回未处理
REPAIR	返修中	否	等待修复
DEFECTIVE	次品	否	不可正常销售
FROZEN	冻结	否	异常冻结
SAMPLE	样衣	否	样衣展示用途

只允许按规则流转，不允许员工随意改：
- 新生产完成 → QC_PENDING / 或直接 SELLABLE
- 客退签收 → RETURN_PENDING
- 质检合格 → SELLABLE
- 质检不合格可修 → REPAIR
- 质检不合格不可修 → DEFECTIVE
- 直播借样 → SAMPLE
- 异常争议 → FROZEN
主订单状态字典
状态代码	状态名称	说明
NEW	新订单	刚同步进系统
PAID	已付款	可进入分配
ALLOCATED	已分配库存	已锁定库存
PICKING	拣货中	仓库正在拣货
PICKED	已拣货	等待打包
PACKING	打包中	正在核对和装箱
READY_TO_SHIP	待出单	待打印面单/待交运
SHIPPED	已发货	已出库
DELIVERED	已签收	已完成
AFTERSALE	售后中	有退换货/异常
CLOSED	关闭	取消或完成归档
PARTIAL_REFUND	部分退款	有部分商品退单
REFUNDED	全部退款	订单退单
订单明细状态
状态代码	说明
PENDING	待处理
ALLOCATED	已锁库存
PICKED	已拣货
PACKED	已打包
SHIPPED	已发货
DELIVERED	已签收
RETURN_REQUEST	申请退货
RETURNED	已退回
REFUND_REQUEST	申请退款
REFUNDED	已退款
DEFECTIVE	次品
库存与订单状态的关系
状态	库存变化
ALLOCATED	锁库存
PICKED	不变
SHIPPED	扣库存
RETURNED	回库存
DEFECTIVE	入次品库存
退货状态字典
代码	结果名称	是否回可售	说明
A1	全新可售	是	包装完整、无穿着痕迹
A2	整理后可售	是	轻微折痕/线头，处理后可售
B1	需返修	否	可修复
B2	次品不可售	否	污渍、破损、严重问题
C1	样衣回收	否	回样衣区
D1	异常争议	否	待人工判定
退货原因字典
代码	原因
R01	尺码不合适
R02	颜色不喜欢
R03	款式不喜欢
R04	质量问题
R05	发错货
R06	物流问题
R07	与描述不符
R99	其他
## 本次评审结论

说明：

- 本节结论优先于下文字段草案。
- 下文字段草案目前尚未完全按本节重写，后续应以本节为准继续收敛。
- 评审原则是同时兼顾业务适配性和 ERPNext 标准对象兼容性。

| 编号 | 用户建议 | 评审结论 | 原因 | 计划同步方式 |
|---|---|---|---|---|
| 1 | 款式层命名为 `Style`，SKU 层命名为 `sku` | 有条件接受 | 业务表达合理，但技术实现上不建议第一阶段单独做 `SKU` 主表，否则会与 ERPNext `Item / Item Variant` 重叠 | 计划中保留“SKU 层”概念，但第一阶段实现映射到 `Item` |
| 2 | `Style` 增加 `category`、`sub_category`，替换 `item_group` | 有条件接受 | 女装业务需要细分类，但 ERPNext 的 `Item Group` 仍然有系统价值，不能直接删除 | 第一阶段增加 `category`、`sub_category`，同时保留 `item_group` 作为系统映射字段 |
| 3 | `Style` 增加 `fabric_main`、`fabric_lining`，替换 `materials` | 有条件接受 | 这两个摘要字段很有价值，但完全替代 `materials` 会损失面辅料扩展能力 | 第一阶段增加摘要字段，`materials` 保留为可选扩展 |
| 4 | `Style` 增加 `design_owner` | 接受 | 服装行业常见字段，便于责任归属和流程跟踪 | 纳入第一阶段 `Style` 字段 |
| 5 | 解释 `item_template`、`wave` 是否需要 | 部分采纳 | `item_template` 对 ERPNext SKU/Variant 联动仍然重要；`wave` 并非所有团队都需要 | 保留 `item_template`；`wave` 改为可选规划字段，不放入第一阶段必做范围 |
| 6 | `Style` 层不需要 `colors` | 不建议直接采用 | 颜色仍然是款式层的规划对象；如果完全移除，将不利于 SKU 生成和企划管理 | 保留“款式允许颜色”层；SKU 层承载实际可售颜色尺码组合 |
| 7 | `status` 改为 `launch_status`，新增 `sales_status` | 接受 | 上市状态和销售状态确实应拆分 | 第一阶段替换原单一 `status` 设计 |
| 8 | `Style` 增加 `size_system`，并定义尺码体系与尺码代码 | 接受 | 这是服装行业核心字段，比纯通用 `Size Set` 更贴近业务 | 第一阶段优先采用 `size_system`，并增加 `Size Code` 字典；原 `Size Set` 方案降级为可选扩展 |
| 9 | 增加 SKU 层字段表 | 有条件接受 | 字段设计合理，但技术上应优先落在 `Item` 扩展字段，而不是新增重复主档 | 第一阶段将这些字段优先映射到 `Item` |
| 10 | SKU 编码规则：品牌简写-款式-主颜色-尺码代码 | 接受 | 符合业务识别和运营习惯 | 第一阶段作为 `Item.item_code` / SKU 编码规则 |
| 11 | 增加主颜色代码词典 `color_group` | 接受 | 有利于颜色归类、分析和命名统一 | 纳入第一阶段主数据 |
| 12 | 增加具体颜色字典 `color_name` | 接受 | 比自由文本更适合长期维护 | 纳入第一阶段主数据 |
| 13 | 增加仓库、库位编码与库位表 | 接受，但分期 | 业务合理，但已超出第一阶段款号/SKU 主数据范围 | 纳入第二阶段仓储专题 |
| 14 | 增加库存状态、主订单状态、订单明细状态、退货状态字典 | 接受，但分期 | 这些是履约与售后流转规则，合理但不应阻塞第一阶段主数据建模 | 纳入第二阶段订单与库存流转专题 |

## 评审后计划同步

## T000 冻结结论

以下业务口径已冻结：

1. `category / sub_category` 最终设计为字典表
2. `default_location` 最终设计为字典表
3. `Production Ticket` 继续归在 `1B`

补充说明：

- 当前代码实现已跟到这 3 个冻结结论
- 本文档后续如与以上 3 条冲突，以本节为准
- 当前已落地 `Style Category`、`Style Sub Category`、`Warehouse Location` 三个字典对象

### 第一阶段：主数据与 SKU 建模

本阶段目标：

- 跑通 `Style -> SKU(Item) -> 销售/库存/生产引用` 的基础链路
- 完成服装行业最核心的主数据字典和编码规则

本阶段纳入计划的内容：

1. `Style` 修订版
2. `Style Color` 或“款式允许颜色”层
3. `Color Group` 主颜色字典
4. `Color` 具体颜色字典
5. `Size System` 尺码体系字典
6. `Size Code` 尺码代码字典
7. `Item` 作为 SKU 层实现对象，并补充 SKU 字段
8. SKU 编码规则
9. `Production Ticket` 保留，但放到主数据完成后再做

第一阶段 `Style` 重点新增字段：

- `category`
- `sub_category`
- `fabric_main`
- `fabric_lining`
- `design_owner`
- `launch_status`
- `sales_status`
- `size_system`

第一阶段 `Style` 保留字段：

- `style_code`
- `style_name`
- `brand`
- `item_template`
- `tag_price`
- `target_cost`

第一阶段 `Style` 暂缓或降级字段：

- `wave`：降级为可选规划字段
- `materials`：保留为可选扩展，不作为第一阶段核心

第一阶段 SKU 层优先落在 `Item` 的字段：

- `sku_code`
- `style_code`
- `color_code`
- `color_name`
- `size_code`
- `size_name`
- `barcode`
- `weight`
- `safe_stock`
- `default_location`
- `sellable`
- `sku_status`
- `batch_enable`
- `remark`

### 第二阶段：仓储与履约流转

本阶段纳入计划的内容：

1. `Warehouse Zone` / 仓储区域字典
2. `Warehouse Location` / 库位主档增强
3. 库位编码规则
4. `Inventory Status` / 库存状态字典
5. 库存状态流转控制
6. 退货结果字典
7. 退货原因字典

### 第三阶段：手工同步与运营支持

本阶段纳入计划的内容：

1. `Channel Store`
2. 手工订单同步
3. 手工履约状态维护
4. 运营辅助对象与报表

补充说明：

- 平台订单同步已改为永久搁置，当前只能手工同步
- 当前开发批次不进入渠道自动化范围
- 生产相关能力后置，优先支持女装电商运营主链路

# Fashion ERP 字段字典设计

相关文档：

- 总体设计与字段草案：本文档
- 第一期实施版：[fashion-erp-phase1-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-implementation.md)

本文档是 `fashion_erp` 自定义应用的字段字典草案，用于女装电商与服装生产场景。

本文档目标：

- 明确第一阶段 DocType 设计
- 为后续开发保留可持续修改的字段字典
- 在正式编码前统一默认值、唯一性、索引和命名规则

本文档范围：

- `fashion_erp` 中新增的自定义 DocType
- 通过 `Custom Field` 扩展的标准 ERPNext DocType
- 第一阶段建议的命名规则与索引策略

本文档状态：

- 草案
- 可继续修改

## 使用说明

建议你后续修改时遵循以下原则：

- 字段代码名尽量稳定，避免在开发后频繁重命名
- 中文标签和业务说明可以反复调整
- 默认值、唯一性、索引属于实现约束，改动前需要评估历史数据影响
- 子表中的“组合唯一”通常需要通过 `validate` 逻辑保证，而不是只靠数据库唯一索引

## 设计原则

- 标准 ERPNext 已能承载的能力优先复用
- 行业差异化能力放入自定义 app，不直接改 ERPNext 核心
- 数据中心是 `Style`，不是单个 SKU
- SKU 通过 `Item Template + Item Variant` 生成

核心关系：

`Style -> Item Template -> Item Variant -> Sales Order Item / BOM / Work Order / Stock Entry`

## App 结构

建议模块布局：

```text
fashion_erp/
- style/
- channel/
- garment_mfg/
- reporting/
- setup/
- patches/
- fixtures/
- hooks.py
```

模块职责：

- `style`：款号主档、颜色、尺码组、SKU 生成
- `channel`：电商渠道、店铺、订单同步、库存回传
- `garment_mfg`：生产跟踪、委外、质检、包装
- `reporting`：矩阵报表、进度看板、经营分析
- `setup`：系统设置、命名规则、初始化逻辑
- `patches`：数据库补丁、组合索引、数据修正
- `fixtures`：导出的 `Custom Field`、`Workflow`、`Client Script`、`Print Format`

## 字段字典约定

### 默认值说明

- `无`：不建议预置默认值，要求用户明确输入
- `当前年份`：建议通过脚本或 `before_insert` 自动写入
- `Now`：建议使用当前时间戳
- `1` / `0`：布尔开关默认值

### 唯一性说明

- `是`：建议使用数据库唯一约束
- `否`：不做唯一约束
- `组合唯一`：建议通过代码校验或数据库组合索引控制

### 索引说明

- `唯一索引`：唯一字段，直接建立唯一索引
- `查询索引`：高频筛选、联查、列表页检索字段
- `组合索引`：建议通过 patch 增加联合索引
- `无`：当前阶段不建议建索引

### 命名规则说明

- `name` 是 Frappe 实际主键
- 如 `autoname = field:xxx`，则 `name` 与业务编码一致
- 如使用 `format:`，则 `name` 按系统规则生成

## 统一命名规则

| 对象 | `name` 规则 | 业务编码字段 | 建议格式 | 示例 |
|---|---|---|---|---|
| `Style` | `field:style_code` | `style_code` | `品牌简称-YY季-品类-流水号` | `RS-26SS-DR-0001` |
| `Color Group` | `field:color_group_code` | `color_group_code` | 主颜色代码 | `BLK` |
| `Color` | `field:color_name` | `color_name` | 具体颜色名 | `奶油白` |
| `Size System` | `field:size_system_code` | `size_system_code` | 尺码体系代码 | `DRESS` |
| `Size Code` | `format:{size_system}-{size_code}` | `size_code` | `尺码体系-尺码代码` | `TOP-M` |
| `SKU(Item)` | 标准 `item_code` | `item_code` | `品牌简写-款式-主颜色-尺码代码`；品牌简写来自 `Brand.brand_abbr` | `RL-RS26S001-BLK-M` |
| `Channel Store` | 初期 `field:store_name` | `store_name` | 若跨渠道重名，再改为独立 `store_code` | `TikTok-旗舰店` |
| `Production Ticket` | `format:PT-{YYYY}-{#####}` | 无 | 系统生成 | `PT-2026-00001` |
| `Style Color` | 子表 | `color` | 引用具体颜色主档 | `奶油白` |

统一编码建议：

- 业务编码统一使用大写英文、数字、中划线
- 避免空格、中文、斜杠
- 建议正则：`^[A-Z0-9][A-Z0-9_-]*$`

## 全局索引策略

第一阶段建议优先建立字段级索引：

- `Style.style_code`
- `Style.style_name`
- `Style.brand`
- `Style.category`
- `Style.sub_category`
- `Style.size_system`
- `Style.item_group`
- `Style.launch_status`
- `Style.sales_status`
- `Color Group.color_group_code`
- `Color.color_group`
- `Color.color_name`
- `Size System.size_system_code`
- `Size Code.size_system`
- `Size Code.size_code`
- `Channel Store.channel`
- `Channel Store.warehouse`
- `Item.style`
- `Item.color_code`
- `Item.size_code`
- `Item.sku_status`
- `Item.sellable`
- `Production Ticket.style`
- `Production Ticket.stage`
- `Production Ticket.status`
- `Production Ticket.supplier`

第二阶段如查询量变大，建议通过 patch 增加组合索引：

- `tabItem(style, color_code, size_code)`
- `tabSales Order(channel_store, external_order_id)`
- `tabBOM(style, bom_type, version_no)`
- `tabWork Order(style, production_ticket)`
- `tabProduction Ticket(style, stage, status)`
- `tabProduction Stage Log(parent, stage, log_time)`

## 自定义 DocType

### 1. Style

用途：

- 女装业务的核心主档
- 在生成 SKU 之前，先管理款号层面的属性、规划状态和销售状态

#### DocType 级定义

| 项目 | 建议值 |
|---|---|
| 模块 | `style` |
| 表类型 | 主表 |
| `autoname` | `field:style_code` |
| 主显示字段 | `style_name` |
| 搜索字段 | `style_code, style_name` |
| 主要唯一约束 | `style_code` |
| 建议索引 | `style_code`, `style_name`, `brand`, `category`, `sub_category`, `size_system`, `item_group`, `launch_status`, `sales_status` |
| 默认上市状态 | `Draft` |
| 默认销售状态 | `Not Ready` |

#### 字段字典

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `style_code` | 款号 | `Data` | 是 | 无 | 是 | 唯一索引 | 建议大写，格式 `品牌简称-YY季-品类-流水号` | 业务主编码，同时作为 `name` |
| `style_name` | 款名 | `Data` | 是 | 无 | 否 | 查询索引 | 建议控制在 140 字符内 | 用于业务展示 |
| `brand` | 品牌 | `Link` -> `Brand` | 否 | 无 | 否 | 查询索引 | 关联 ERPNext `Brand`；SKU 前缀读取 `Brand.brand_abbr` | 便于后续扩展品牌维度 |
| `category` | 一级品类 | `Link` -> `Style Category` | 是 | 无 | 否 | 查询索引 | 引用受控分类字典 | 如上装、连衣裙、裤装 |
| `sub_category` | 二级品类 | `Link` -> `Style Sub Category` | 否 | 无 | 否 | 查询索引 | 引用受控二级分类字典 | 如针织衫、牛仔裤、半裙 |
| `item_group` | ERPNext 品类映射 | `Link` -> `Item Group` | 否 | 无 | 否 | 查询索引 | 作为系统映射字段保留 | 不再作为唯一业务品类字段 |
| `season` | 季节 | `Select` | 是 | 无 | 否 | 查询索引 | `SS`, `AW`, `ALL` | 季节属性 |
| `year` | 年份 | `Int` | 是 | 当前年份 | 否 | 查询索引 | 四位年份 | 与季节配合形成款号 |
| `wave` | 波段 | `Data` | 否 | 无 | 否 | 无 | 可选规划字段 | 第一阶段非核心 |
| `gender` | 性别 | `Select` | 否 | `Women` | 否 | 无 | `Women`, `Unisex`, `Kids` | 当前场景默认女装 |
| `design_owner` | 设计负责人 | `Data` | 否 | 无 | 否 | 查询索引 | 用户手工输入文本 | 用于责任归属 |
| `size_system` | 尺码体系 | `Link` -> `Size System` | 是 | 无 | 否 | 查询索引 | 必须选择已启用尺码体系 | SKU 生成依赖 |
| `item_template` | 模板货品 | `Link` -> `Item` | 否 | 无 | 否 | 查询索引 | 建议绑定模板 `Item` | 对应 ERPNext 模板货品 |
| `fabric_main` | 主面料 | `Data` | 否 | 无 | 否 | 无 | 摘要字段 | 用于快速查看主面料 |
| `fabric_lining` | 里料 | `Data` | 否 | 无 | 否 | 无 | 摘要字段 | 用于快速查看里料 |
| `target_cost` | 目标成本 | `Currency` | 否 | `0` | 否 | 无 | 非负数 | 目标成本 |
| `tag_price` | 吊牌价 | `Currency` | 否 | `0` | 否 | 无 | 非负数 | 建议零售价参考 |
| `launch_status` | 上市状态 | `Select` | 是 | `Draft` | 否 | 查询索引 | `Draft`, `Sampling`, `Approved`, `Ready`, `Launched`, `Archived` | 款式开发与上市准备状态 |
| `sales_status` | 销售状态 | `Select` | 是 | `Not Ready` | 否 | 查询索引 | `Not Ready`, `On Sale`, `Stop Sale`, `Clearance`, `Discontinued` | 销售可用状态 |
| `cover_image` | 主图 | `Attach Image` | 否 | 无 | 否 | 无 | 图片附件 | 用于展示 |
| `description` | 款式说明 | `Small Text` | 否 | 无 | 否 | 无 | 文本说明 | 设计、工艺摘要 |
| `colors` | 款式允许颜色 | `Table` -> `Style Color` | 是 | 无 | 否 | 无 | 至少 1 行 | 用于定义本款允许生成 SKU 的颜色 |

#### 业务规则

- `style_code` 必须唯一
- 保存时建议自动转大写并去除首尾空格
- 执行 `Generate Variants` 前必须满足：
  - `size_system` 已设置
  - `colors` 至少存在一个 `enabled = 1`
- `item_group` 可由 `category / sub_category` 自动映射，不建议手工随意填写
- 当 `launch_status = Launched` 时，建议至少存在一个模板货品或已生成 SKU

补充说明：

- 第一阶段不再以 `Style Material` 作为核心结构
- 若后续需要自动 BOM 和面辅料精细化管理，可恢复面辅料子表作为第二阶段扩展

### 2. Style Color

用途：

- 存储某一款号允许使用的具体颜色
- 作为 `Style` 与颜色主数据之间的桥接层

#### DocType 级定义

| 项目 | 建议值 |
|---|---|
| 模块 | `style` |
| 表类型 | 子表 |
| 上级 DocType | `Style` |
| 主要唯一约束 | `parent + color` 组合唯一 |
| 建议索引 | 默认依赖父表，不额外建索引 |
| 默认状态 | `enabled = 1` |

#### 字段字典

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `color` | 具体颜色 | `Link` -> `Color` | 是 | 无 | 组合唯一 | 无 | 引用有效颜色主档 | 本款允许使用的颜色 |
| `color_name` | 颜色名称 | `Data` | 是 | 自动带出 | 否 | 无 | 从 `Color` 获取 | 给员工看 |
| `color_code` | 主颜色代码 | `Data` | 是 | 自动带出 | 否 | 无 | 从 `Color Group` 获取 | 用于 SKU 命名和统计 |
| `sort_order` | 排序值 | `Int` | 否 | `0` | 否 | 无 | 从小到大 | 控制矩阵显示顺序 |
| `enabled` | 启用 | `Check` | 是 | `1` | 否 | 无 | `1/0` | 是否参与 SKU 生成 |

#### 业务规则

- 同一个 `Style` 下不允许重复选择同一 `Color`
- `enabled = 0` 的颜色不参与 SKU 生成

### 3. Color Group

用途：

- 维护主颜色代码词典
- 用于 SKU 命名、颜色归类和统计分析

#### DocType 级定义

| 项目 | 建议值 |
|---|---|
| 模块 | `style` |
| 表类型 | 主表 |
| `autoname` | `field:color_group_code` |
| 主显示字段 | `color_group_name` |
| 搜索字段 | `color_group_code, color_group_name` |
| 主要唯一约束 | `color_group_code` |
| 建议索引 | `color_group_code`, `enabled`, `sort_order` |
| 默认状态 | `enabled = 1` |

#### 字段字典

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `color_group_code` | 主颜色代码 | `Data` | 是 | 无 | 是 | 唯一索引 | 建议使用三位大写英文 | 如 `WHT`, `BLK`, `RED` |
| `color_group_name` | 主颜色名称 | `Data` | 是 | 无 | 否 | 查询索引 | 中文展示名 | 如白色系、黑色系 |
| `sort_order` | 排序值 | `Int` | 否 | `0` | 否 | 无 | 从小到大 | 控制列表顺序 |
| `enabled` | 启用 | `Check` | 是 | `1` | 否 | 查询索引 | `1/0` | 是否可选 |
| `remark` | 备注 | `Small Text` | 否 | 无 | 否 | 无 | 自由文本 | 说明信息 |

#### 业务规则

- `color_group_code` 必须唯一
- `color_group_code` 应与 SKU 命名规则保持一致
- 建议先预置你已定义的 10 个主颜色代码

### 4. Color

用途：

- 维护具体颜色字典
- 用于把“奶油白、米白、象牙白”映射到统一的主颜色代码

#### DocType 级定义

| 项目 | 建议值 |
|---|---|
| 模块 | `style` |
| 表类型 | 主表 |
| `autoname` | `field:color_name` |
| 主显示字段 | `color_name` |
| 搜索字段 | `color_name, color_group` |
| 主要唯一约束 | `color_name` |
| 建议索引 | `color_name`, `color_group`, `enabled` |
| 默认状态 | `enabled = 1` |

#### 字段字典

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `color_name` | 具体颜色名 | `Data` | 是 | 无 | 是 | 唯一索引 | 中文或业务常用名 | 如奶油白、米白 |
| `color_group` | 主颜色 | `Link` -> `Color Group` | 是 | 无 | 否 | 查询索引 | 引用主颜色字典 | 决定 SKU 中的颜色代码 |
| `enabled` | 启用 | `Check` | 是 | `1` | 否 | 查询索引 | `1/0` | 是否可选 |
| `remark` | 备注 | `Small Text` | 否 | 无 | 否 | 无 | 自由文本 | 辅助说明 |

#### 业务规则

- `color_name` 建议唯一
- 一个具体颜色必须归属于一个主颜色

### 5. Size System

用途：

- 定义服装业务中的尺码体系
- 替代原先通用的 `Size Set` 概念

#### DocType 级定义

| 项目 | 建议值 |
|---|---|
| 模块 | `style` |
| 表类型 | 主表 |
| `autoname` | `field:size_system_code` |
| 主显示字段 | `size_system_name` |
| 搜索字段 | `size_system_code, size_system_name` |
| 主要唯一约束 | `size_system_code` |
| 建议索引 | `size_system_code`, `enabled` |
| 默认状态 | `enabled = 1` |

#### 字段字典

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `size_system_code` | 尺码体系代码 | `Data` | 是 | 无 | 是 | 唯一索引 | 建议使用大写英文 | 如 `TOP`, `DRESS`, `BOTTOM`, `FREE` |
| `size_system_name` | 尺码体系名称 | `Data` | 是 | 无 | 否 | 查询索引 | 中文展示名 | 如上装尺码、连衣裙尺码 |
| `applicable_products` | 适用商品 | `Small Text` | 否 | 无 | 否 | 无 | 说明性文本 | 如 T恤、衬衫、卫衣 |
| `enabled` | 启用 | `Check` | 是 | `1` | 否 | 查询索引 | `1/0` | 是否可选 |
| `remark` | 备注 | `Small Text` | 否 | 无 | 否 | 无 | 自由文本 | 辅助说明 |

#### 业务规则

- `size_system_code` 必须唯一
- 第一阶段建议预置 `TOP`, `DRESS`, `BOTTOM`, `SKIRT`, `SHOE`, `FREE`, `BRA`, `ACC`

### 6. Size Code

用途：

- 定义某个尺码体系下允许使用的尺码代码
- 例如 `TOP-M`、`BOTTOM-28`、`FREE-ONE`

#### DocType 级定义

| 项目 | 建议值 |
|---|---|
| 模块 | `style` |
| 表类型 | 主表 |
| `autoname` | `format:{size_system}-{size_code}` |
| 主显示字段 | `size_name` |
| 搜索字段 | `size_system, size_code, size_name` |
| 主要唯一约束 | `size_system + size_code` 组合唯一 |
| 建议索引 | `size_system`, `size_code`, `sort_order`, `enabled` |
| 默认状态 | `enabled = 1` |

#### 字段字典

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `size_system` | 尺码体系 | `Link` -> `Size System` | 是 | 无 | 组合唯一 | 查询索引 | 引用有效尺码体系 | 上装、裤装等 |
| `size_code` | 尺码代码 | `Data` | 是 | 无 | 组合唯一 | 查询索引 | 建议使用标准代码 | 如 `S`, `M`, `L`, `28`, `ONE` |
| `size_name` | 尺码名称 | `Data` | 是 | 无 | 否 | 查询索引 | 可与代码相同 | 展示名称 |
| `sort_order` | 排序值 | `Int` | 是 | 无 | 否 | 查询索引 | 从小到大排序 | 控制矩阵顺序 |
| `enabled` | 启用 | `Check` | 是 | `1` | 否 | 无 | `1/0` | 是否参与 SKU 生成 |

#### 业务规则

- 同一尺码体系下不允许重复 `size_code`
- 同一尺码体系下不建议重复 `sort_order`

### 7. Channel Store

用途：

- 维护电商渠道与店铺配置
- 将店铺与仓库、价格体系关联

#### DocType 级定义

| 项目 | 建议值 |
|---|---|
| 模块 | `channel` |
| 表类型 | 主表 |
| `autoname` | 初期 `field:store_name` |
| 主显示字段 | `store_name` |
| 搜索字段 | `channel, store_name` |
| 主要唯一约束 | 建议 `channel + store_name` 组合唯一 |
| 建议索引 | `channel`, `warehouse`, `status` |
| 默认状态 | `Draft` |

说明：

- 如果后续出现跨渠道重名店铺，建议新增 `store_code` 并切换为 `field:store_code`

#### 字段字典

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `channel` | 渠道 | `Select` | 是 | `Manual` | 否 | 查询索引 | 如 `Shopee`, `TikTok`, `Shopify`, `Manual` | 电商渠道 |
| `store_name` | 店铺名称 | `Data` | 是 | 无 | 组合唯一 | 查询索引 | 建议与平台店铺名一致 | 店铺显示名 |
| `warehouse` | 履约仓库 | `Link` -> `Warehouse` | 是 | 无 | 否 | 查询索引 | 必须引用有效仓库 | 渠道默认发货仓 |
| `price_list` | 默认价格表 | `Link` -> `Price List` | 否 | 无 | 否 | 无 | 引用有效价格表 | 渠道默认售价规则 |
| `status` | 状态 | `Select` | 是 | `Draft` | 否 | 查询索引 | `Draft`, `Active`, `Disabled` | 店铺使用状态 |
| `api_config_ref` | 接口配置标识 | `Data` | 否 | 无 | 否 | 无 | 可存外部密钥映射名 | 对接时使用 |

#### 业务规则

- 同一渠道下店铺名建议唯一
- `status = Active` 时建议必须已设置仓库

### 8. Production Ticket

用途：

- 作为生产批次卡或流转卡
- 跟踪款色在不同工序之间的进度

#### DocType 级定义

| 项目 | 建议值 |
|---|---|
| 模块 | `garment_mfg` |
| 表类型 | 主表 |
| `autoname` | `format:PT-{YYYY}-{#####}` |
| 主显示字段 | `style` |
| 搜索字段 | `name, style, color_code, supplier` |
| 主要唯一约束 | `name` 自动唯一 |
| 建议索引 | `style`, `stage`, `status`, `supplier`, `planned_start_date` |
| 默认状态 | `Draft` |
| 默认工序 | `Planned` |

#### 字段字典

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `style` | 款号 | `Link` -> `Style` | 是 | 无 | 否 | 查询索引 | 必须引用有效 `Style` | 生产主体 |
| `item_template` | 模板货品 | `Link` -> `Item` | 否 | 无 | 否 | 无 | 对应模板货品 | 与 ERPNext 物料联动 |
| `color_code` | 色号 | `Data` | 是 | 无 | 否 | 查询索引 | 建议与 `Style Color.color_code` 或 `Color Group.color_group_code` 一致 | 生产颜色 |
| `qty` | 计划数量 | `Int` | 是 | `0` | 否 | 无 | 非负整数 | 批次计划量 |
| `bom_no` | BOM | `Link` -> `BOM` | 否 | 无 | 否 | 无 | 引用有效 BOM | 生产所用 BOM |
| `work_order` | 工单 | `Link` -> `Work Order` | 否 | 无 | 否 | 查询索引 | 引用有效工单 | 与标准生产联动 |
| `supplier` | 委外工厂 | `Link` -> `Supplier` | 否 | 无 | 否 | 查询索引 | 引用有效供应商 | 委外生产时使用 |
| `stage` | 当前工序 | `Select` | 是 | `Planned` | 否 | 查询索引 | `Planned`, `Cutting`, `Stitching`, `Finishing`, `Packing`, `Done` | 当前生产环节 |
| `status` | 状态 | `Select` | 是 | `Draft` | 否 | 查询索引 | `Draft`, `In Progress`, `Hold`, `Completed`, `Cancelled` | 业务状态 |
| `planned_start_date` | 计划开始日期 | `Date` | 否 | 无 | 否 | 查询索引 | 日期 | 计划排产 |
| `planned_end_date` | 计划结束日期 | `Date` | 否 | 无 | 否 | 无 | 日期 | 计划完工 |
| `actual_start_date` | 实际开始日期 | `Date` | 否 | 无 | 否 | 无 | 日期 | 实际开工 |
| `actual_end_date` | 实际结束日期 | `Date` | 否 | 无 | 否 | 无 | 日期 | 实际完工 |
| `defect_qty` | 次品数量 | `Int` | 否 | `0` | 否 | 无 | 非负整数 | 汇总不良数 |
| `remark` | 备注 | `Small Text` | 否 | 无 | 否 | 无 | 自由文本 | 异常说明 |
| `stage_logs` | 工序日志 | `Table` -> `Production Stage Log` | 否 | 无 | 否 | 无 | 可为空 | 工序明细 |

#### 业务规则

- `qty`、`defect_qty` 必须为非负数
- `status = Completed` 时建议必须存在 `actual_end_date`
- `stage = Done` 时，`status` 不应保持 `Draft`

### 9. Production Stage Log

用途：

- 记录生产卡在各工序的投入、产出与不良情况

#### DocType 级定义

| 项目 | 建议值 |
|---|---|
| 模块 | `garment_mfg` |
| 表类型 | 子表 |
| 上级 DocType | `Production Ticket` |
| 主要唯一约束 | 初期不做唯一约束 |
| 建议索引 | 如日志量大，后期加 `parent + stage + log_time` 组合索引 |
| 默认时间 | `Now` |

#### 字段字典

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `stage` | 工序 | `Select` | 是 | 无 | 否 | 无 | 与主表工序枚举一致 | 当前日志所属工序 |
| `qty_in` | 投入数 | `Int` | 否 | `0` | 否 | 无 | 非负整数 | 投入数量 |
| `qty_out` | 产出数 | `Int` | 否 | `0` | 否 | 无 | 非负整数 | 完成数量 |
| `defect_qty` | 不良数 | `Int` | 否 | `0` | 否 | 无 | 非负整数 | 工序不良 |
| `warehouse` | 去向仓库 | `Link` -> `Warehouse` | 否 | 无 | 否 | 无 | 引用有效仓库 | 完成后去向 |
| `supplier` | 委外方 | `Link` -> `Supplier` | 否 | 无 | 否 | 无 | 引用有效供应商 | 委外工序使用 |
| `log_time` | 记录时间 | `Datetime` | 是 | `Now` | 否 | 无 | 当前时间 | 日志时间戳 |
| `remark` | 备注 | `Small Text` | 否 | 无 | 否 | 无 | 自由文本 | 异常说明 |

#### 业务规则

- `qty_in`、`qty_out`、`defect_qty` 必须为非负数
- 若存在委外工序，建议同步记录 `supplier`

## 扩展标准 ERPNext DocType

以下字段建议优先通过 `Custom Field` 实现。

### 1. Item

用途：

- 第一阶段直接把标准 `Item` 作为 SKU 层实现对象
- 通过“复用标准字段 + 少量自定义字段”实现女装 SKU 管理

标准字段复用建议：

| 业务概念 | 优先采用的标准字段 | 说明 |
|---|---|---|
| `sku_code` | `Item.item_code` | 不建议重复增加同义自定义字段 |
| `barcode` | ERPNext 标准条码字段或 `Item Barcode` | 避免重复造字段 |
| `weight` | 标准重量字段 | 优先复用 ERPNext 自带重量定义 |
| `batch_enable` | 标准批次开关字段 | 不建议新增重复布尔字段 |

建议新增的自定义字段：

- 款号维度
- 颜色尺码维度
- 可售控制
- 运营控制

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `style` | 款号 | `Link` -> `Style` | 否 | 无 | 否 | 查询索引 | 引用有效 `Style` | SKU 所属款号 |
| `style_code` | 款号编码 | `Data` | 否 | 自动带出 | 否 | 无 | 从 `Style` 获取 | 冗余展示字段 |
| `color_code` | 主颜色代码 | `Data` | 否 | 无 | 否 | 查询索引 | 如 `BLK`, `WHT` | 用于矩阵和命名 |
| `color_name` | 具体颜色名 | `Data` | 否 | 无 | 否 | 查询索引 | 如黑色、奶油白 | 给员工看 |
| `size_system` | 尺码体系 | `Link` -> `Size System` | 否 | 自动带出 | 否 | 查询索引 | 从 `Style` 获取 | 用于约束尺码 |
| `size_code` | 尺码代码 | `Data` | 否 | 无 | 否 | 查询索引 | 如 `M`, `28`, `ONE` | SKU 尺码编码 |
| `size_name` | 尺码名称 | `Data` | 否 | 无 | 否 | 无 | 可与代码相同 | 给员工看 |
| `safe_stock` | 安全库存 | `Float` | 否 | `0` | 否 | 无 | 非负数 | 低于此值提醒 |
| `default_location` | 默认库位 | `Link` -> `Warehouse Location` | 否 | 无 | 否 | 查询索引 | 引用受控库位字典 | 常用上架或拣货位 |
| `sellable` | 是否可售 | `Check` | 否 | `1` | 否 | 查询索引 | `1/0` | 某些 SKU 可停卖 |
| `sku_status` | SKU 状态 | `Select` | 否 | `正常` | 否 | 查询索引 | `正常`, `停产`, `停售`, `冻结` | 运营状态 |
| `remark` | 备注 | `Small Text` | 否 | 无 | 否 | 无 | 自由文本 | 如直播爆款尺码说明 |

补充建议：

- `Item.item_code` 应直接采用 SKU 编码规则
- 若矩阵查询频繁，后续增加组合索引：`(style, color_code, size_code)`
- `default_location` 已切换为 `Link -> Warehouse Location`

### 2. Sales Order

用途：

- 补充电商渠道来源信息

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `channel` | 渠道 | `Data` | 否 | 无 | 否 | 查询索引 | 如 `TikTok`, `Shopee` | 订单来源渠道 |
| `channel_store` | 来源店铺 | `Link` -> `Channel Store` | 否 | 无 | 否 | 查询索引 | 引用有效店铺 | 店铺维度分析 |
| `external_order_id` | 外部订单号 | `Data` | 否 | 无 | 组合唯一 | 查询索引 | 建议与店铺组合唯一 | 平台单号 |
| `biz_type` | 业务类型 | `Select` | 否 | `Retail` | 否 | 无 | `Retail`, `Wholesale`, `Presale`, `Exchange` | 订单分类 |

补充建议：

- 后续增加组合索引：`(channel_store, external_order_id)`

### 3. Sales Order Item

用途：

- 在订单明细中保留款色码信息，方便矩阵统计

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `style` | 款号 | `Link` -> `Style` | 否 | 无 | 否 | 查询索引 | 引用有效 `Style` | 订单明细所属款号 |
| `color_code` | 主颜色代码 | `Data` | 否 | 无 | 否 | 查询索引 | 建议与 SKU 色号一致 | 明细颜色代码 |
| `color_name` | 具体颜色名 | `Data` | 否 | 无 | 否 | 无 | 建议与 SKU 颜色一致 | 明细颜色名称 |
| `size_code` | 尺码代码 | `Data` | 否 | 无 | 否 | 查询索引 | 建议与 SKU 尺码一致 | 明细尺码代码 |
| `size_name` | 尺码名称 | `Data` | 否 | 无 | 否 | 无 | 建议与 SKU 尺码一致 | 明细尺码名称 |
| `platform_sku` | 平台 SKU | `Data` | 否 | 无 | 否 | 无 | 平台原始编码 | 渠道对账使用 |
| `is_presale` | 是否预售 | `Check` | 否 | `0` | 否 | 无 | `1/0` | 预售订单识别 |

### 4. BOM

用途：

- 在标准 BOM 上补充款号和版本视角

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `style` | 款号 | `Link` -> `Style` | 否 | 无 | 否 | 查询索引 | 引用有效 `Style` | BOM 对应款号 |
| `bom_type` | BOM 类型 | `Select` | 否 | `Bulk` | 否 | 查询索引 | `Sample`, `Bulk`, `Packaging` | BOM 分类 |
| `sample_or_bulk` | 样衣/大货 | `Select` | 否 | 无 | 否 | 无 | 可选简化字段 | 兼容不同用户习惯 |
| `version_no` | BOM 版本号 | `Data` | 否 | `V1` | 组合唯一 | 查询索引 | 建议格式 `V1`, `V2` | 同款多版 BOM |

补充建议：

- 后续增加组合索引：`(style, bom_type, version_no)`

### 5. Work Order

用途：

- 在标准工单上补充款号与生产卡关联

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `style` | 款号 | `Link` -> `Style` | 否 | 无 | 否 | 查询索引 | 引用有效 `Style` | 生产款号 |
| `production_ticket` | 生产卡 | `Link` -> `Production Ticket` | 否 | 无 | 否 | 查询索引 | 引用有效生产卡 | 与自定义流转卡关联 |
| `color_code` | 主颜色代码 | `Data` | 否 | 无 | 否 | 无 | 建议与色号一致 | 工单颜色代码 |
| `size_range` | 尺码范围 | `Data` | 否 | 无 | 否 | 无 | 如 `S-XL` | 便于工单摘要 |

补充建议：

- 后续增加组合索引：`(style, production_ticket)`

### 6. Purchase Order

用途：

- 采购单中增加款号和预计使用信息

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `style` | 款号 | `Link` -> `Style` | 否 | 无 | 否 | 查询索引 | 引用有效 `Style` | 采购关联款号 |
| `material_type` | 物料类型 | `Data` | 否 | 无 | 否 | 无 | 如面料、辅料 | 便于分析 |
| `planned_use_date` | 预计使用日期 | `Date` | 否 | 无 | 否 | 无 | 日期 | 预计投产日期 |

### 7. Stock Entry Detail

用途：

- 补足库存凭证明细中的款色码和生产卡信息

| 字段代码 | 中文标签 | 类型 | 必填 | 默认值 | 唯一性 | 索引 | 命名/取值规则 | 说明 |
|---|---|---|---:|---|---|---|---|---|
| `style` | 款号 | `Link` -> `Style` | 否 | 无 | 否 | 查询索引 | 引用有效 `Style` | 关联款号 |
| `color_code` | 主颜色代码 | `Data` | 否 | 无 | 否 | 查询索引 | 建议与色号一致 | 关联颜色代码 |
| `size_code` | 尺码代码 | `Data` | 否 | 无 | 否 | 查询索引 | 建议与尺码一致 | 关联尺码代码 |
| `production_ticket` | 生产卡 | `Link` -> `Production Ticket` | 否 | 无 | 否 | 查询索引 | 引用有效生产卡 | 跟踪来源 |

## 页面与操作按钮

### Style 表单按钮

- `Create Template Item`：创建模板货品
- `Generate Variants`：按颜色与尺码生成 SKU
- `Create BOM`：后续若启用面辅料扩展，再根据材料结构生成 BOM 草稿
- `Open Matrix`：打开颜色尺码矩阵
- `Create Production Ticket`：快速生成生产卡

### Style Matrix 页面

用途：

- 以矩阵方式查看款号颜色尺码库存

建议筛选：

- `Style`
- `Warehouse`
- `Price List`
- `Include Inactive`

建议矩阵定义：

- 行：颜色
- 列：尺码
- 单元格：`On Hand / Reserved / Available`

建议操作：

- `Generate Missing Variants`
- `Batch Update Price`
- `Export CSV`

### Production Board 页面

用途：

- 展示多张生产卡在不同工序中的分布

建议列：

- `Planned`
- `Cutting`
- `Stitching`
- `Finishing`
- `Packing`
- `Done`

建议筛选：

- `Date Range`
- `Style`
- `Supplier`
- `Status`

卡片摘要建议：

- `ticket_no`
- `style_code`
- `color_code`
- `qty`
- `supplier`

## 第一阶段建议实施范围

建议先实现：

1. `Style`
2. `Style Color`
3. `Color Group`
4. `Color`
5. `Size System`
6. `Size Code`
7. `Item` 作为 SKU 层扩展实现
8. `Style Matrix` 页面
9. `Generate Variants` 动作
10. `Production Ticket`
11. `Production Stage Log`

第一阶段建议扩展的标准 DocType 字段：

- `Brand`：`brand_abbr`
- `Item`：`style`、`sku_code`、`color_code`、`color_name`、`size_code`、`size_name`、`safe_stock`、`default_location`、`sellable`、`sku_status`
- `Sales Order`：`channel`、`channel_store`
- `Sales Order Item`：`style`、`color`、`size`
- `Work Order`：`style`、`production_ticket`

## 冻结后的剩余设计问题

以下不再属于 `T000` 口径确认，而是后续设计细化问题：

1. `Production Ticket` 最终是否只到款色级，还是扩展到款色码级
2. `Style Category / Style Sub Category` 是否需要父子级联约束
3. `Warehouse Location` 是否与 `Warehouse Zone` 拆表
4. 是否需要在第一阶段就实现组合索引 patch

## 修订建议

- 优先改中文标签和业务描述，谨慎改字段代码名
- 在业务流程没稳定前，不要过早引入大量新 DocType
- 能通过 `Custom Field` 和脚本实现的，先不要做重型定制
- 当你准备落库实现时，再把本文件拆分成：
  - DocType 结构定义
  - 字段清单
  - 命名规则
  - 校验规则
  - 索引 patch 清单
