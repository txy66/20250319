"""
utils/lunar_helper.py - 农历转换 + 节假日/节气标注

基于 zhdate 库实现公历→农历转换，并提供简短的农历显示文本
（如"初一"→显示月份名"正月"，其他日期显示"初二""廿三"等），
同时支持固定节假日和常见节气的日期查找。
"""

from __future__ import annotations

from datetime import date, datetime

from zhdate import ZhDate

# ─── 农历日期数字 → 中文显示 ────────────────────────────────────────────────

_DAY_CN: dict[int, str] = {
    1: "初一", 2: "初二", 3: "初三", 4: "初四", 5: "初五",
    6: "初六", 7: "初七", 8: "初八", 9: "初九", 10: "初十",
    11: "十一", 12: "十二", 13: "十三", 14: "十四", 15: "十五",
    16: "十六", 17: "十七", 18: "十八", 19: "十九", 20: "二十",
    21: "廿一", 22: "廿二", 23: "廿三", 24: "廿四", 25: "廿五",
    26: "廿六", 27: "廿七", 28: "廿八", 29: "廿九", 30: "三十",
}

_MONTH_CN: dict[int, str] = {
    1: "正月", 2: "二月", 3: "三月", 4: "四月", 5: "五月", 6: "六月",
    7: "七月", 8: "八月", 9: "九月", 10: "十月", 11: "冬月", 12: "腊月",
}

# ─── 公历固定节假日（月-日 → 名称）─────────────────────────────────────────

_SOLAR_HOLIDAYS: dict[str, str] = {
    "01-01": "元旦",
    "02-14": "情人节",
    "03-08": "妇女节",
    "03-12": "植树节",
    "04-01": "愚人节",
    "05-01": "劳动节",
    "05-04": "青年节",
    "06-01": "儿童节",
    "07-01": "建党节",
    "08-01": "建军节",
    "09-10": "教师节",
    "10-01": "国庆节",
    "10-02": "国庆",
    "10-03": "国庆",
    "12-24": "平安夜",
    "12-25": "圣诞节",
}

# ─── 常见二十四节气近似日期（公历，每年有 ±1 天误差，够用）─────────────────

_SOLAR_TERMS: dict[str, str] = {
    "01-05": "小寒", "01-20": "大寒",
    "02-04": "立春", "02-19": "雨水",
    "03-05": "惊蛰", "03-20": "春分",
    "04-04": "清明", "04-20": "谷雨",
    "05-05": "立夏", "05-21": "小满",
    "06-05": "芒种", "06-21": "夏至",
    "07-07": "小暑", "07-22": "大暑",
    "08-07": "立秋", "08-23": "处暑",
    "09-07": "白露", "09-23": "秋分",
    "10-08": "寒露", "10-23": "霜降",
    "11-07": "立冬", "11-22": "小雪",
    "12-07": "大雪", "12-22": "冬至",
}


def get_lunar_text(d: date) -> str:
    """
    获取某一天的日历格子底部辅助文字。

    优先级：节假日 > 节气 > 农历初一日（显示月份名）> 农历日期

    Args:
        d: 公历日期

    Returns:
        简短中文字符串，如"端午""夏至""正月""廿三"
    """
    mmdd = f"{d.month:02d}-{d.day:02d}"

    # 1. 公历节假日
    if mmdd in _SOLAR_HOLIDAYS:
        return _SOLAR_HOLIDAYS[mmdd]

    # 2. 节气
    if mmdd in _SOLAR_TERMS:
        return _SOLAR_TERMS[mmdd]

    # 3. 农历
    try:
        lunar = ZhDate.from_datetime(datetime(d.year, d.month, d.day))
        lunar_day = lunar.lunar_day
        lunar_month = lunar.lunar_month

        # 农历初一显示月份名
        if lunar_day == 1:
            return _MONTH_CN.get(lunar_month, f"{lunar_month}月")

        return _DAY_CN.get(lunar_day, str(lunar_day))
    except Exception:
        return ""


def get_lunar_info(d: date) -> dict:
    """
    获取某一天的完整农历信息。

    Returns:
        {"lunar_month": int, "lunar_day": int, "text": str}
    """
    try:
        lunar = ZhDate.from_datetime(datetime(d.year, d.month, d.day))
        return {
            "lunar_month": lunar.lunar_month,
            "lunar_day": lunar.lunar_day,
            "text": get_lunar_text(d),
        }
    except Exception:
        return {"lunar_month": 0, "lunar_day": 0, "text": ""}
