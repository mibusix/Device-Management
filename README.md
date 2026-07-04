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
