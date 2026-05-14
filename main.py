"""
FinanceApp - 个人财务可视化桌面应用

程序入口。支持以下模式：
- 默认 / --gui：启动 PyQt6 图形界面
- --init-db：仅初始化数据库（建表 + 预置分类）
"""

import argparse
import sys
import io

# 修复 Windows 终端 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from core.database import init_db, close_connection, get_connection


def print_summary() -> None:
    """打印数据库概览信息。"""
    conn = get_connection()

    # 分类统计
    categories = conn.execute("SELECT type, COUNT(*) as cnt FROM categories GROUP BY type").fetchall()
    print("\n📊 预置分类统计：")
    for row in categories:
        type_label = "支出" if row["type"] == "expense" else "收入"
        print(f"   {type_label}: {row['cnt']} 个")

    # 显示所有分类
    print("\n📋 分类列表：")
    all_cats = conn.execute(
        "SELECT icon, name, type FROM categories ORDER BY type, id"
    ).fetchall()
    for cat in all_cats:
        type_label = "支出" if cat["type"] == "expense" else "收入"
        print(f"   {cat['icon']} {cat['name']} ({type_label})")

    # 记录统计
    tx_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    print(f"\n📝 交易记录: {tx_count} 条")
    print("\n✅ 初始化完成，项目就绪！\n")


def run_gui() -> None:
    """启动 PyQt6 图形界面。"""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from ui.main_window import MainWindow

    # 高 DPI 适配
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("FinanceApp")
    app.setApplicationDisplayName("个人财务管理")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def main() -> None:
    parser = argparse.ArgumentParser(description="个人财务可视化桌面应用")
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="仅初始化数据库（建表 + 预置分类）",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        default=True,
        help="启动图形界面（默认行为）",
    )
    args = parser.parse_args()

    if args.init_db:
        init_db()
        print_summary()
        close_connection()
    else:
        run_gui()


if __name__ == "__main__":
    main()
