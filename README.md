# FinanceApp - 个人财务可视化桌面应用

一款纯本地运行的个人财务管理工具，帮助用户记录收支、自动统计、直观可视化。

## 技术栈

| 层次 | 技术 |
|------|------|
| GUI 框架 | PyQt6 |
| 图表渲染 | pyecharts + QtWebEngine |
| 数据存储 | SQLite |
| 账单解析 | pandas + openpyxl |
| 打包分发 | PyInstaller |
| 开发语言 | Python 3.11+ |

## 功能

- ✅ 手动录入收入/支出记录
- ✅ 分类标签管理（内置 13 个默认分类）
- ✅ 周/月统计自动汇总
- ✅ 趋势折线图 + 分类饼图 + 对比柱状图
- ✅ 银行账单批量导入（CSV/Excel）
- 🔲 预算管理与超支预警（v1.1）
- 🔲 数据导出（v1.1）

## 项目结构

```
FinanceApp/
├── main.py              # 程序入口
├── core/                # 核心业务逻辑层
│   ├── database.py      # 数据库连接与初始化
│   ├── transaction.py   # 收支 CRUD
│   ├── category.py      # 分类 CRUD
│   ├── statistics.py    # 统计聚合
│   └── importer.py      # 账单导入
├── ui/                  # 界面层（PyQt6）
├── charts/              # 图表生成层
└── utils/               # 工具模块
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python main.py --init-db

# 启动应用（Phase 1 后可用）
python main.py
```

## 开发里程碑

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | 项目结构、数据库初始化、预置分类 | ✅ 进行中 |
| Phase 1 | 基础 CRUD：新增/编辑/删除收支记录 | 🔲 待开始 |
| Phase 2 | 统计模块：周报/月报聚合查询 | 🔲 待开始 |
| Phase 3 | 仪表盘：三种图表 + 概览卡片 | 🔲 待开始 |
| Phase 4 | 银行账单导入 | 🔲 待开始 |
| Phase 5 | UI 美化 + 分类管理页 | 🔲 待开始 |
| Phase 6 | 打包 + 测试 + 修 bug | 🔲 待开始 |

## License

MIT
