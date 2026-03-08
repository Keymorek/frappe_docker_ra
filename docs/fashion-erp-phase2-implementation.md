# Fashion ERP 第二阶段实施版

本文档用于冻结 `fashion_erp` 第二阶段范围。

相关文档：

- 总体设计：[fashion-erp-doctype-design.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-doctype-design.md)
- 第一期实施版：[fashion-erp-phase1-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-implementation.md)
- 第二阶段任务清单：[fashion-erp-phase2-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase2-task-list.md)

## 第二阶段结论

1. 第二阶段主题冻结为：`仓储与状态流转`
2. 电商订单同步及平台状态自动回写当前统一按 `外部依赖阻塞/暂停` 处理；现阶段只保留手工同步
3. `Channel Store` 保留，但仅作为手工归类和运营维度，不做平台订单拉取、库存回传、渠道分配
4. 公司当前主营场景是女装电商运营，不是制造型工厂
5. 生产相关能力保留，但优先级后置；内部生产只用于打样辅助
6. 大货入库默认来自第三方外包供应商，而不是内部生产完工

## 第二阶段目标

本阶段先把仓储侧的基础字典和状态口径做稳：

- `Warehouse Zone`
- `Warehouse Location` 增强版
- `Inventory Status`
- 后续的退货原因、退货结果、状态流转规则

目标不是马上做完整 WMS，而是先统一：

- 库位区域口径
- 库位编码口径
- 库存状态字典
- 未来状态流转的落点

## 第二阶段暂不做

- 平台订单自动同步（外部依赖阻塞/暂停）
- 渠道库存回传（外部依赖阻塞/暂停）
- 电商售后自动化回写平台（外部依赖阻塞/暂停）
- 自动分仓
- 平台履约接口（外部依赖阻塞/暂停）
- 车间排产、工序派工、完工入库驱动的生产闭环

补充说明：

- 其中所有平台接口类事项，当前统一按 `外部依赖阻塞/暂停` 处理，待未来拿到稳定平台资格和数据结构后再恢复
- 其中“生产闭环”不是当前主业务矛盾，后续只保留给打样辅助场景

## 当前已进入开发的二阶段对象

1. `Warehouse Zone`
2. `Inventory Status`
3. `Warehouse Location` 字段增强
4. `Return Reason`
5. `Return Disposition`
6. `Stock Entry` 库存状态流转校验
7. `After Sales Ticket`
8. `After Sales Actions`
9. `After Sales Stock Entry Draft`

## 第二阶段收口结论

第二阶段完成后，不再继续往“生产完工映射”方向展开，而是切换到新的第三阶段主题：

`电商运营履约 + 第三方外包入库 + 售后闭环`

后续承接文档：

- [fashion-erp-product-analysis.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-product-analysis.md)
- [fashion-erp-phase3-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-implementation.md)
- [fashion-erp-phase3-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-task-list.md)

补充说明：

- 售后单号建议自动生成，格式为 `YYYYMMDDTK0001`
- 售后工单需要支持关联 `Sales Order / Sales Invoice / Delivery Note`
- 售后明细需要支持关联原始订单行和发货行
