# AGENTS.md

## 启动/开发命令

- 本地开发：
  ```bash
  pip install -r requirements.txt
  export SECRET_KEY="$(openssl rand -hex 32)"
  uvicorn app.main:app --host 0.0.0.0 --port 8080
  ```
  需要热重载可自行加 `--reload`；仓库 README 没写，默认不带。

- Docker Compose：
  ```bash
  echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
  docker compose up -d
  ```

- 本地构建镜像：
  ```bash
  docker build -t device-mgr .
  docker run -d -p 8080:8080 -e SECRET_KEY="$(openssl rand -hex 32)" -v "$(pwd)/data:/app/data" device-mgr
  ```
  Dockerfile 默认以 UID/GID 1000 的非 root 用户运行；若本地用户 UID 不同，挂载 `data/` 可能权限不足，可用 `--build-arg USER_UID=$(id -u) USER_GID=$(id -g)` 覆盖。

## 架构入口

- FastAPI 入口是 `app.main:app`。
- `app/main.py` 在模块导入时就调用 `init_db()`，然后注册所有 router 和认证中间件。
- 版本号统一放在项目根目录 `VERSION` 文件中；`app/__init__.py` 会读取它，并注册到 FastAPI `version` 与 `GET /api/version`。
- 静态文件目录 `app/static` 不存在时会被静默跳过挂载。

## 分页

- `/api/stats/devices`、`/api/devices/`、`/api/groups/{id}/devices` 已支持 `page` / `page_size` 参数，默认 `page_size=20`、最大 `500`。
- 返回结构为 `{"total", "page", "page_size", "pages", "items": [...]}`。
- 统计页面已加上分页 UI；分组设备页面默认请求 `page_size=500` 以兼容现有展示。

## 认证与权限

- 除 `/login`、`/api/auth/login`、以 `/static` 开头的路径外，全部请求都需要 `token` Cookie。
- 未登录访问页面会 302 到 `/login`；访问 `/api/*` 会返回 401。
- 中间件把 `user_id`、`user_role`、`username` 放到 `request.state`；后续依赖 `get_current_user` 优先读 state，而不是重新解析 token。
- 角色：`admin` / `user` / `guest`。`require_role(...)` 用于 API 权限控制。
- **CSRF**：登录后服务端会下发 `csrf_token` Cookie；前端 `fetch` 自动为 POST/PUT/DELETE/PATCH 加上 `X-CSRF-Token` header。用 curl 测试写接口时，必须先获取 `csrf_token` Cookie 并在同请求中带上该 header。
- **Token 注销**：退出登录会把当前 JWT 的 `jti` 写入 `token_blacklist` 表，该 token 立即失效。

## 数据层与迁移

- 默认 SQLite：`sqlite:///data/devices.db`，可通过 `DATABASE_URL` 覆盖。
- `app/database.py` 启动时执行：
  1. `Base.metadata.create_all`
  2. 对已有表手动 `ALTER TABLE ADD COLUMN`（白名单硬编码，作为轻量迁移）
  3. 初始化 4 个预设分组（多联机/控制保护器/压缩机/水泵）
  4. 创建默认账户 `admin/admin123`（首次登录必须改密）和 `guest/guest`
  5. 清理已过期的 `token_blacklist` 记录
- 模型时间戳统一使用 UTC（`datetime.now(timezone.utc)`）。
- 重置数据库直接删 `data/devices.db`，重启即可恢复种子状态。

## 环境变量

| 变量 | 说明 |
|------|------|
| `SECRET_KEY` | **必填**，JWT 签名密钥；未设置直接抛 `RuntimeError`。 |
| `DATABASE_URL` | 可选，默认 `sqlite:///data/devices.db`。 |
| `HTTPS` | 设为 `1`/`true`/`yes`/`on` 时 Cookie 启用 `secure` 标志。 |

## 测试/质量工具

- 测试框架已配置为 `pytest`，依赖在 `requirements-dev.txt`。
- 运行测试：
  ```bash
  pip install -r requirements-dev.txt
  export SECRET_KEY="$(openssl rand -hex 32)"
  pytest -q
  ```
- 测试使用内存 SQLite，每个测试前会重置数据库并清空登录限流器。
- 验证部署也可用 README 里的 curl 示例：先 `-c` 登录保存 Cookie，再用 `-b` 请求 `/api/stats/devices`。

## CI/CD

- `.github/workflows/docker-publish.yml`：向 `master` 分支 push 时自动构建并推送 `mibusix/device-management:latest` 到 Docker Hub。
- 需要仓库 Secrets：`DOCKER_USERNAME`、`DOCKER_TOKEN`。

## 常见坑

- 直接运行 `uvicorn app.main:app` 而不设 `SECRET_KEY` 会立刻报错。
- `docker-compose.yml` 不再提供默认 `SECRET_KEY`，未设置 `.env` 时容器会因缺少密钥启动失败。
- API 鉴权基于 Cookie，不是 Authorization header；用 curl 测试记得带 `-c/-b`。
- 登录接口有速率限制（每 IP 5 次失败/5 分钟），连续失败会返回 429。
- `data/` 和 `.env` 已被 `.gitignore` 忽略，不要把生产数据库或密钥提交。
