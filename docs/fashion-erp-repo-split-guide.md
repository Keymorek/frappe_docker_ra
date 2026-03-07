# Fashion ERP 仓库拆分与维护说明

本文档用于说明如何把当前项目中的 `custom_apps/fashion_erp` 拆分成独立私有 GitHub 仓库，同时保留当前 `frappe_docker_ra` 作为部署仓库，避免后续开发失去指导文档和上下文。

## 一、拆分目标

当前建议的仓库结构是：

1. `frappe_docker_ra`
   - 角色：部署仓库
   - 用途：Docker Compose、镜像构建、环境变量、服务器部署、生产更新
2. `fashion_erp`
   - 角色：应用开发仓库
   - 用途：业务代码、DocType、fixtures、hooks、patches、应用级设计文档、开发计划

这样拆分的目标是：

- 让 `fashion_erp` 成为真正独立可发布的 app
- 让生产部署继续沿用当前 `frappe_docker_ra`
- 让开发文档跟着 app 走，避免后续迭代时文档和代码脱节

## 二、推荐拆分原则

判断规则很简单：

- 跟“应用代码和业务设计”有关的，放 `fashion_erp` 仓库
- 跟“镜像构建和生产部署”有关的，留在 `frappe_docker_ra`

## 三、必须迁移到 `fashion_erp` 私有仓库的内容

下面这些内容应作为 `fashion_erp` 应用仓库的主体：

### 1. 应用代码目录

必须迁移：

- [custom_apps/fashion_erp/fashion_erp](E:\Dropbox\Syn\Project\frappe_docker_ra\custom_apps\fashion_erp\fashion_erp)

这里面包括：

- `doctype/`
- `services/`
- `events/`
- `workspace/`
- `fixtures/`
- `patches/`
- `translations/`
- `locale/`
- `hooks.py`
- `install.py`
- `modules.txt`
- `patches.txt`

### 2. 应用打包文件

必须迁移：

- [custom_apps/fashion_erp\pyproject.toml](E:\Dropbox\Syn\Project\frappe_docker_ra\custom_apps\fashion_erp\pyproject.toml)
- [custom_apps/fashion_erp\setup.py](E:\Dropbox\Syn\Project\frappe_docker_ra\custom_apps\fashion_erp\setup.py)
- [custom_apps/fashion_erp\MANIFEST.in](E:\Dropbox\Syn\Project\frappe_docker_ra\custom_apps\fashion_erp\MANIFEST.in)
- [custom_apps/fashion_erp\requirements.txt](E:\Dropbox\Syn\Project\frappe_docker_ra\custom_apps\fashion_erp\requirements.txt)
- [custom_apps/fashion_erp\README.md](E:\Dropbox\Syn\Project\frappe_docker_ra\custom_apps\fashion_erp\README.md)
- [custom_apps/fashion_erp\license.txt](E:\Dropbox\Syn\Project\frappe_docker_ra\custom_apps\fashion_erp\license.txt)

## 四、建议一并迁移到 `fashion_erp` 私有仓库的文档

这些文档属于“应用设计与开发计划”，建议也放进 `fashion_erp` 仓库：

- [fashion-erp-product-analysis.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-product-analysis.md)
- [fashion-erp-phase1-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-implementation.md)
- [fashion-erp-phase1-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-task-list.md)
- [fashion-erp-phase1-file-map.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase1-file-map.md)
- [fashion-erp-phase2-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase2-implementation.md)
- [fashion-erp-phase2-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase2-task-list.md)
- [fashion-erp-phase3-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-implementation.md)
- [fashion-erp-phase3-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-task-list.md)
- [fashion-erp-doctype-design.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-doctype-design.md)
- [fashion-erp-after-sales-ticket-design.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-after-sales-ticket-design.md)

建议在新仓库中放到类似目录：

```text
docs/
  fashion-erp-product-analysis.md
  fashion-erp-phase1-implementation.md
  fashion-erp-phase1-task-list.md
  fashion-erp-phase1-file-map.md
  fashion-erp-phase2-implementation.md
  fashion-erp-phase2-task-list.md
  fashion-erp-phase3-implementation.md
  fashion-erp-phase3-task-list.md
  fashion-erp-doctype-design.md
  fashion-erp-after-sales-ticket-design.md
```

## 五、应继续留在 `frappe_docker_ra` 的内容

下面这些内容属于部署和运维，不建议迁到 `fashion_erp` 应用仓库：

### 1. Docker 和 Compose 相关

保留在当前部署仓库：

- `compose.yaml`
- `overrides/`
- `images/`
- `example.env`
- `pwd.yml`

### 2. Frappe Docker 原始部署文档

包括：

- `docs/01-getting-started/`
- `docs/02-setup/`
- `docs/04-operations/`

这些是部署方法参考，不属于 `fashion_erp` 应用本体。

### 3. 自定义 app 部署教程

这个文档应继续留在部署仓库：

- [fashion-erp-custom-app-deployment.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-custom-app-deployment.md)

原因：

- 它描述的是如何基于 `frappe_docker_ra` 构建和更新生产镜像
- 它天然属于部署流程，而不是 app 内部开发文档

### 4. 仓库拆分说明

本文件也建议保留在部署仓库：

- [fashion-erp-repo-split-guide.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-repo-split-guide.md)

## 六、推荐的迁移顺序

建议不要一次性清空当前仓库，而是按下面顺序过渡：

### 第一步：创建私有仓库

例如：

```text
git@github.com:<your-org>/fashion_erp.git
```

### 第二步：把 app 代码复制进去

至少复制：

```text
custom_apps/fashion_erp/fashion_erp
custom_apps/fashion_erp/pyproject.toml
custom_apps/fashion_erp/setup.py
custom_apps/fashion_erp/MANIFEST.in
custom_apps/fashion_erp/requirements.txt
custom_apps/fashion_erp/README.md
custom_apps/fashion_erp/license.txt
```

### 第三步：把核心开发文档复制进去

至少先复制这些：

- `fashion-erp-product-analysis.md`
- `fashion-erp-phase3-implementation.md`
- `fashion-erp-phase3-task-list.md`
- `fashion-erp-doctype-design.md`

### 第四步：让部署仓库继续保留一份

在过渡阶段，建议 `frappe_docker_ra` 里先保留这些文档，不要马上删除。

原因：

- 你当前所有上下文还在这里
- 以后排查部署问题时，仍然可能需要和部署仓库一起阅读

### 第五步：以后新需求优先更新 app 仓库

从你开始正式分仓之后，原则改成：

- 业务设计文档优先更新 `fashion_erp` 仓库
- 部署方法文档优先更新 `frappe_docker_ra`

## 七、拆分后的推荐维护方式

### `fashion_erp` 仓库负责

1. 业务代码
2. 业务设计文档
3. 开发计划和任务拆分
4. 字段字典和对象设计
5. 自定义 app 的 README

### `frappe_docker_ra` 仓库负责

1. Docker 镜像构建
2. `apps.json` 使用方式
3. 生产环境部署
4. 生产环境更新与回滚
5. 服务器环境变量
6. 自定义 app 部署教程

## 八、最小可行拆分方案

如果你想先最小化成本，不想一次迁太多文件，我建议先这样：

### 先迁过去

- `custom_apps/fashion_erp/` 下全部应用代码与打包文件
- `fashion-erp-product-analysis.md`
- `fashion-erp-phase3-implementation.md`
- `fashion-erp-phase3-task-list.md`

### 先留在这里

- 其它历史文档
- 部署文档
- Frappe Docker 原始文档

这样就已经足够支撑：

- 后续开发继续进行
- 生产镜像通过 `apps.json` 构建
- 不会马上失去当前项目的指导性文件

## 九、一句话结论

最推荐的做法不是“把所有东西都搬走”，而是：

1. 把 `fashion_erp` 代码和核心开发文档迁到独立私有仓库
2. 把 `frappe_docker_ra` 保留为部署仓库
3. 过渡期两边都保留文档
4. 后续新需求优先在 `fashion_erp` 仓库维护产品和开发文档

这样既不会失去上下文，也能让后续开发和部署逐步走向标准化。
