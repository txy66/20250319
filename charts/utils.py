"""
charts/utils.py - 图表工具

核心：把 pyecharts 生成的 HTML 中对 CDN 的依赖（echarts.min.js）
替换为本地 inline 脚本，避免：
1. QtWebEngine 离线/受限网络环境下的 SSL 握手失败
2. 联网下载大文件导致图表加载慢

echarts.min.js 位于 assets/echarts/echarts.min.js（v5.4.3）。
启动时一次性读入缓存，~1 MB，对渲染性能无影响。
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path


# ── 本地 echarts 路径 ──────────────────────────────────────────────────────

_ASSETS_DIR: Path = Path(__file__).resolve().parent.parent / "assets" / "echarts"
_ECHARTS_PATH: Path = _ASSETS_DIR / "echarts.min.js"


# ── 一次性读入缓存 ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_echarts_js() -> str:
    """
    读取本地 echarts.min.js 内容。
    首次调用读文件，后续调用直接返回缓存。
    若文件缺失，抛出 FileNotFoundError。
    """
    if not _ECHARTS_PATH.exists():
        raise FileNotFoundError(
            f"echarts.min.js 不存在：{_ECHARTS_PATH}\n"
            "请从 https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js 下载，"
            "或运行：`curl -sSL -o assets/echarts/echarts.min.js <URL>`"
        )
    return _ECHARTS_PATH.read_text(encoding="utf-8")


# ── HTML 注入 ──────────────────────────────────────────────────────────────

# 匹配 pyecharts / 各类 echarts CDN 引用
# 容忍 type="text/javascript"、多余空格、协议无关 URL（//cdn...）
_ECHARTS_SCRIPT_PATTERN = re.compile(
    r'<script\b[^>]*?src\s*=\s*["\'][^"\']*echarts[^"\']*\.js["\'][^>]*></script>',
    re.IGNORECASE,
)


def inline_echarts(html: str) -> str:
    """
    把 pyecharts HTML 中的外部 echarts CDN 引用替换为本地 inline 脚本。

    Args:
        html: pyecharts `chart.render_embed()` 输出的 HTML

    Returns:
        注入本地 echarts.min.js 后的 HTML
    """
    echarts_js = get_echarts_js()
    replacement = f"<script>{echarts_js}</script>"

    # 用 lambda 避免 re.sub 对 replacement 中的反斜杠做模板解释
    new_html, n = _ECHARTS_SCRIPT_PATTERN.subn(lambda _m: replacement, html, count=1)
    if n == 0:
        # 没匹配到外部脚本 — 说明 pyecharts 输出格式变了
        # 退化为直接插入到 </head> 之前
        new_html = html.replace("</head>", f"{replacement}</head>", 1) if "</head>" in html else replacement + html
    return new_html


def inject_body_style(html: str, bg: str = "#ffffff") -> str:
    """
    向 pyecharts 完整 HTML 中注入 body 背景样式，保证图表无白边/灰边。
    render_embed() 返回完整 HTML，不能再用 _wrap_html 双重包装。
    """
    body_style = f"body {{ margin: 0; padding: 0; background: {bg}; }}"
    if "<head>" in html:
        return html.replace("<head>", f"<head>\n    <style>{body_style}</style>", 1)
    if "<head " in html:
        return html.replace("<head ", f"<head>\n    <style>{body_style}</style><head ", 1)
    return html


def prepare_chart_html(html: str, bg: str = "#ffffff") -> str:
    """
    一站式预处理：inline echarts + 注入 body 样式。
    """
    html = inline_echarts(html)
    html = inject_body_style(html, bg=bg)
    return html