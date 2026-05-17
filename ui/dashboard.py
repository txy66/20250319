"""
ui/dashboard.py - 仪表盘页面

展示本月收支概览卡片 + 三张可视化图表：
- 月度收支趋势折线图（近12个月）
- 本月支出分类饼图
- 月度收入 vs 支出柱状图（近6个月）

支持切换时段范围（本周/本月/本年）。
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

from core.statistics import get_summary, get_monthly_stats, get_expense_by_category
from utils.formatter import format_amount
from utils.date_helper import current_week_range, current_month_range


class DashboardPage(QWidget):
    """仪表盘页面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._period = "month"  # week / month / year
        self._init_ui()

    def _init_ui(self) -> None:
        # 使用滚动区域包裹，防止图表超出
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 标题 + 时段切换 ──
        header = QHBoxLayout()

        title = QLabel("📊 仪表盘")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        # 时段按钮
        self._btn_week = QPushButton("本周")
        self._btn_week.setObjectName("secondaryBtn")
        self._btn_week.clicked.connect(lambda: self._switch_period("week"))
        header.addWidget(self._btn_week)

        self._btn_month = QPushButton("本月")
        self._btn_month.clicked.connect(lambda: self._switch_period("month"))
        header.addWidget(self._btn_month)

        self._btn_year = QPushButton("本年")
        self._btn_year.setObjectName("secondaryBtn")
        self._btn_year.clicked.connect(lambda: self._switch_period("year"))
        header.addWidget(self._btn_year)

        layout.addLayout(header)

        # ── 概览卡片 ──
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self._card_income = self._create_overview_card("总收入", "0.00", "#22c55e", "incomeValue")
        self._card_expense = self._create_overview_card("总支出", "0.00", "#ef4444", "expenseValue")
        self._card_balance = self._create_overview_card("净利润", "0.00", "#3b82f6", "balanceValue")
        self._card_count = self._create_overview_card("记录数", "0", "#6366f1", "")

        cards_layout.addWidget(self._card_income)
        cards_layout.addWidget(self._card_expense)
        cards_layout.addWidget(self._card_balance)
        cards_layout.addWidget(self._card_count)

        layout.addLayout(cards_layout)

        # ── 图表区域（两行两列） ──
        charts_grid = QGridLayout()
        charts_grid.setSpacing(12)

        # 折线图（占满第一行）
        self._line_view = QWebEngineView()
        self._line_view.setMinimumHeight(380)
        charts_grid.addWidget(self._create_chart_card("月度收支趋势", self._line_view), 0, 0, 1, 2)

        # 饼图
        self._pie_view = QWebEngineView()
        self._pie_view.setMinimumHeight(380)
        charts_grid.addWidget(self._create_chart_card("支出分类占比", self._pie_view), 1, 0)

        # 柱状图
        self._bar_view = QWebEngineView()
        self._bar_view.setMinimumHeight(380)
        charts_grid.addWidget(self._create_chart_card("月度收入 vs 支出", self._bar_view), 1, 1)

        layout.addLayout(charts_grid)
        layout.addStretch()

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # 默认加载
        self._switch_period("month")

    def _create_overview_card(self, title: str, value: str, color: str, value_id: str) -> QFrame:
        """创建概览卡片。"""
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(90)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)
        card_layout.setContentsMargins(16, 12, 16, 12)

        label = QLabel(title)
        label.setStyleSheet("font-size: 13px; color: #64748b; font-weight: bold;")
        card_layout.addWidget(label)

        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
        if value_id:
            value_label.setObjectName(value_id)
        card_layout.addWidget(value_label)

        card_layout.addStretch()
        return card

    def _create_chart_card(self, title: str, chart_view: QWebEngineView) -> QFrame:
        """创建图表卡片。"""
        card = QFrame()
        card.setObjectName("card")

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)
        card_layout.setContentsMargins(12, 12, 12, 12)

        chart_title = QLabel(title)
        chart_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #334155; padding: 0 4px;")
        card_layout.addWidget(chart_title)

        card_layout.addWidget(chart_view)
        return card

    def _switch_period(self, period: str) -> None:
        """切换时段范围。"""
        self._period = period

        # 更新按钮样式
        for btn, pid in [
            (self._btn_week, "week"),
            (self._btn_month, "month"),
            (self._btn_year, "year"),
        ]:
            if pid == period:
                btn.setObjectName("")  # 默认主色按钮
                btn.setStyleSheet("")
            else:
                btn.setObjectName("secondaryBtn")
                btn.setStyleSheet("")

        # 重新加载数据
        self._load_data()

    def _get_period_range(self) -> tuple[str, str]:
        """获取当前时段的日期范围。"""
        if self._period == "week":
            return current_week_range()
        elif self._period == "month":
            return current_month_range()
        else:  # year
            from datetime import date
            today = date.today()
            return f"{today.year}-01-01", today.isoformat()

    def _load_data(self) -> None:
        """加载统计和图表数据。"""
        start, end = self._get_period_range()

        # 更新概览卡片
        summary = get_summary(start_date=start, end_date=end)

        self._card_income.children()[1].setText(format_amount(summary["income"]))
        self._card_expense.children()[1].setText(format_amount(summary["expense"]))
        self._card_balance.children()[1].setText(format_amount(summary["balance"]))
        self._card_count.children()[1].setText(f"{summary['count']} 条")

        # 加载图表
        self._load_charts(start, end)

    def _load_charts(self, start: str, end: str) -> None:
        """异步加载三张图表。"""
        from charts.line_chart import generate_monthly_trend_chart
        from charts.pie_chart import generate_expense_pie_chart
        from charts.bar_chart import generate_monthly_bar_chart

        # 月度统计数据（用于折线图和柱状图）
        monthly = get_monthly_stats(12)

        # 折线图
        line_html = generate_monthly_trend_chart(monthly)
        self._line_view.setHtml(self._wrap_html(line_html))

        # 饼图（使用当前时段）
        expense_by_cat = get_expense_by_category(start_date=start, end_date=end)
        if expense_by_cat:
            pie_html = generate_expense_pie_chart(expense_by_cat)
        else:
            pie_html = '<div style="text-align:center;padding:80px;color:#94a3b8;font-size:16px;">暂无支出数据</div>'
        self._pie_view.setHtml(self._wrap_html(pie_html))

        # 柱状图
        bar_html = generate_monthly_bar_chart(monthly)
        self._bar_view.setHtml(self._wrap_html(bar_html))

    @staticmethod
    def _wrap_html(body: str) -> str:
        """包装 pyecharts HTML 片段为完整页面。"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ margin: 0; padding: 0; background: #ffffff; }}
    </style>
</head>
<body>
{body}
</body>
</html>"""

    def refresh(self) -> None:
        """刷新仪表盘数据（供外部调用）。"""
        self._load_data()
