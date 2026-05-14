"""
utils/formatter.py - 金额和数值格式化工具
"""


def format_amount(amount: float) -> str:
    """
    将金额格式化为人民币显示字符串。

    Examples:
        >>> format_amount(12345.6)
        '¥12,345.60'
        >>> format_amount(-500)
        '-¥500.00'
    """
    sign = "-" if amount < 0 else ""
    return f"{sign}¥{abs(amount):,.2f}"


def format_amount_short(amount: float) -> str:
    """短格式金额（不带千位分隔符）"""
    sign = "-" if amount < 0 else ""
    return f"{sign}¥{abs(amount):.2f}"
