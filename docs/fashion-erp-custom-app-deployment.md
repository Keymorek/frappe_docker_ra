# Fashion ERP 自定义 App 部署与更新教程

本文档用于说明如何在本地服务器上，基于当前 `frappe_docker_ra` 仓库，部署包含自定义 app `fashion_erp` 的生产环境，以及后续每次更新自定义 app 后如何更新线上环境。

适用场景：

- 服务器系统：`Debian 13`
- 部署方式：`Manual production deployment`
- 访问方式：局域网 IP
- 基础应用：`ERPNext 16`
- 自定义 app：`fashion_erp`

## 一、推荐目录和仓库结构

生产环境建议分成两类仓库：

1. `部署仓库`
   - 就是当前仓库：`frappe_docker_ra`
   - 用途：管理 compose、overrides、文档、部署流程
2. `自定义 app 仓库`
   - 建议单独一个私有 GitHub 仓库，例如：`git@github.com:<your-org>/fashion_erp.git`
   - 用途：只放 `fashion_erp` 代码

> 重要：
>
> 当前自定义 app 代码在 [custom_apps/fashion_erp](E:\Dropbox\Syn\Project\frappe_docker_ra\custom_apps\fashion_erp)。
> 生产镜像构建时，推荐把这个目录内容同步到独立私有仓库，再通过 `apps.json` 拉取。
> 不建议长期直接修改运行中的容器，也不建议靠 `docker cp` 维护生产 app。

推荐服务器目录：

```text
/opt/frappe_docker_ra            # 部署仓库
~/gitops                         # env 和最终 compose 文件
~/fashion-build                  # apps.json 和镜像构建辅助文件
```

## 二、第一次部署前的准备

### 1. 准备自定义 app 仓库

把 [custom_apps/fashion_erp](E:\Dropbox\Syn\Project\frappe_docker_ra\custom_apps\fashion_erp) 的内容作为一个独立仓库提交到 GitHub。

这个仓库根目录应至少包含：

```text
fashion_erp/
pyproject.toml
setup.py
MANIFEST.in
requirements.txt
README.md
```

### 2. 让服务器有权限拉取私有仓库

如果你的 `fashion_erp` 仓库是 GitHub 私有仓库，服务器需要具备访问权限。

推荐用 SSH：

```bash
ssh -T git@github.com
```

如果提示认证成功，说明后续 `docker build` 能通过 `apps.json` 拉取自定义 app。

### 3. 准备部署仓库

假设部署仓库放在：

```bash
/opt/frappe_docker_ra
```

并且你已经完成 Docker 和 `docker compose` 安装。

## 三、第一次部署包含自定义 app 的生产环境

### 步骤 1：准备 `apps.json`

在服务器创建：

```bash
mkdir -p ~/fashion-build
cd ~/fashion-build
```

创建 `apps.json`：

```json
[
  {
    "url": "https://github.com/frappe/erpnext",
    "branch": "version-16"
  },
  {
    "url": "git@github.com:<your-org>/fashion_erp.git",
    "branch": "main"
  }
]
```

说明：

- `erpnext` 仍然通过官方仓库进入镜像
- `fashion_erp` 使用你自己的私有仓库
- 如果你的 app 分支不是 `main`，按实际修改

### 步骤 2：生成 `APPS_JSON_BASE64`

```bash
cd ~/fashion-build
export APPS_JSON_BASE64=$(base64 -w 0 apps.json)
```

### 步骤 3：构建生产镜像

进入部署仓库：

```bash
cd /opt/frappe_docker_ra
```

构建镜像：

```bash
docker build \
  --build-arg FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg FRAPPE_BRANCH=version-16 \
  --build-arg APPS_JSON_BASE64=$APPS_JSON_BASE64 \
  --tag fashion-erp:16-prod \
  --file images/layered/Containerfile .
```

构建完成后可确认：

```bash
docker images | grep fashion-erp
```

### 步骤 4：准备生产环境变量

创建：

```bash
mkdir -p ~/gitops
cp /opt/frappe_docker_ra/example.env ~/gitops/erpnext-lan.env
```

编辑 `~/gitops/erpnext-lan.env`，至少确认这些变量：

```env
ERPNEXT_VERSION=v16.8.2
DB_PASSWORD=这里换成强密码
HTTP_PUBLISH_PORT=8080
FRAPPE_SITE_NAME_HEADER=rserp.local

CUSTOM_IMAGE=fashion-erp
CUSTOM_TAG=16-prod
PULL_POLICY=never
```

说明：

- `CUSTOM_IMAGE` 和 `CUSTOM_TAG` 指向你刚构建的本地镜像
- `PULL_POLICY=never` 避免 Docker 去远程拉同名镜像
- `FRAPPE_SITE_NAME_HEADER` 应与你实际站点名一致

### 步骤 5：生成最终 compose 文件

```bash
docker compose --env-file ~/gitops/erpnext-lan.env \
  -f /opt/frappe_docker_ra/compose.yaml \
  -f /opt/frappe_docker_ra/overrides/compose.mariadb.yaml \
  -f /opt/frappe_docker_ra/overrides/compose.redis.yaml \
  -f /opt/frappe_docker_ra/overrides/compose.noproxy.yaml \
  config > ~/gitops/erpnext-lan.yaml
```

### 步骤 6：启动生产栈

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml up -d
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml ps -a
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml logs -f configurator
```

确认条件：

- `db` 为健康状态
- `configurator` 为 `Exited (0)`
- `backend / frontend / websocket / queue-short / queue-long / scheduler` 为 `Up`

### 步骤 7：创建站点并安装应用

在执行 `new-site` 或 `install-app fashion_erp` 之前，先在代码目录运行一次静态安装验收：

```bash
cd /opt/frappe_docker_ra
python3 custom_apps/fashion_erp/tests/app_structure_validation.py
python3 -m unittest custom_apps.fashion_erp.tests.unit.test_app_structure_validation
```

通过标准：

- 输出 `fashion_erp static structure validation passed.`
- `test_app_structure_validation` 全部通过
- 如果任一命令失败，先修复代码结构问题，不要继续安装

如果是第一次新建站点：

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench new-site rserp.local \
  --mariadb-user-host-login-scope='%' \
  --db-root-password '这里填 DB_PASSWORD' \
  --admin-password '这里填管理员密码' \
  --install-app erpnext
```

然后安装自定义 app：

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local install-app fashion_erp
```

### 步骤 8：首次部署后的必要命令

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local migrate

docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local clear-cache
```

如果前端资源没有刷新，再执行：

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench build --app fashion_erp
```

### 步骤 9：验证自定义 app 是否已装好

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local list-apps
```

应至少看到：

- `frappe`
- `erpnext`
- `fashion_erp`

## 四、如果你已经有现成站点，如何接入自定义 app

如果你的 `rserp.local` 已经跑起来，只是还没有接入 `fashion_erp`，则顺序改为：

1. 构建包含 `fashion_erp` 的镜像
2. 修改 `CUSTOM_IMAGE / CUSTOM_TAG`
3. 重新生成 compose 文件
4. `up -d`
5. 执行：

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local install-app fashion_erp
```

然后再执行：

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local migrate

docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local clear-cache
```

## 五、每次更新自定义 app 后如何更新生产环境

这一部分是最重要的日常流程。

原则：

- 不要直接改运行中的容器
- 不要把代码手工复制到容器
- 每次更新都走“提交代码 -> 重建镜像 -> 重新部署 -> migrate”流程

### 步骤 1：在本地修改 `fashion_erp`

修改你自己的 app 仓库，然后提交并推送到 GitHub。

### 步骤 2：服务器重新生成 `APPS_JSON_BASE64`

如果 `apps.json` 没变，也建议重新执行一次：

```bash
cd ~/fashion-build
export APPS_JSON_BASE64=$(base64 -w 0 apps.json)
```

### 步骤 3：重新构建镜像

推荐做法是每次更新一个新 tag，而不是永远覆盖同一个 tag。

构建镜像前，先重新执行一次静态安装验收：

```bash
cd /opt/frappe_docker_ra
python3 custom_apps/fashion_erp/tests/app_structure_validation.py
python3 -m unittest custom_apps.fashion_erp.tests.unit.test_app_structure_validation
```

如果这两步未通过，不要进入镜像构建和站点升级。

例如：

```bash
cd /opt/frappe_docker_ra

docker build \
  --build-arg FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg FRAPPE_BRANCH=version-16 \
  --build-arg APPS_JSON_BASE64=$APPS_JSON_BASE64 \
  --tag fashion-erp:16-20260307-1 \
  --file images/layered/Containerfile .
```

### 步骤 4：更新 env 中的镜像 tag

编辑：

```bash
~/gitops/erpnext-lan.env
```

把：

```env
CUSTOM_TAG=16-prod
```

改成：

```env
CUSTOM_TAG=16-20260307-1
```

### 步骤 5：重新生成 compose 文件

```bash
docker compose --env-file ~/gitops/erpnext-lan.env \
  -f /opt/frappe_docker_ra/compose.yaml \
  -f /opt/frappe_docker_ra/overrides/compose.mariadb.yaml \
  -f /opt/frappe_docker_ra/overrides/compose.redis.yaml \
  -f /opt/frappe_docker_ra/overrides/compose.noproxy.yaml \
  config > ~/gitops/erpnext-lan.yaml
```

### 步骤 6：重新部署容器

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml up -d
```

### 步骤 7：执行站点迁移

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local migrate
```

### 步骤 8：清缓存

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local clear-cache
```

### 步骤 9：如果有明显前端变更，再补一次 build

正常情况下，镜像里已经包含最新代码，不应依赖线上 build。

只有在前端资源没有更新时，再执行：

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench build --app fashion_erp
```

## 六、推荐的日常更新命令清单

每次更新你自己的 app 后，服务器侧一般只需要执行这组命令：

```bash
cd ~/fashion-build
export APPS_JSON_BASE64=$(base64 -w 0 apps.json)

cd /opt/frappe_docker_ra
docker build \
  --build-arg FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg FRAPPE_BRANCH=version-16 \
  --build-arg APPS_JSON_BASE64=$APPS_JSON_BASE64 \
  --tag fashion-erp:16-<新版本标签> \
  --file images/layered/Containerfile .

docker compose --env-file ~/gitops/erpnext-lan.env \
  -f /opt/frappe_docker_ra/compose.yaml \
  -f /opt/frappe_docker_ra/overrides/compose.mariadb.yaml \
  -f /opt/frappe_docker_ra/overrides/compose.redis.yaml \
  -f /opt/frappe_docker_ra/overrides/compose.noproxy.yaml \
  config > ~/gitops/erpnext-lan.yaml

docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml up -d

docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local migrate

docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml exec backend \
  bench --site rserp.local clear-cache
```

## 七、回滚建议

推荐永远保留上一个镜像 tag。

如果这次更新出问题，回滚方式很简单：

1. 把 `CUSTOM_TAG` 改回上一个版本
2. 重新生成 compose 文件
3. 执行：

```bash
docker compose --project-name erpnext-lan -f ~/gitops/erpnext-lan.yaml up -d
```

如果本次数据库迁移已经改变结构，回滚前要先确认是否兼容。

## 八、不要这样做

不要在生产容器里直接修改 `apps/fashion_erp`

不要通过 `docker cp` 长期维护生产代码

不要每次都用同一个不可追踪的镜像 tag

不要执行：

```bash
docker compose down -v
```

这会删除卷，可能导致数据库和站点数据丢失。

## 九、当前项目最推荐的生产维护方式

对于你当前这个项目，推荐口径是：

1. `frappe_docker_ra` 继续作为部署仓库
2. `fashion_erp` 单独作为私有 app 仓库
3. 生产环境统一通过 `apps.json + docker build` 生成镜像
4. 每次更新都用“新镜像 tag + migrate”的方式上线

这样后续升级 ERPNext、升级自定义 app、回滚问题版本都会简单很多。

## 十、如果在新对话中继续项目，如何快速续接

如果你下次开一个新的对话，建议直接在开头引用下面这些文档作为当前主基线：

1. [fashion-erp-product-analysis.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-product-analysis.md)
2. [fashion-erp-phase3-implementation.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-implementation.md)
3. [fashion-erp-phase3-task-list.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-phase3-task-list.md)
4. [fashion-erp-custom-app-deployment.md](E:\Dropbox\Syn\Project\frappe_docker_ra\docs\fashion-erp-custom-app-deployment.md)

推荐你在新对话里直接这样开头：

```text
继续 fashion_erp 项目。先读取 docs/fashion-erp-product-analysis.md、docs/fashion-erp-phase3-implementation.md、docs/fashion-erp-phase3-task-list.md，按当前计划继续工作。
```

如果你想指定继续某个任务，可以这样写：

```text
继续 fashion_erp 项目。先读取 docs/fashion-erp-product-analysis.md、docs/fashion-erp-phase3-implementation.md、docs/fashion-erp-phase3-task-list.md。当前最新状态是：T405 DONE，T406 DOING，T410 DONE。请继续 T406。
```

如果你希望先做需求分析或计划更新，而不是直接写代码，可以这样写：

```text
继续 fashion_erp 项目。先读取 docs/fashion-erp-product-analysis.md、docs/fashion-erp-phase3-implementation.md、docs/fashion-erp-phase3-task-list.md。先检查文档和代码进度是否一致，再做计划更新，不要先写代码。
```

最稳妥的原则是：

- 让新对话先读 `产品分析 + 第三阶段实施版 + 第三阶段任务清单`
- 如果涉及部署，再补读本文件
- 如果涉及老模块字段设计，再补读 `fashion-erp-doctype-design.md`
