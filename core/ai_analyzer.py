"""
core/ai_analyzer.py - AI 智能省钱建议引擎

调用 DeepSeek API，基于用户历史支出数据生成省钱建议。
仅发送聚合统计数据，不发送原始交易明细，保护隐私。
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import httpx

from core.statistics import get_summary, get_expense_by_category
from core.database import get_connection

# ─── 配置 ────────────────────────────────────────────────────────────────

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "ai_config.json"

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
REQUEST_TIMEOUT = 30  # 秒

SYSTEM_PROMPT = """你是一位专业的个人理财分析师，擅长从消费数据中发现问题并给出实用建议。

分析规则：
1. 重点关注支出结构是否合理，识别高消费分类和异常支出
2. 给出具体可执行的省钱建议，包含预计可省金额
3. 如果某分类支出明显偏高，分析是否合理并给出替代方案
4. 语气友好专业，建议要具体可落地

输出格式（使用 Markdown）：
## 📊 支出结构概览
简要总结当期支出概况

## ⚠️ 异常支出识别
列出可能不合理的支出

## 💡 分类省钱建议
按分类逐个给出建议，每条包含预计可省金额

## 📝 总结与行动建议
3-5条优先级排序的行动建议"""


def _build_user_prompt(
    months: int,
    total_expense: float,
    total_income: float,
    category_breakdown: list[dict],
    monthly_avg: float,
    daily_avg: float,
) -> str:
    """构建用户消息 Prompt。"""
    # 分类支出详情
    cat_lines = []
    for cat in category_breakdown[:15]:  # 最多传 15 个分类
        cat_lines.append(
            f"  - {cat['icon']} {cat['category']}：¥{cat['amount']:.2f}（占比 {cat['percent']:.1f}%）"
        )

    cat_text = "\n".join(cat_lines) if cat_lines else "  无支出数据"

    return f"""以下是用户最近 {months} 个月的消费数据（仅聚合统计，不含具体交易明细）：

**时间范围**：最近 {months} 个月
**总收入**：¥{total_income:.2f}
**总支出**：¥{total_expense:.2f}
**月均支出**：¥{monthly_avg:.2f}
**日均支出**：¥{daily_avg:.2f}

**各分类支出明细**：
{cat_text}

请分析以上数据，给出具体的省钱建议。"""


# ─── API Key 管理 ─────────────────────────────────────────────────────────

def load_api_key() -> Optional[str]:
    """从本地配置文件加载 API Key。"""
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("api_key", "").strip() or None
        except Exception:
            return None
    return None


def save_api_key(api_key: str) -> None:
    """保存 API Key 到本地配置文件。"""
    _CONFIG_PATH.write_text(
        json.dumps({"api_key": api_key.strip()}, ensure_ascii=False),
        encoding="utf-8",
    )


# ─── 数据聚合 ─────────────────────────────────────────────────────────────

def gather_savings_data(months: int = 3) -> dict:
    """
    聚合指定月数的支出数据，供 AI 分析使用。

    Returns:
        包含收支汇总和分类明细的字典
    """
    today = date.today()
    start = today - timedelta(days=months * 30)
    start_str = start.isoformat()
    end_str = today.isoformat()

    # 总收支
    summary = get_summary(start_date=start_str, end_date=end_str)

    # 分类支出
    category_breakdown = get_expense_by_category(start_date=start_str, end_date=end_str)

    # 计算月均和日均
    days = max((today - start).days, 1)
    monthly_avg = summary["expense"] / max(months, 1)
    daily_avg = summary["expense"] / days

    return {
        "months": months,
        "total_expense": summary["expense"],
        "total_income": summary["income"],
        "balance": summary["balance"],
        "tx_count": summary["count"],
        "category_breakdown": category_breakdown,
        "monthly_avg_expense": round(monthly_avg, 2),
        "daily_avg_expense": round(daily_avg, 2),
    }


# ─── AI 分析调用 ─────────────────────────────────────────────────────────

def analyze_savings(api_key: str, months: int = 3) -> str:
    """
    调用 DeepSeek API 生成省钱建议。

    Args:
        api_key: DeepSeek API Key
        months: 分析最近几个月的数据

    Returns:
        AI 生成的 Markdown 格式建议文本

    Raises:
        ValueError: API Key 为空
        httpx.HTTPStatusError: API 请求失败
        Exception: 其他错误
    """
    if not api_key.strip():
        raise ValueError("API Key 不能为空")

    # 聚合数据
    data = gather_savings_data(months)

    if data["tx_count"] == 0:
        return "当前时段内暂无交易数据，无法进行分析。请先记录一些收支后再试。"

    # 构建 Prompt
    user_prompt = _build_user_prompt(
        months=data["months"],
        total_expense=data["total_expense"],
        total_income=data["total_income"],
        category_breakdown=data["category_breakdown"],
        monthly_avg=data["monthly_avg_expense"],
        daily_avg=data["daily_avg_expense"],
    )

    # 调用 API
    response = httpx.post(
        DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    result = response.json()
    content = result["choices"][0]["message"]["content"]
    return content
