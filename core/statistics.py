"""
core/statistics.py - 统计聚合查询

提供周报、月报统计功能，计算指定时段内的收入、支出和净利润。
"""

from __future__ import annotations

from typing import Optional
from datetime import date, timedelta

from core.database import get_connection
from utils.date_helper import current_week_range, current_month_range, last_n_months_range


def get_summary(
    *,
    start_date: str,
    end_date: str,
    type_filter: Optional[str] = None,
) -> dict:
    """
    获取指定日期范围内的收支汇总。

    Args:
        start_date: 起始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        type_filter: 可选，"income" 或 "expense"

    Returns:
        {"income": float, "expense": float, "balance": float, "count": int}
    """
    conn = get_connection()
    clauses = ["date BETWEEN ? AND ?"]
    params: list = [start_date, end_date]

    if type_filter:
        clauses.append("type = ?")
        params.append(type_filter)

    where = "WHERE " + " AND ".join(clauses)

    # 总收入
    income_row = conn.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE date BETWEEN ? AND ? AND type = 'income'",
        [start_date, end_date],
    ).fetchone()
    income = round(income_row[0], 2)

    # 总支出
    expense_row = conn.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE date BETWEEN ? AND ? AND type = 'expense'",
        [start_date, end_date],
    ).fetchone()
    expense = round(expense_row[0], 2)

    # 记录数
    count_row = conn.execute(
        f"SELECT COUNT(*) FROM transactions {where}",
        params,
    ).fetchone()

    return {
        "income": income,
        "expense": expense,
        "balance": round(income - expense, 2),
        "count": count_row[0],
    }


def get_weekly_stats() -> list[dict]:
    """
    获取最近 12 周的周报统计。

    Returns:
        [{"week": "2026-W03", "start": "2026-01-13", "end": "2026-01-19",
          "income": float, "expense": float, "balance": float}, ...]
    """
    conn = get_connection()
    results = []

    # 获取最近12周的周一日期
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    for i in range(11, -1, -1):
        week_monday = monday - timedelta(weeks=i)
        week_sunday = week_monday + timedelta(days=6)
        start = week_monday.isoformat()
        end = week_sunday.isoformat()

        summary = get_summary(start_date=start, end_date=end)

        # 周标签，如 "05/12 - 05/18"
        week_label = f"{week_monday.month:02d}/{week_monday.day:02d}-{week_sunday.month:02d}/{week_sunday.day:02d}"

        results.append({
            "week": week_label,
            "start": start,
            "end": end,
            **summary,
        })

    return results


def get_monthly_stats(months: int = 12) -> list[dict]:
    """
    获取最近 N 个月的月报统计。

    Args:
        months: 回溯月数，默认 12

    Returns:
        [{"month": "2026-05", "income": float, "expense": float, "balance": float}, ...]
    """
    conn = get_connection()
    results = []

    today = date.today()
    for i in range(months - 1, -1, -1):
        # 计算月份范围
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        start = first_day.isoformat()
        end = last_day.isoformat()
        month_str = f"{year}-{month:02d}"

        summary = get_summary(start_date=start, end_date=end)

        results.append({
            "month": month_str,
            "start": start,
            "end": end,
            **summary,
        })

    return results


def get_expense_by_category(
    *,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """
    获取指定时段内各支出分类的金额汇总。

    Returns:
        [{"category": "餐饮", "icon": "🍜", "amount": float, "percent": float}, ...]
    """
    conn = get_connection()

    rows = conn.execute(
        """SELECT c.name, c.icon, SUM(t.amount) as total
           FROM transactions t
           JOIN categories c ON t.category_id = c.id
           WHERE t.type = 'expense' AND t.date BETWEEN ? AND ?
           GROUP BY t.category_id
           ORDER BY total DESC""",
        (start_date, end_date),
    ).fetchall()

    total_expense = sum(r["total"] for r in rows) if rows else 0

    results = []
    for r in rows:
        percent = round(r["total"] * 100.0 / total_expense, 1) if total_expense > 0 else 0
        results.append({
            "category": r["name"],
            "icon": r["icon"],
            "amount": round(r["total"], 2),
            "percent": percent,
        })

    return results
