# Fashion ERP 工作日志

## 2026-03-08 安装期静态验收补强

### 事件

本轮在开发站点安装 `fashion_erp` 时，连续出现两类安装期错误：

- `No module named 'fashion_erp.stock.doctype.landed_cost_vendor_invoice'`
- `No module named 'fashion_erp.style.doctype.craft_sheet_log.craft_sheet_log'`

这说明问题并不在业务逻辑本身，而在 `Frappe install-app` 需要的代码结构契约没有被静态验收覆盖到。

### 根因

1. 自定义模块曾使用 `Stock` 作为模块名，和 ERPNext 标准 `Stock` 模块发生命名冲突，导致安装时标准 DocType 被错误解析到 `fashion_erp.stock.*`。
2. 多个子表 DocType 目录只有 `.json` 和 `__init__.py`，缺少 Frappe 在安装期会导入的同名 Python 控制器文件。
3. 原有静态验收主要覆盖服务层单测和定向搜索，没有覆盖 `modules.txt`、模块包名、DocType 控制器、Script Report 文件完整性这类安装前结构检查。

### 本次修复

1. 将自定义模块 `Stock` 重命名为 `Fashion Stock`，并把 Python 包目录统一改为 `fashion_stock`。
2. 一次性补齐缺失的 Doctype 控制器文件，包括：
   - `Craft Sheet Log`
   - `Sample Ticket Log`
   - `Order Sync Batch Item`
   - `After Sales Item`
   - `After Sales Log`
   - `Outsource Order Material`
   - `Outsource Order Log`
   - `Outsource Receipt Item`
   - `Outsource Receipt Log`
3. 新增静态结构校验脚本 [app_structure_validation.py](/mnt/e/Dropbox/Syn/Project/frappe_docker_ra/custom_apps/fashion_erp/tests/app_structure_validation.py)，覆盖以下规则：
   - `modules.txt` 声明的模块必须有对应 Python 包目录
   - 自定义模块包名不能使用标准 Frappe / ERPNext 保留包名
   - `DocType` 目录必须同时具备 `__init__.py` 和同名控制器 `.py`
   - `Script Report` 必须具备同名 `.py` 与 `.js`
   - `DocType / Report` JSON 中的 `module` 必须与 `modules.txt` 和实际目录一致
   - 不允许存在未在 `modules.txt` 中声明却承载 `doctype/report/workspace` 的模块目录
4. 新增单测 [test_app_structure_validation.py](/mnt/e/Dropbox/Syn/Project/frappe_docker_ra/custom_apps/fashion_erp/tests/unit/test_app_structure_validation.py)，把上述结构校验纳入默认 `unittest` 回归。

### 新的静态验收要求

从本条日志起，任何进入安装、镜像构建、站点升级的版本，都必须先通过以下两条命令：

```bash
python3 custom_apps/fashion_erp/tests/app_structure_validation.py
python3 -m unittest custom_apps.fashion_erp.tests.unit.test_app_structure_validation
```

不允许再跳过这一步直接执行 `bench new-site`、`bench install-app` 或镜像构建。

### 验证结果

- 静态结构校验：通过
- 单测回归：`python3 -m unittest discover -s custom_apps/fashion_erp/tests/unit -p 'test_*.py'` 通过

### 防再发要求

1. 后续新增任何 `DocType / Report / 模块重命名`，必须同步检查结构校验是否仍然通过。
2. 涉及模块名调整时，必须同时检查：
   - `modules.txt`
   - Python 包目录
   - JSON `module`
   - `hooks.py`
   - fixtures 和报表路径
3. 如果安装期再次出现结构类问题，优先补静态校验规则，禁止只修当前报错而不补预防措施。
