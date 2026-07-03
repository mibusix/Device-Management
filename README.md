# 设备管理系统

小团队设备管理 Web 应用，支持设备登记、位置管理、设备类型自定义字段、能耗计算。

## 功能

- **仪表盘** — 设备总数/状态统计/类型分布/区域分布/能耗概览
- **设备管理** — 添加/编辑/删除设备，按类型/状态/区域/关键词筛选
- **位置管理** — 大区域 → 小区域层级结构，按位置查看设备
- **设备类型** — 动态管理类型、子类型、自定义字段模板
- **能耗计算** — 录入功率和运行时长，自动计算 kWh
- **多联机能耗** — 多联机设备独立能耗管理
- **响应式** — PC 侧边栏导航 + 手机底部 Tab 栏

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
│   ├── database.py          # SQLite 连接
│   ├── models.py            # 数据模型
│   ├── routers/
│   │   ├── pages.py         # 页面路由
│   │   ├── devices.py       # 设备 API
│   │   ├── locations.py     # 位置 API
│   │   ├── types_api.py     # 类型管理 API
│   │   └── energy.py        # 能耗 API
│   └── templates/           # 页面模板
├── requirements.txt
└── README.md
```

## 使用流程

1. **位置管理** → 添加大区域（A区/B区），再添加小区域（机房/夹层）
2. **类型管理** → 添加设备类型，设置自定义字段
3. **设备管理** → 添加设备，选择类型和位置
4. **能耗计算** → 选择设备录入功率和时长

## 截图

（暂无）
