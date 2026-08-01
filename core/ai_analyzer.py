"""
core/ai_analyzer.py - AI 智能省钱建议引擎

调用 OpenAI 兼容接口（支持硅基流动/DeepSeek/OpenAI 等），基于用户历史支出数据生成省钱建议。
仅发送聚合统计数据，不发送原始交易明细，保护隐私。
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import httpx

from core.statistics import get_summary, get_expense_by_category
from core.database import get_connection

# ─── 配置 ────────────────────────────────────────────────────────────────

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "ai_config.json"

# 预置服务商配置（均为 OpenAI 兼容接口）
PROVIDERS = {
    "siliconflow": {
        "name": "硅基流动",
        "api_url": "https://api.siliconflow.cn/v1/chat/completions",
        "models": [
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-V2.5",
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
        ],
        "default_model": "deepseek-ai/DeepSeek-V3",
    },
    "deepseek": {
        "name": "DeepSeek 官方",
        "api_url": "https://api.deepseek.com/chat/completions",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
    },
    "openai": {
        "name": "OpenAI",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "default_model": "gpt-4o-mini",
    },
}

DEFAULT_PROVIDER = "siliconflow"
REQUEST_TIMEOUT = 60  # 秒（部分大模型响应较慢，放宽到 60s）

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


# ─── 配置管理 ─────────────────────────────────────────────────────────────

def _load_config() -> dict:
    """读取完整配置（向后兼容旧版只存 api_key 的格式）。"""
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            return data
        except Exception:
            return {}
    return {}


def _save_config(config: dict) -> None:
    """保存完整配置到本地文件。"""
    _CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_api_key() -> Optional[str]:
    """从本地配置文件加载 API Key。"""
    return _load_config().get("api_key", "").strip() or None


def save_api_key(api_key: str) -> None:
    """保存 API Key（保留其他已有配置字段）。"""
    cfg = _load_config()
    cfg["api_key"] = api_key.strip()
    _save_config(cfg)


def load_provider() -> str:
    """读取当前服务商 id，默认 siliconflow。"""
    return _load_config().get("provider", DEFAULT_PROVIDER)


def save_provider(provider: str) -> None:
    """保存服务商 id，并同步更新默认模型。"""
    cfg = _load_config()
    cfg["provider"] = provider
    # 切换服务商时自动重置为该服务商的默认模型
    p = PROVIDERS.get(provider)
    if p:
        cfg["model"] = p["default_model"]
    _save_config(cfg)


def load_model() -> str:
    """读取当前模型名，若未设置则取服务商默认模型。"""
    cfg = _load_config()
    m = cfg.get("model", "").strip()
    if m:
        return m
    p = PROVIDERS.get(cfg.get("provider", DEFAULT_PROVIDER))
    return p["default_model"] if p else "deepseek-ai/DeepSeek-V3"


def save_model(model: str) -> None:
    """保存模型名。"""
    cfg = _load_config()
    cfg["model"] = model
    _save_config(cfg)


def get_api_url() -> str:
    """根据当前服务商返回 API URL。"""
    cfg = _load_config()
    # 允许用户自定义 URL（覆盖服务商默认）
    custom = cfg.get("api_url", "").strip()
    if custom:
        return custom
    p = PROVIDERS.get(cfg.get("provider", DEFAULT_PROVIDER))
    return p["api_url"] if p else PROVIDERS[DEFAULT_PROVIDER]["api_url"]


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

def analyze_savings(api_key: str, data: dict) -> str:
    """
    调用 OpenAI 兼容接口生成省钱建议（支持硅基流动/DeepSeek/OpenAI 等）。

    Args:
        api_key: API Key
        data: 预聚合的消费数据（来自 gather_savings_data，应在主线程调用以避免 SQLite 跨线程问题）

    Returns:
        AI 生成的 Markdown 格式建议文本

    Raises:
        ValueError: API Key 为空
        httpx.HTTPStatusError: API 请求失败
        Exception: 其他错误
    """
    if not api_key.strip():
        raise ValueError("API Key 不能为空")

    months = data["months"]

    if data["tx_count"] == 0:
        return "当前时段内暂无交易数据，无法进行分析。请先记录一些收支后再试。"

    # 构建 Prompt
    user_prompt = _build_user_prompt(
        months=months,
        total_expense=data["total_expense"],
        total_income=data["total_income"],
        category_breakdown=data["category_breakdown"],
        monthly_avg=data["monthly_avg_expense"],
        daily_avg=data["daily_avg_expense"],
    )

    # 读取当前服务商配置
    api_url = get_api_url()
    model = load_model()
    provider_id = load_provider()
    provider_name = PROVIDERS.get(provider_id, {}).get("name", provider_id)

    # 调用 API（OpenAI 兼容格式），含自动重试（429/5xx 触发指数退避）
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    max_retries = 3
    last_error: str = ""
    for attempt in range(1, max_retries + 1):
        try:
            response = httpx.post(api_url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        except httpx.HTTPError as e:
            # 网络层异常（连接超时、DNS 失败等）
            last_error = f"网络异常：{e}"
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"[{provider_name}] {last_error}") from e

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return content

        # 解析错误体
        try:
            err_body = response.json()
            err_msg = err_body.get("error", {}).get("message", "") or str(err_body)
        except Exception:
            err_msg = response.text[:200]
        last_error = f"HTTP {response.status_code}：{err_msg}"

        # 429 / 5xx 自动重试
        if response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
            wait_sec = 2 ** attempt  # 2s, 4s, 8s
            time.sleep(wait_sec)
            continue

        # 其他错误直接抛出（401/403/400 等）
        # 429 重试完仍失败时附带重试次数提示
        if response.status_code == 429:
            raise RuntimeError(
                f"[{provider_name}] 服务繁忙，请稍后重试（已重试 {attempt} 次）。\n"
                f"💡 建议：① 等待 1-2 分钟后再试 ② 切换到较小的模型\n"
                f"错误详情：{err_msg}"
            )
        raise RuntimeError(f"[{provider_name}] API 请求失败：{last_error}")

    # 理论上不会到这里
    raise RuntimeError(f"[{provider_name}] API 请求失败：{last_error}")
