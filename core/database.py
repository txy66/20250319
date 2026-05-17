"""
core/database.py - 数据库连接管理、建表、预置分类种子数据

采用幂等初始化模式：重复调用不会重复插入或报错。
"""

import sqlite3
import os
from pathlib import Path

# 数据库文件路径：项目根目录下的 app.db
DB_PATH = Path(__file__).resolve().parent.parent / "app.db"

# 全局连接实例（单例模式）
_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """获取数据库连接（单例）。"""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(str(DB_PATH))
        _connection.row_factory = sqlite3.Row  # 支持字典式访问
        _connection.execute("PRAGMA journal_mode=WAL")  # 提升并发性能
        _connection.execute("PRAGMA foreign_keys=ON")   # 启用外键约束
    return _connection


def close_connection() -> None:
    """关闭数据库连接。"""
    global _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
        finally:
            _connection = None


def _create_tables(conn: sqlite3.Connection) -> None:
    """创建所有数据表（IF NOT EXISTS 保证幂等）。"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL UNIQUE,
            type        TEXT    NOT NULL CHECK(type IN ('income', 'expense')),
            icon        TEXT,
            is_default  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            type        TEXT    NOT NULL CHECK(type IN ('income', 'expense')),
            amount      REAL    NOT NULL CHECK(amount > 0),
            category_id INTEGER NOT NULL,
            date        TEXT    NOT NULL,
            note        TEXT,
            source      TEXT    DEFAULT 'manual' CHECK(source IN ('manual', 'import')),
            created_at  TEXT    NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
        CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
        CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
    """)
    conn.commit()


def _seed_categories(conn: sqlite3.Connection) -> None:
    """插入 13 个默认分类（仅当表为空时插入，保证幂等）。"""
    count = conn.execute("SELECT COUNT(*) FROM categories WHERE is_default = 1").fetchone()[0]
    if count > 0:
        return

    # 支出分类
    expense_categories = [
        ("餐饮", "expense", "🍜"),
        ("交通", "expense", "🚌"),
        ("购物", "expense", "🛍️"),
        ("娱乐", "expense", "🎮"),
        ("医疗", "expense", "🏥"),
        ("住房", "expense", "🏠"),
        ("教育", "expense", "📚"),
        ("其他支出", "expense", "📌"),
    ]

    # 收入分类
    income_categories = [
        ("工资", "income", "💼"),
        ("奖金", "income", "🎁"),
        ("投资收益", "income", "📈"),
        ("兼职", "income", "💻"),
        ("其他收入", "income", "💰"),
    ]

    conn.executemany(
        "INSERT OR IGNORE INTO categories (name, type, icon, is_default) VALUES (?, ?, ?, 1)",
        [(name, typ, icon) for name, typ, icon in expense_categories + income_categories],
    )
    conn.commit()


def init_db() -> None:
    """
    初始化数据库：建表 + 预置分类。
    可重复调用，不会报错或产生重复数据。
    """
    conn = get_connection()
    _create_tables(conn)
    _seed_categories(conn)
    print(f"[OK] 数据库初始化完成: {DB_PATH}")
