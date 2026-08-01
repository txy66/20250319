"""
utils/theme_manager.py — 纯色主题系统 + 动态 QSS 生成器

功能：
1. 内置 6 款纯色主题（天空蓝/翡翠绿/日落橙/紫罗兰/深海蓝/玫瑰粉）
2. 统一的 theme_config.json 配置管理（主题 id + 背景启用/预设/透明度）
3. generate_stylesheet(theme_id) 生成完整 QSS，替换所有颜色为当前主题值
4. ThemeManager 单例，控制全局样式 + 配置持久化

设计原则：
- 侧边栏、卡片、表格等中性色大部分主题间保持一致，保证可读性
- 主色（primary）决定按钮、焦点指示器、选中等交互控件的颜色
- 语义色（success/error/warning）跟随主色基调微调
- 配置文件与 background_manager 共享，避免散落
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

# ── 配置文件路径（与 ai_config.json / bg_config.json 同级） ──────────────
_APP_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _APP_ROOT / "theme_config.json"


# ═════════════════════════════════════════════════════════════════════════
# 颜色工具函数（纯 Python，零依赖）
# ═════════════════════════════════════════════════════════════════════════

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken(hex_color: str, factor: float = 0.85) -> str:
    """降低亮度。factor 越小越暗。"""
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(int(r * factor), int(g * factor), int(b * factor))


def _lighten(hex_color: str, factor: float = 0.15) -> str:
    """提升亮度（向白色混合）。"""
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return _rgb_to_hex(r, g, b)


def _tint(hex_color: str, factor: float = 0.92) -> str:
    """极度提亮（接近白色），用于背景色。"""
    return _lighten(hex_color, factor)


def _rgba(hex_color: str, alpha: int) -> str:
    """生成 CSS rgba 值。"""
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _blend(hex_a: str, hex_b: str, ratio: float = 0.50) -> str:
    """混合两个颜色。ratio=0 纯 hex_a，ratio=1 纯 hex_b。"""
    ra, ga, ba = _hex_to_rgb(hex_a)
    rb, gb, bb = _hex_to_rgb(hex_b)
    return _rgb_to_hex(
        int(ra + (rb - ra) * ratio),
        int(ga + (gb - ga) * ratio),
        int(ba + (bb - ba) * ratio),
    )


# ═════════════════════════════════════════════════════════════════════════
# 主题色彩令牌
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ThemeTokens:
    """单个主题的完整色彩令牌集合（~35 个语义令牌）。"""

    # ── 标识 ──
    id: str
    name: str
    description: str

    # ── 主色系（按钮 / 焦点 / 选中） ──
    primary_500: str   # 主色
    primary_600: str   # hover 态
    primary_700: str   # pressed 态
    primary_50: str    # 超浅底色（input focus bg, selection bg）
    primary_100: str   # 浅底色
    primary_text: str  # 浅底上的文字色

    # ── 语义色 ──
    success_500: str
    success_600: str
    success_light_bg: str
    success_light_border: str
    success_lighter_bg: str
    error_500: str
    error_600: str
    warning_500: str
    income_text: str      # 收入数值文字色（通常 = success 微调）
    expense_text: str     # 支出数值文字色（通常 = error）
    balance_text: str     # 结余数值文字色（通常 = primary）

    # ── 侧边栏 ──
    sidebar_bg: str           # 实色（无背景图片时）
    sidebar_bg_rgba: str      # 半透明（有背景图片时）
    sidebar_text: str
    sidebar_separator: str
    sidebar_hover: str

    # ── 内容区 ──
    content_bg: str
    content_bg_rgba: str

    # ── 卡片 / 容器 ──
    card_bg: str
    card_bg_rgba: str
    card_border: str

    # ── 文字 ──
    text_primary: str
    text_secondary: str
    text_muted: str
    text_on_dark: str

    # ── 边框 / 线条 ──
    border_default: str
    border_strong: str
    border_subtle: str
    border_hover: str

    # ── 输入控件 ──
    input_bg: str
    input_border: str
    input_text: str
    input_focus_bg: str

    # ── 表格 ──
    table_bg: str
    table_grid: str
    table_header_bg: str
    table_selection_bg: str
    table_selection_text: str

    # ── 杂项 ──
    filter_bg: str
    dialog_bg: str
    scrollbar_handle: str
    scrollbar_handle_hover: str
    messagebox_bg: str
    radio_border: str
    radio_bg: str

    # ── 添加按钮 ──
    add_btn: str
    add_btn_hover: str

    # ── 次级按钮 ──
    secondary_btn_bg: str
    secondary_btn_text: str
    secondary_btn_border: str
    secondary_btn_hover_bg: str
    secondary_btn_hover_border: str

    # ── 日历 ──
    calendar_nav_bg: str
    calendar_nav_hover_bg: str
    calendar_nav_text: str
    calendar_nav_hover_text: str
    calendar_grid_bg_rgba: str
    calendar_header_bg_rgba: str
    day_cell_bg: str
    day_cell_hover_bg: str
    day_cell_hover_border: str
    day_cell_selected_bg: str
    day_cell_selected_border: str
    day_cell_today_bg: str
    day_cell_today_text: str
    day_income: str
    day_expense: str

    # ── 日历明细 ──
    calendar_detail_bg_rgba: str
    transaction_item_bg: str
    transaction_item_hover_bg: str


# ═════════════════════════════════════════════════════════════════════════
# 生成工具：从一个主色 + 基调 推导出完整令牌
# ═════════════════════════════════════════════════════════════════════════

def _make_tokens(
    tid: str,
    name: str,
    desc: str,
    primary: str,
    success: str = "#22c55e",
) -> ThemeTokens:
    """从核心主色推导出完整的主题色彩令牌。

    约定：
    - primary → 衍生 primary_600/700/50/100
    - 语义色跟随主色基调微调（冷暖感）
    - 侧边栏 / 卡片等中性色保持通用，保证跨主题可读性
    """
    p500 = primary
    p600 = _darken(p500, 0.88)
    p700 = _darken(p500, 0.78)
    p50 = _tint(p500, 0.15)
    p100 = _tint(p500, 0.30)
    p_text = _darken(p500, 0.60)

    # 语义色：success 也跟随主色微调
    s500 = success
    s600 = _darken(success, 0.88)
    s_light = _tint(success, 0.12)
    s_lighter = _tint(success, 0.07)
    s_border = _lighten(success, 0.70)

    # ── 侧边栏（深色基底，混入 15% 主色，使各主题侧边栏有微妙的色彩温差）──
    _sb = _blend("#1e293b", p500, 0.15)
    sidebar_bg = _sb
    sidebar_bg_rgba = _rgba(_sb, 230)
    sidebar_hover = _lighten(_sb, 0.12)
    sidebar_separator = _lighten(_sb, 0.08)

    # ── 内容区（浅色基底，混入 5% 主色，形成冷暖氛围差异）──
    _cb = _blend("#f5f7fa", p500, 0.05)
    content_bg = _cb
    content_bg_rgba = _rgba(_cb, 110)

    # ── 卡片（保持白色实底保证可读性，但边框微调）──
    _b1 = _blend("#e2e8f0", p500, 0.06)

    # ── 边框系列（均混入少量主色）──
    border_default = _b1
    border_subtle = _blend("#f1f5f9", p500, 0.04)
    border_strong = _blend("#d1d5db", p500, 0.08)
    border_hover = _blend("#9ca3af", p500, 0.12)

    # ── 滚动条 ──
    scrollbar_handle = _blend("#cbd5e1", p500, 0.18)
    scrollbar_handle_hover = _blend("#94a3b8", p500, 0.14)

    # ── 表格 ──
    table_header_bg = _blend("#f8fafc", p500, 0.04)

    # ── 筛选区 ──
    filter_bg = _blend("#ffffff", p500, 0.03)

    # ── 次级按钮 hover ──
    secondary_btn_hover_bg = _blend("#f9fafb", p500, 0.05)
    secondary_btn_hover_border = border_hover

    # ── 日历 ──
    calendar_nav_bg = _blend("#f1f5f9", p500, 0.06)
    calendar_nav_hover_bg = _blend("#e2e8f0", p500, 0.08)

    # ── 明细行 hover ──
    transaction_item_hover_bg = _blend("#f8fafc", p500, 0.04)

    return ThemeTokens(
        id=tid, name=name, description=desc,

        # 主色系
        primary_500=p500,
        primary_600=p600,
        primary_700=p700,
        primary_50=p50,
        primary_100=p100,
        primary_text=p_text,

        # 语义色
        success_500=s500,
        success_600=s600,
        success_light_bg=s_light,
        success_light_border=s_border,
        success_lighter_bg=s_lighter,
        error_500="#ef4444",
        error_600="#dc2626",
        warning_500="#f59e0b",
        income_text=s500,
        expense_text="#ef4444",
        balance_text=p500,

        # 侧边栏（每主题独立色调）──
        sidebar_bg=sidebar_bg,
        sidebar_bg_rgba=sidebar_bg_rgba,
        sidebar_text="#cbd5e1",
        sidebar_separator=sidebar_separator,
        sidebar_hover=sidebar_hover,

        # 内容区
        content_bg=content_bg,
        content_bg_rgba=content_bg_rgba,

        # 卡片
        card_bg="#ffffff",
        card_bg_rgba="rgba(255, 255, 255, 220)",
        card_border=border_default,

        # 文字
        text_primary="#1e293b",
        text_secondary="#475569",
        text_muted="#94a3b8",
        text_on_dark="#ffffff",

        # 边框
        border_default=border_default,
        border_strong=border_strong,
        border_subtle=border_subtle,
        border_hover=border_hover,

        # 输入
        input_bg="#ffffff",
        input_border="#d1d5db",
        input_text="#1f2937",
        input_focus_bg=p50,

        # 表格
        table_bg="#ffffff",
        table_grid=border_subtle,
        table_header_bg=table_header_bg,
        table_selection_bg=p50,
        table_selection_text=p_text,

        # 杂项
        filter_bg=filter_bg,
        dialog_bg=content_bg,
        scrollbar_handle=scrollbar_handle,
        scrollbar_handle_hover=scrollbar_handle_hover,
        messagebox_bg="#ffffff",
        radio_border=border_strong,
        radio_bg="#ffffff",

        # 按钮
        add_btn=s500,
        add_btn_hover=s600,
        secondary_btn_bg="#ffffff",
        secondary_btn_text="#374151",
        secondary_btn_border=border_strong,
        secondary_btn_hover_bg=secondary_btn_hover_bg,
        secondary_btn_hover_border=secondary_btn_hover_border,

        # 日历
        calendar_nav_bg=calendar_nav_bg,
        calendar_nav_hover_bg=calendar_nav_hover_bg,
        calendar_nav_text="#475569",
        calendar_nav_hover_text="#1e293b",
        calendar_grid_bg_rgba="rgba(255, 255, 255, 180)",
        calendar_header_bg_rgba="rgba(255, 255, 255, 220)",
        day_cell_bg="#ffffff",
        day_cell_hover_bg=s_light,
        day_cell_hover_border=s_border,
        day_cell_selected_bg=s_lighter,
        day_cell_selected_border=s500,
        day_cell_today_bg=s500,
        day_cell_today_text="#ffffff",
        day_income=s500,
        day_expense="#ef4444",
        calendar_detail_bg_rgba="rgba(255, 255, 255, 220)",
        transaction_item_bg="#ffffff",
        transaction_item_hover_bg=transaction_item_hover_bg,
    )


# ═════════════════════════════════════════════════════════════════════════
# 6 款内置主题
# ═════════════════════════════════════════════════════════════════════════

THEMES: tuple[ThemeTokens, ...] = (
    _make_tokens("sky_blue", "天空蓝", "清新专业的蓝色系 — 默认主题", "#3b82f6", "#22c55e"),
    _make_tokens("emerald", "翡翠绿", "自然生机的绿色系", "#10b981", "#22c55e"),
    _make_tokens("sunset", "日落橙", "温暖活力的橙色系", "#f97316", "#10b981"),
    _make_tokens("violet", "紫罗兰", "优雅神秘的紫色系", "#8b5cf6", "#10b981"),
    _make_tokens("ocean", "深海蓝", "冷静沉稳的青蓝色系", "#06b6d4", "#10b981"),
    _make_tokens("rose", "玫瑰粉", "柔美温暖的粉色系", "#ec4899", "#22c55e"),
)

THEME_MAP: dict[str, ThemeTokens] = {t.id: t for t in THEMES}
DEFAULT_THEME_ID = "sky_blue"


def get_theme(theme_id: str) -> ThemeTokens:
    return THEME_MAP.get(theme_id) or THEME_MAP[DEFAULT_THEME_ID]


# ═════════════════════════════════════════════════════════════════════════
# 统一配置数据结构
# ═════════════════════════════════════════════════════════════════════════

@dataclass
class AppConfig:
    """应用全局外观配置（主题 + 背景）。"""
    theme_id: str = DEFAULT_THEME_ID
    bg_enabled: bool = False
    bg_preset_id: str = "tulips"
    bg_opacity: int = 35

    def validate(self) -> AppConfig:
        if self.theme_id not in THEME_MAP:
            self.theme_id = DEFAULT_THEME_ID
        self.bg_opacity = max(0, min(100, self.bg_opacity))
        return self


def load_config() -> AppConfig:
    if not _CONFIG_PATH.exists():
        return AppConfig().validate()
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return AppConfig().validate()
        return AppConfig(
            theme_id=str(data.get("theme_id", DEFAULT_THEME_ID)),
            bg_enabled=bool(data.get("bg_enabled", False)),
            bg_preset_id=str(data.get("bg_preset_id", "tulips")),
            bg_opacity=int(data.get("bg_opacity", 35)),
        ).validate()
    except Exception:
        return AppConfig().validate()


def save_config(cfg: AppConfig) -> None:
    cfg.validate()
    _CONFIG_PATH.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ═════════════════════════════════════════════════════════════════════════
# 动态 QSS 生成器
# ═════════════════════════════════════════════════════════════════════════

def generate_stylesheet(theme_id: str = DEFAULT_THEME_ID) -> str:
    """根据主题 id 生成完整 QSS 样式表。"""
    t = get_theme(theme_id)

    return f"""\
/*
 * FinanceApp 动态主题样式表
 * 当前主题：{t.name}（{t.id}）
 */

/* ── 全局 ── */
QWidget {{
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {t.content_bg};
}}

/* ── 自定义背景层 ── */
#bgLayer {{
    background: transparent;
}}

/* ── 侧边栏 ── */
#sidebar {{
    background-color: {t.sidebar_bg_rgba};
    border: none;
}}
#sidebar QLabel {{
    color: {t.text_on_dark};
    font-size: 16px;
    font-weight: bold;
    padding: 16px 16px 8px 16px;
}}
#sidebar::separator {{
    height: 1px;
    background: {t.sidebar_separator};
    margin: 4px 12px;
}}

/* ── 侧边栏按钮 ── */
#sidebar QPushButton {{
    background-color: transparent;
    color: {t.sidebar_text};
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    font-size: 14px;
    margin: 2px 8px;
}}
#sidebar QPushButton:hover {{
    background-color: {t.sidebar_hover};
    color: {t.text_on_dark};
}}
#sidebar QPushButton:checked {{
    background-color: {t.primary_500};
    color: {t.text_on_dark};
    font-weight: bold;
}}

/* ── 内容区 ── */
#contentArea {{
    background-color: {t.content_bg_rgba};
    border: none;
}}

/* ── 卡片 ── */
QFrame#card {{
    background-color: {t.card_bg};
    border: 1px solid {t.card_border};
    border-radius: 12px;
    padding: 16px;
}}

/* ── 概览卡片 ── */
QLabel#overviewCard {{
    background-color: {t.card_bg};
    border: 1px solid {t.card_border};
    border-radius: 12px;
    padding: 20px;
    font-size: 14px;
}}
QLabel#overviewValue {{
    font-size: 24px;
    font-weight: bold;
    padding-top: 4px;
}}
QLabel#incomeValue {{ color: {t.income_text}; }}
QLabel#expenseValue {{ color: {t.expense_text}; }}
QLabel#balanceValue {{ color: {t.balance_text}; }}

/* ── 表格 ── */
QTableWidget {{
    background-color: {t.table_bg};
    border: 1px solid {t.card_border};
    border-radius: 8px;
    gridline-color: {t.table_grid};
    selection-background-color: {t.table_selection_bg};
    selection-color: {t.table_selection_text};
    font-size: 13px;
}}
QTableWidget::item {{
    padding: 8px;
    border-bottom: 1px solid {t.table_grid};
}}
QHeaderView::section {{
    background-color: {t.table_header_bg};
    color: {t.text_secondary};
    font-weight: bold;
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid {t.card_border};
    font-size: 13px;
}}

/* ── 按钮通用 ── */
QPushButton {{
    background-color: {t.primary_500};
    color: {t.text_on_dark};
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: bold;
    min-height: 20px;
}}
QPushButton:hover {{ background-color: {t.primary_600}; }}
QPushButton:pressed {{ background-color: {t.primary_700}; }}

QPushButton#dangerBtn {{
    background-color: {t.error_500};
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton#dangerBtn:hover {{ background-color: {t.error_600}; }}

QPushButton#secondaryBtn {{
    background-color: {t.secondary_btn_bg};
    color: {t.secondary_btn_text};
    border: 1px solid {t.secondary_btn_border};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton#secondaryBtn:hover {{
    background-color: {t.secondary_btn_hover_bg};
    border-color: {t.secondary_btn_hover_border};
}}

QPushButton#addBtn {{ background-color: {t.add_btn}; }}
QPushButton#addBtn:hover {{ background-color: {t.add_btn_hover}; }}

/* ── 输入框 ── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {t.input_bg};
    border: 1px solid {t.input_border};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: {t.input_text};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 2px solid {t.primary_500};
    background-color: {t.input_focus_bg};
}}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox QAbstractItemView {{
    background-color: {t.card_bg};
    border: 1px solid {t.input_border};
    border-radius: 4px;
    selection-background-color: {t.primary_50};
    selection-color: {t.primary_text};
}}

/* ── 日期编辑器 ── */
QDateEdit {{
    background-color: {t.input_bg};
    border: 1px solid {t.input_border};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: {t.input_text};
}}
QDateEdit::drop-down {{ border: none; width: 30px; }}

/* ── 文本框 ── */
QTextEdit {{
    background-color: {t.input_bg};
    border: 1px solid {t.input_border};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: {t.input_text};
}}
QTextEdit:focus {{
    border: 2px solid {t.primary_500};
    background-color: {t.input_focus_bg};
}}

/* ── 单选按钮 ── */
QRadioButton {{ font-size: 14px; spacing: 8px; padding: 4px; }}
QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid {t.radio_border};
    background-color: {t.radio_bg};
}}
QRadioButton::indicator:checked {{
    border: 2px solid {t.primary_500};
    background-color: {t.primary_500};
}}

/* ── 对话框 ── */
QDialog {{ background-color: {t.dialog_bg}; }}
QDialogButtonBox QPushButton {{ min-width: 80px; }}

/* ── 标签 ── */
QLabel#sectionTitle {{
    font-size: 18px;
    font-weight: bold;
    color: {t.text_primary};
    padding: 0 0 8px 0;
}}
QLabel#fieldLabel {{
    font-size: 13px;
    font-weight: bold;
    color: {t.text_secondary};
    padding: 0 0 4px 0;
}}

/* ── 筛选区 ── */
QFrame#filterBar {{
    background-color: {t.filter_bg};
    border: 1px solid {t.card_border};
    border-radius: 8px;
    padding: 12px;
}}

/* ── 滚动条 ── */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t.scrollbar_handle};
    min-height: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{ background: {t.scrollbar_handle_hover}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── 消息框 ── */
QMessageBox {{ background-color: {t.messagebox_bg}; }}

/* ── 日历页面 ── */
#calendarHeader {{
    background-color: {t.calendar_header_bg_rgba};
    border: none;
}}
#calendarMonthLabel {{
    font-size: 20px;
    font-weight: bold;
    color: {t.text_primary};
}}
#calendarMonthSummary {{
    font-size: 13px;
    color: {t.text_secondary};
    padding: 2px 0;
}}
#calendarNavBtn {{
    background-color: {t.calendar_nav_bg};
    color: {t.calendar_nav_text};
    border: 1px solid {t.card_border};
    border-radius: 6px;
    font-size: 14px;
    font-weight: bold;
    min-width: 20px;
    padding: 4px;
}}
#calendarNavBtn:hover {{
    background-color: {t.calendar_nav_hover_bg};
    color: {t.calendar_nav_hover_text};
}}

/* 网格区域 */
#calendarGridArea {{
    background-color: {t.calendar_grid_bg_rgba};
}}

#weekdayHeader {{
    font-size: 12px;
    font-weight: bold;
    color: {t.text_muted};
    background-color: transparent;
}}

/* 日期格子 */
#dayCell {{
    background-color: {t.day_cell_bg};
    border: 1px solid {t.border_subtle};
    border-radius: 8px;
}}
#dayCell:hover {{
    background-color: {t.day_cell_hover_bg};
    border-color: {t.day_cell_hover_border};
}}
#dayCell[selected="true"] {{
    background-color: {t.day_cell_selected_bg};
    border: 2px solid {t.day_cell_selected_border};
}}

#dayNumber {{
    font-size: 14px;
    font-weight: bold;
    color: {t.text_primary};
    padding: 0;
    margin: 0;
}}
#dayNumberToday {{
    font-size: 14px;
    font-weight: bold;
    color: {t.day_cell_today_text};
    background-color: {t.day_cell_today_bg};
    border-radius: 10px;
    padding: 0 4px;
    margin: 0;
}}
#dayIncome {{
    font-size: 10px;
    color: {t.day_income};
    padding: 0;
    margin: 0;
}}
#dayExpense {{
    font-size: 10px;
    color: {t.day_expense};
    padding: 0;
    margin: 0;
}}
#dayLunar {{
    font-size: 9px;
    color: {t.text_muted};
    padding: 0;
    margin: 0;
}}

/* 分隔线 */
#calendarSeparator {{
    background-color: {t.card_border};
    max-height: 1px;
}}

/* 明细区域 */
#calendarDetailArea {{
    background-color: {t.calendar_detail_bg_rgba};
}}
#calendarDaySummary {{
    font-size: 14px;
    color: {t.text_secondary};
    padding: 4px 0;
}}
#calendarDetailScroll {{ background-color: transparent; border: none; }}
#emptyDetailLabel {{ color: {t.text_muted}; font-size: 13px; }}

/* 账单明细行 */
#transactionItem {{
    background-color: {t.transaction_item_bg};
    border-bottom: 1px solid {t.border_subtle};
    border-radius: 0;
}}
#transactionItem:hover {{ background-color: {t.transaction_item_hover_bg}; }}
#txCategoryLabel {{ font-size: 13px; color: {t.text_primary}; }}
#txNoteLabel {{ font-size: 12px; color: {t.text_muted}; }}
#txAmountLabel {{ font-size: 14px; font-weight: bold; }}

/* ═══ 主题/背景设置对话框 ═══ */

#themeSwatchCard {{
    background-color: {t.card_bg};
    border: 2px solid {t.card_border};
    border-radius: 10px;
}}
#themeSwatchCard:hover {{ border-color: {t.border_hover}; }}
#themeSwatchCard[selected="true"] {{
    border-color: {t.primary_500};
    background-color: {t.primary_50};
}}

#bgThumbCard {{
    background-color: {t.card_bg};
    border: 2px solid {t.card_border};
    border-radius: 10px;
}}
#bgThumbCard:hover {{ border-color: {t.border_hover}; }}
#bgThumbCard[selected="true"] {{
    border-color: {t.primary_500};
    background-color: {t.primary_50};
}}

#bgThumbRadio {{
    font-size: 13px;
    color: {t.text_primary};
    spacing: 4px;
}}
#bgThumbRadio::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid {t.scrollbar_handle};
    background-color: {t.radio_bg};
}}
#bgThumbRadio::indicator:hover {{ border-color: {t.primary_500}; }}
#bgThumbRadio::indicator:checked {{
    border: 2px solid {t.primary_500};
    background-color: {t.primary_500};
}}

#opacityValue {{
    font-size: 13px;
    font-weight: bold;
    color: {t.text_primary};
    font-family: "Consolas", "Courier New", monospace;
}}

#bgPreview {{
    background-color: {t.calendar_nav_bg};
    border: 1px solid {t.scrollbar_handle};
    border-radius: 8px;
}}
"""


# ═════════════════════════════════════════════════════════════════════════
# ThemeManager 单例
# ═════════════════════════════════════════════════════════════════════════

class ThemeManager:
    """全局主题管理器。

    职责：
    - 维护当前的 AppConfig（theme + bg）
    - 提供 update_config() 接口更新并持久化
    - 提供 generate_stylesheet() 生成当前主题 QSS
    """

    def __init__(self) -> None:
        self._config: AppConfig = load_config()

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def theme(self) -> ThemeTokens:
        return get_theme(self._config.theme_id)

    def update(self, **kwargs) -> AppConfig:
        """更新指定字段并持久化。可传 theme_id / bg_enabled / bg_preset_id / bg_opacity。"""
        updates = asdict(self._config)
        for k, v in kwargs.items():
            if k in updates:
                updates[k] = v
        self._config = AppConfig(**updates).validate()
        save_config(self._config)
        return self._config

    def stylesheet(self) -> str:
        """返回当前主题的完整 QSS。"""
        return generate_stylesheet(self._config.theme_id)


# ── 全局单例 ──

_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    global _manager
    if _manager is None:
        _manager = ThemeManager()
    return _manager


def reset_theme_manager() -> None:
    global _manager
    _manager = None


# ── CLI 测试 ──

if __name__ == "__main__":
    print("可用主题：")
    for t in THEMES:
        swatch = "█" * 6
        print(f"  [{t.id}] {swatch}  {t.name} — {t.description}")
    print(f"\n当前配置: {get_theme_manager().config}")
    print(f"\nQSS 长度: {len(generate_stylesheet())} 字符")
    print("\n--- QSS 预览（前 400 字符）---")
    print(generate_stylesheet()[:400])
