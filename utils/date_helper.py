"""
utils/date_helper.py - 日期工具函数

提供周/月范围计算等常用日期操作。
"""

from datetime import date, timedelta
from typing import Tuple


def today_str() -> str:
    """返回今天的日期字符串（YYYY-MM-DD）。"""
    return date.today().isoformat()


def current_week_range() -> Tuple[str, str]:
    """
    返回当前自然周的范围（周一 ~ 周日）。

    Returns:
        (start_date, end_date) 字符串元组
    """
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def current_month_range() -> Tuple[str, str]:
    """
    返回当前自然月的范围。

    Returns:
        (start_date, end_date) 字符串元组
    """
    today = date.today()
    first_day = today.replace(day=1)
    if today.month == 12:
        last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return first_day.isoformat(), last_day.isoformat()


def last_n_months_range(n: int) -> Tuple[str, str]:
    """
    返回最近 N 个月的日期范围（从今天往前推）。

    Args:
        n: 月数

    Returns:
        (start_date, end_date) 字符串元组
    """
    today = date.today()
    # 往前推 n-1 个月的第一天
    month = today.month - (n - 1)
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    start = date(year, month, 1)
    return start.isoformat(), today.isoformat()


def month_label(month_str: str) -> str:
    """
    将 YYYY-MM 格式化为更友好的显示。

    Example:
        "2026-01" -> "2026年1月"
    """
    parts = month_str.split("-")
    if len(parts) == 2:
        return f"{parts[0]}年{int(parts[1])}月"
    return month_str
