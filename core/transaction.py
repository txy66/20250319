"""
core/transaction.py - 收支记录 CRUD 操作

提供交易的增、删、改、查功能，以及列表查询与筛选。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, date
from typing import Optional

from core.database import get_connection


# ---------------------------------------------------------------------------
# 创建
# ---------------------------------------------------------------------------

def create_transaction(
    *,
    type: str,
    amount: float,
    category_id: int,
    date: str,
    note: str = "",
    source: str = "manual",
) -> int:
    """
    新增一条交易记录。

    Args:
        type: "income" 或 "expense"
        amount: 金额（必须 > 0）
        category_id: 分类 ID
        date: 交易日期（YYYY-MM-DD）
        note: 备注
        source: 来源（manual / import）

    Returns:
        新记录的 ID
    """
    conn = get_connection()
    now = datetime.now().isoformat(timespec="seconds")
    cursor = conn.execute(
        """INSERT INTO transactions (type, amount, category_id, date, note, source, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (type, amount, category_id, date, note, source, now),
    )
    conn.commit()
    return cursor.lastrowid


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------

def get_transaction(tx_id: int) -> Optional[dict]:
    """根据 ID 获取一条交易记录（含分类信息）。"""
    conn = get_connection()
    row = conn.execute(
        """SELECT t.*, c.name AS category_name, c.icon AS category_icon
           FROM transactions t
           LEFT JOIN categories c ON t.category_id = c.id
           WHERE t.id = ?""",
        (tx_id,),
    ).fetchone()
    return dict(row) if row else None


def list_transactions(
    *,
    type: Optional[str] = None,
    category_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """
    查询交易记录列表（支持多条件筛选）。

    Args:
        type: 按收支类型筛选
        category_id: 按分类筛选
        start_date / end_date: 按日期范围筛选（YYYY-MM-DD）
        keyword: 按备注关键词模糊搜索
        limit: 返回条数上限
        offset: 偏移量

    Returns:
        交易记录字典列表（按日期降序）
    """
    conn = get_connection()
    clauses: list[str] = []
    params: list = []

    if type:
        clauses.append("t.type = ?")
        params.append(type)
    if category_id is not None:
        clauses.append("t.category_id = ?")
        params.append(category_id)
    if start_date:
        clauses.append("t.date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("t.date <= ?")
        params.append(end_date)
    if keyword:
        clauses.append("t.note LIKE ?")
        params.append(f"%{keyword}%")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    rows = conn.execute(
        f"""SELECT t.*, c.name AS category_name, c.icon AS category_icon
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            {where}
            ORDER BY t.date DESC, t.id DESC
            LIMIT ? OFFSET ?""",
        (*params, limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


def count_transactions(
    *,
    type: Optional[str] = None,
    category_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keyword: Optional[str] = None,
) -> int:
    """获取满足条件的交易记录总数。"""
    conn = get_connection()
    clauses: list[str] = []
    params: list = []

    if type:
        clauses.append("type = ?")
        params.append(type)
    if category_id is not None:
        clauses.append("category_id = ?")
        params.append(category_id)
    if start_date:
        clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("date <= ?")
        params.append(end_date)
    if keyword:
        clauses.append("note LIKE ?")
        params.append(f"%{keyword}%")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    row = conn.execute(f"SELECT COUNT(*) FROM transactions {where}", params).fetchone()
    return row[0]


# ---------------------------------------------------------------------------
# 更新
# ---------------------------------------------------------------------------

def update_transaction(
    tx_id: int,
    *,
    type: Optional[str] = None,
    amount: Optional[float] = None,
    category_id: Optional[int] = None,
    date: Optional[str] = None,
    note: Optional[str] = None,
) -> bool:
    """
    更新一条交易记录（只更新传入的非 None 字段）。

    Returns:
        是否有行被更新
    """
    fields: list[str] = []
    params: list = []

    if type is not None:
        fields.append("type = ?")
        params.append(type)
    if amount is not None:
        fields.append("amount = ?")
        params.append(amount)
    if category_id is not None:
        fields.append("category_id = ?")
        params.append(category_id)
    if date is not None:
        fields.append("date = ?")
        params.append(date)
    if note is not None:
        fields.append("note = ?")
        params.append(note)

    if not fields:
        return False

    params.append(tx_id)
    conn = get_connection()
    cursor = conn.execute(
        f"UPDATE transactions SET {', '.join(fields)} WHERE id = ?",
        params,
    )
    conn.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# 删除
# ---------------------------------------------------------------------------

def delete_transaction(tx_id: int) -> bool:
    """
    根据ID删除一条交易记录。

    Returns:
        是否有行被删除
    """
    conn = get_connection()
    cursor = conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    return cursor.rowcount > 0
