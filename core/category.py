"""
core/category.py - 分类 CRUD 操作

提供分类的查询功能，以及新增、修改、删除操作。
Phase 1 阶段主要实现查询，供 UI 层下拉列表使用。
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from core.database import get_connection


def list_categories(*, type: Optional[str] = None) -> list[dict]:
    """
    获取分类列表。

    Args:
        type: 可选，按类型筛选（"income" 或 "expense"）

    Returns:
        分类字典列表，按 id 排序
    """
    conn = get_connection()
    if type:
        rows = conn.execute(
            "SELECT * FROM categories WHERE type = ? ORDER BY id",
            (type,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM categories ORDER BY type, id"
        ).fetchall()
    return [dict(r) for r in rows]


def get_category(cat_id: int) -> Optional[dict]:
    """根据 ID 获取单个分类。"""
    conn = get_connection()
    row = conn.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
    return dict(row) if row else None


def create_category(*, name: str, type: str, icon: str = "") -> int:
    """
    新增一个自定义分类。

    Returns:
        新分类的 ID
    """
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO categories (name, type, icon, is_default) VALUES (?, ?, ?, 0)",
        (name, type, icon),
    )
    conn.commit()
    return cursor.lastrowid


def update_category(cat_id: int, *, name: Optional[str] = None, icon: Optional[str] = None) -> bool:
    """更新分类名称或图标。"""
    fields, params = [], []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if icon is not None:
        fields.append("icon = ?")
        params.append(icon)
    if not fields:
        return False
    params.append(cat_id)
    conn = get_connection()
    cursor = conn.execute(
        f"UPDATE categories SET {', '.join(fields)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_category(cat_id: int) -> bool:
    """
    删除一个自定义分类。

    注意：内置默认分类（is_default=1）不允许删除。
    如果该分类下有关联的交易记录，也会阻止删除。
    """
    conn = get_connection()

    # 检查是否为默认分类
    cat = conn.execute("SELECT is_default FROM categories WHERE id = ?", (cat_id,)).fetchone()
    if not cat:
        return False
    if cat["is_default"]:
        raise ValueError("内置默认分类不允许删除")

    # 检查是否有关联交易
    tx_count = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE category_id = ?", (cat_id,)
    ).fetchone()[0]
    if tx_count > 0:
        raise ValueError(f"该分类下有 {tx_count} 条交易记录，请先迁移后再删除")

    cursor = conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    return cursor.rowcount > 0
