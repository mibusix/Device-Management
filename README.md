# 设备管理系统

小团队设备管理 Web 应用，支持分组设备管理、自定义字段、位置层级、辅助计算工具。

## 功能

- **仪表盘** — 设备总数/状态统计/类型分布/区域分布/分组设备统计
- **设备统计** — 统一/跨类型设备查询与筛选
- **设备管理** — 按分组（多联机/控制保护器/压缩机/水泵）管理设备，每组独立字段模板
- **位置管理** — 大区域 → 小区域层级结构
- **小工具** — 能耗估算（选设备+开停机时间）、压力单位换算、欧姆定律计算

## 技术栈

- Python 3 / FastAPI / SQLAlchemy / SQLite
- Jinja2 / Tailwind CSS (CDN) / Alpine.js

## 快速开始

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器打开 `http://localhost:8000`。

## 项目结构

```
├── app/
│   ├── main.py              # 入口
│   ├── config.py            # 配置
│   ├── database.py          # SQLite 连接 + 预设分组种子
│   ├── models.py            # 数据模型
│   ├── routers/
│   │   ├── pages.py         # 页面路由
│   │   ├── devices.py       # 系统设备 API
│   │   ├── locations.py     # 位置 API
│   │   ├── groups.py        # 分组管理 API
│   │   └── stats.py         # 统一设备统计 API
│   └── templates/
│       ├── base.html        # 布局（响应式导航）
│       ├── dashboard.html
│       ├── devices/
│       ├── groups/
│       ├── locations/
│       └── tools/           # 小工具（能耗/压力/电学计算）
├── data/
│   └── devices.db           # SQLite 数据库（自动创建）
├── requirements.txt
└── README.md
```

## 使用流程

1. **位置管理** → 添加大区域（A区/B区），再添加小区域（机房/夹层）
2. **设备管理** → 分组会预设 4 类（多联机/控制保护器/压缩机/水泵），进入分组 → 管理字段模板 → 添加设备
3. **设备统计** → 统一查看所有系统设备
4. **小工具** → 能耗估算、压力换算、电阻/电流/电压计算

## 截图

（暂无）

---

## 部署教程

本节提供完整的部署指南，帮助您将设备管理系统部署到生产环境。

### 环境要求

- **Python**：3.8 或更高版本
- **操作系统**：Linux、macOS 或 Windows
- **依赖管理**：pip（Python 包管理器）
- **网络**：能够访问互联网以下载依赖包

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <项目仓库地址>
   cd 设备管理
   ```

2. **创建虚拟环境（推荐）**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # 或
   venv\Scripts\activate  # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

### 配置说明

项目通过环境变量进行配置，无需修改代码。主要配置项包括数据库连接、安全密钥和访问认证。

### 启动方式

**开发环境启动：**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**生产环境启动：**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

启动后，浏览器访问 `http://localhost:8000` 即可使用系统。

### 环境变量说明

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `AUTH_USER` | 否 | 无 | 基本认证用户名。设置后启用 HTTP 基本认证，保护系统访问。 |
| `AUTH_PASSWORD` | 否 | 无 | 基本认证密码。需与 `AUTH_USER` 同时设置才生效。 |
| `SECRET_KEY` | 否 | `change-this-to-a-random-secret-key` | 应用密钥，用于安全相关功能。生产环境必须修改为随机强密码。 |
| `DATABASE_URL` | 否 | `sqlite:///data/devices.db` | 数据库连接字符串。默认使用 SQLite，可改为 PostgreSQL 等。 |

**示例配置（.env 文件）：**
```env
AUTH_USER=admin
AUTH_PASSWORD=your_secure_password
SECRET_KEY=your_random_secret_key_here
DATABASE_URL=sqlite:///data/devices.db
```

### 验证部署

1. **服务状态检查**
   ```bash
   curl http://localhost:8000
   ```
   返回 HTML 内容表示服务正常运行。

2. **API 端点测试**
   ```bash
   # 测试统计 API
   curl http://localhost:8000/api/stats/devices
   
   # 测试设备列表 API
   curl http://localhost:8000/api/devices/
   ```

3. **认证测试**（如果启用了认证）
   ```bash
   curl -u admin:password http://localhost:8000
   ```

### 常见问题

**Q1: 启动时报错 "Address already in use"**
- 端口 8000 被占用，修改端口号：
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8080
  ```

**Q2: 数据库文件在哪里？**
- 默认数据库文件位于 `data/devices.db`，首次启动自动创建。

**Q3: 如何重置数据库？**
- 删除 `data/devices.db` 文件，重启服务即可自动重建。

**Q4: 如何启用 HTTPS？**
- 推荐使用 Nginx 或 Caddy 作为反向代理配置 HTTPS，而不是直接在应用中配置。

**Q5: 如何修改默认端口？**
- 启动时指定 `--port` 参数：
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 9000
  ```

**Q6: 忘记认证密码怎么办？**
- 重新设置 `AUTH_USER` 和 `AUTH_PASSWORD` 环境变量，重启服务即可。

**Q7: 如何备份数据？**
- 直接备份 `data/devices.db` 文件即可。SQLite 数据库是单文件，便于备份和迁移。
