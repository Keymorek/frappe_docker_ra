# Codex Environment Setup

本文档说明如何为当前 `frappe_docker_ra` 仓库配置 Codex 环境，并让 Codex 能实际开发本地 `fashion_erp` 自定义 app。

## 1. 先区分两类环境

这个项目在 Codex 里建议分成两层：

- Codex setup script
  - 只做环境检查和下一步提示
  - 不负责启动 Docker 服务，也不写敏感变量
- 项目运行环境
  - 开发态走 `devcontainer-example/docker-compose.yml`
  - 部署态或镜像验证走 `compose.yaml + overrides + .env`

不要把 `.env` 里的业务变量塞进 Codex setup script。

## 2. Codex 里应该填什么 setup script

当前项目已有可复用脚本 [scripts/codex-env-check.sh](/mnt/e/Dropbox/Syn/Project/frappe_docker_ra/scripts/codex-env-check.sh)。

在 Codex 的环境设置界面里，把 setup script 设成：

```bash
cd /mnt/e/Dropbox/Syn/Project/frappe_docker_ra
bash scripts/codex-env-check.sh
```

这个脚本会检查：

- `compose.yaml`
- `example.env`
- `devcontainer-example/docker-compose.yml`
- `development/installer.py`
- `custom_apps/fashion_erp`
- `.env`
- `.devcontainer/docker-compose.yml`

## 3. 推荐给 Codex 的开发模式

如果目的是让 Codex 修改 `fashion_erp` 并能跑起来，优先使用开发态，不要直接拿生产 compose 作为开发环境。

原因很简单：

- [compose.yaml](/mnt/e/Dropbox/Syn/Project/frappe_docker_ra/compose.yaml) 默认使用镜像
- 这套运行栈不会直接热更新你仓库里的 `custom_apps/fashion_erp`
- 本地源码开发更适合走 dev container，然后把本地 app 挂进 bench

推荐步骤：

### 主机侧

```bash
cd /mnt/e/Dropbox/Syn/Project/frappe_docker_ra
cp -R devcontainer-example .devcontainer
docker compose -f .devcontainer/docker-compose.yml up -d
docker compose -f .devcontainer/docker-compose.yml exec frappe bash
```

### 容器内

```bash
cd /workspace
bash scripts/bootstrap-fashion-erp-dev.sh
cd /workspace/development/frappe-bench
bench start
```

[scripts/bootstrap-fashion-erp-dev.sh](/mnt/e/Dropbox/Syn/Project/frappe_docker_ra/scripts/bootstrap-fashion-erp-dev.sh) 会完成这些事情：

- 用 `version-16` 初始化 bench
- 创建 `development.localhost` 站点
- 安装 ERPNext
- 把仓库内的 `custom_apps/fashion_erp` 链接到 bench 的 `apps/fashion_erp`
- 用 bench 虚拟环境执行 `pip install -e`
- 在站点安装 `fashion_erp`
- 执行 `migrate`、`build --app fashion_erp`、`clear-cache`

它使用的 ERPNext app 列表文件是 [scripts/apps-erpnext-v16.json](/mnt/e/Dropbox/Syn/Project/frappe_docker_ra/scripts/apps-erpnext-v16.json)。

## 4. 为什么单独提供 `version-16` 脚本

当前开发脚本默认值还是 `version-15`：

- [development/installer.py](/mnt/e/Dropbox/Syn/Project/frappe_docker_ra/development/installer.py#L71)
- [development/apps-example.json](/mnt/e/Dropbox/Syn/Project/frappe_docker_ra/development/apps-example.json#L1)

但这个项目的自定义 app 部署文档是按 ERPNext 16 写的：

- [docs/fashion-erp-custom-app-deployment.md](/mnt/e/Dropbox/Syn/Project/frappe_docker_ra/docs/fashion-erp-custom-app-deployment.md#L5)

所以这里单独提供了 `version-16` 的 Codex 开发引导脚本，避免默认版本不一致。

## 5. 如果只想验证 compose 运行栈

这种情况不需要 bench 开发环境，只需要本地 `.env`：

```bash
cd /mnt/e/Dropbox/Syn/Project/frappe_docker_ra
cp example.env .env
```

最小建议值：

```env
ERPNEXT_VERSION=v16.8.2
DB_PASSWORD=123
HTTP_PUBLISH_PORT=8080
FRAPPE_SITE_NAME_HEADER=development.localhost
```

然后启动：

```bash
docker compose --env-file .env \
  -f compose.yaml \
  -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml \
  -f overrides/compose.noproxy.yaml \
  up -d
```

注意：这条路径更适合镜像验证，不适合直接开发本地 `fashion_erp` 源码。
