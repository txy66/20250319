"""
ui/calendar_page.py - 日历收支查询页面

以月历视图展示每日收入/支出汇总，点击日期加载当日账单明细。
布局：头部（年月导航 + 月度汇总）→ 日历网格 → 当日明细列表。
"""

from __future__ import annotations

from datetime import date, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.statistics import get_summary
from core.transaction import list_transactions
from utils.lunar_helper import get_lunar_text
from utils.formatter import format_amount


class DayCell(QFrame):
    """日历中的单日格子。"""

    clicked = pyqtSignal(object)  # 发射 self

    def __init__(self, day: int, parent=None):
        super().__init__(parent)
        self.day = day
        self.date_str: str = ""
        self.is_today: bool = False
        self.is_selected: bool = False
        self.income: float = 0.0
        self.expense: float = 0.0

        self.setObjectName("dayCell")
        self.setFixedSize(120, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setSpacing(1)
        layout.setContentsMargins(4, 4, 4, 2)

        # 日期数字
        self._day_label = QLabel(str(day))
        self._day_label.setObjectName("dayNumber")
        self._day_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._day_label)

        # 收入（绿色小字）
        self._income_label = QLabel("")
        self._income_label.setObjectName("dayIncome")
        self._income_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._income_label)

        # 支出（红色小字）
        self._expense_label = QLabel("")
        self._expense_label.setObjectName("dayExpense")
        self._expense_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._expense_label)

        # 农历/节假日/节气
        self._lunar_label = QLabel("")
        self._lunar_label.setObjectName("dayLunar")
        self._lunar_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self._lunar_label)

        layout.addStretch()

    def mousePressEvent(self, event) -> None:
        """点击格子时发射 clicked 信号。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)

    def set_data(self, date_str: str, income: float, expense: float, lunar_text: str,
                 is_today: bool = False) -> None:
        """更新格子数据。"""
        self.date_str = date_str
        self.income = income
        self.expense = expense
        self.is_today = is_today

        # 收入：有收入显示 +金额，无收入显示 +0
        if income > 0:
            self._income_label.setText(f"+{income:.0f}")
            self._income_label.setVisible(True)
        else:
            self._income_label.setText("+0")
            self._income_label.setVisible(True)

        # 支出：有支出显示 -金额，无支出不显示
        if expense > 0:
            self._expense_label.setText(f"-{expense:.0f}")
            self._expense_label.setVisible(True)
        else:
            self._expense_label.setVisible(False)

        # 农历
        self._lunar_label.setText(lunar_text)

        # 今日标记
        if is_today:
            self._day_label.setObjectName("dayNumberToday")

    def set_selected(self, selected: bool) -> None:
        """设置选中状态。"""
        self.is_selected = selected
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class CalendarPage(QWidget):
    """日历收支查询页面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("calendarPage")

        # 当前显示的年月
        today = date.today()
        self._year = today.year
        self._month = today.month

        # 选中日期（默认今天）
        self._selected_date: str = today.isoformat()

        # 日历格子缓存
        self._cells: dict[int, DayCell] = {}

        self._init_ui()
        # 首次加载
        self.refresh()

    def _init_ui(self) -> None:
        """构建页面布局。"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── 头部区域 ──
        header = QWidget()
        header.setObjectName("calendarHeader")
        header.setFixedHeight(100)
        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(6)
        header_layout.setContentsMargins(24, 12, 24, 8)

        # 第一行：年月导航
        nav_row = QHBoxLayout()
        nav_row.setSpacing(12)

        self._month_label = QLabel("")
        self._month_label.setObjectName("calendarMonthLabel")
        nav_row.addWidget(self._month_label)

        nav_row.addStretch()

        # 上一月按钮
        self._prev_btn = QPushButton("◀")
        self._prev_btn.setObjectName("calendarNavBtn")
        self._prev_btn.setFixedSize(32, 32)
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(self._prev_month)
        nav_row.addWidget(self._prev_btn)

        # 下一月按钮
        self._next_btn = QPushButton("▶")
        self._next_btn.setObjectName("calendarNavBtn")
        self._next_btn.setFixedSize(32, 32)
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._next_month)
        nav_row.addWidget(self._next_btn)

        header_layout.addLayout(nav_row)

        # 第二行：月度汇总
        self._month_summary = QLabel("")
        self._month_summary.setObjectName("calendarMonthSummary")
        self._month_summary.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(self._month_summary)

        main_layout.addWidget(header)

        # ── 日历网格区域 ──
        calendar_widget = QWidget()
        calendar_widget.setObjectName("calendarGridArea")
        calendar_outer_layout = QVBoxLayout(calendar_widget)
        calendar_outer_layout.setSpacing(0)
        calendar_outer_layout.setContentsMargins(24, 8, 24, 4)

        # 星期表头
        week_header = QHBoxLayout()
        week_header.setSpacing(0)
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        for wd in weekdays:
            lbl = QLabel(wd)
            lbl.setObjectName("weekdayHeader")
            lbl.setFixedHeight(28)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            week_header.addWidget(lbl)
        calendar_outer_layout.addLayout(week_header)

        # 日期网格
        self._grid_layout = QGridLayout()
        self._grid_layout.setSpacing(4)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        calendar_outer_layout.addLayout(self._grid_layout)

        main_layout.addWidget(calendar_widget, 1)

        # ── 分隔线 ──
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("calendarSeparator")
        main_layout.addWidget(separator)

        # ── 当日明细区域 ──
        detail_widget = QWidget()
        detail_widget.setObjectName("calendarDetailArea")
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setSpacing(6)
        detail_layout.setContentsMargins(24, 8, 24, 12)

        # 当日汇总
        self._day_summary = QLabel("")
        self._day_summary.setObjectName("calendarDaySummary")
        self._day_summary.setAlignment(Qt.AlignmentFlag.AlignLeft)
        detail_layout.addWidget(self._day_summary)

        # 明细列表（滚动区域）
        scroll = QScrollArea()
        scroll.setObjectName("calendarDetailScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._detail_container = QWidget()
        self._detail_layout = QVBoxLayout(self._detail_container)
        self._detail_layout.setSpacing(0)
        self._detail_layout.setContentsMargins(0, 0, 0, 0)
        self._detail_layout.addStretch()

        scroll.setWidget(self._detail_container)
        detail_layout.addWidget(scroll)

        main_layout.addWidget(detail_widget, 1)

    # ─── 数据加载 ──────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """刷新日历页面全部数据。"""
        self._update_header()
        self._build_calendar()
        self._update_day_detail()

    def _update_header(self) -> None:
        """更新头部年月标签和月度汇总。"""
        self._month_label.setText(f"{self._year}年{self._month}月")

        # 当月汇总
        first_day = date(self._year, self._month, 1)
        if self._month == 12:
            last_day = date(self._year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(self._year, self._month + 1, 1) - timedelta(days=1)

        summary = get_summary(start_date=first_day.isoformat(), end_date=last_day.isoformat())
        income_color = "#10b981" if summary["income"] > 0 else "#94a3b8"
        expense_color = "#ef4444" if summary["expense"] > 0 else "#94a3b8"
        balance = summary["balance"]
        balance_color = "#10b981" if balance >= 0 else "#ef4444"

        self._month_summary.setText(
            f'<span style="color:{income_color};">收 {format_amount(summary["income"])}</span>'
            f'&nbsp;&nbsp;&nbsp;'
            f'<span style="color:{expense_color};">支 {format_amount(summary["expense"])}</span>'
            f'&nbsp;&nbsp;&nbsp;'
            f'<span style="color:{balance_color};">余 {format_amount(balance)}</span>'
        )

    def _build_calendar(self) -> None:
        """构建日历网格，填充日期数据。"""
        # 清空整个网格（包括旧空白占位 frame）
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._cells.clear()

        today = date.today()

        # 当月第一天是星期几（周一=0 ... 周日=6）
        first_day = date(self._year, self._month, 1)
        # Python weekday: Mon=0, Sun=6 → 直接就是我们需要的形式
        start_weekday = first_day.weekday()

        # 当月天数
        if self._month == 12:
            days_in_month = (date(self._year + 1, 1, 1) - timedelta(days=1)).day
        else:
            days_in_month = (date(self._year, self._month + 1, 1) - timedelta(days=1)).day

        # 获取当月每日汇总数据
        first_str = first_day.isoformat()
        if self._month == 12:
            last_str = (date(self._year + 1, 1, 1) - timedelta(days=1)).isoformat()
        else:
            last_str = (date(self._year, self._month + 1, 1) - timedelta(days=1)).isoformat()

        daily_data = self._get_daily_amounts(first_str, last_str)

        row = 0
        col = 0

        # 填充月初空白（上月占位）
        for _ in range(start_weekday):
            blank = QFrame()
            blank.setFixedSize(120, 90)
            self._grid_layout.addWidget(blank, row, col)
            col += 1
            if col >= 7:
                col = 0
                row += 1

        # 填充当月日期
        for day in range(1, days_in_month + 1):
            d = date(self._year, self._month, day)
            date_str = d.isoformat()

            cell = DayCell(day)
            is_today = (d == today)

            data = daily_data.get(date_str, {"income": 0.0, "expense": 0.0})
            lunar_text = get_lunar_text(d)

            cell.set_data(date_str, data["income"], data["expense"], lunar_text, is_today)

            # 默认选中今天或当前选中日期
            if date_str == self._selected_date:
                cell.set_selected(True)

            cell.clicked.connect(lambda checked, c=cell: self._on_day_clicked(c))

            self._cells[day] = cell
            self._grid_layout.addWidget(cell, row, col)

            col += 1
            if col >= 7:
                col = 0
                row += 1

        # 填充月末空白
        if col > 0:
            for _ in range(7 - col):
                blank = QFrame()
                blank.setFixedSize(120, 90)
                self._grid_layout.addWidget(blank, row, col)
                col += 1

    def _update_day_detail(self) -> None:
        """更新当日明细区域。"""
        if not self._selected_date:
            self._day_summary.setText("")
            self._clear_detail_items()
            return

        # 当日汇总
        summary = get_summary(start_date=self._selected_date, end_date=self._selected_date)
        income_color = "#10b981" if summary["income"] > 0 else "#94a3b8"
        expense_color = "#ef4444" if summary["expense"] > 0 else "#94a3b8"
        balance = summary["balance"]
        balance_color = "#10b981" if balance >= 0 else "#ef4444"

        # 格式化选中日期显示
        sel_date = date.fromisoformat(self._selected_date)
        date_display = f"{sel_date.month}月{sel_date.day}日"

        self._day_summary.setText(
            f'<span style="font-weight:bold;">{date_display}</span>&nbsp;&nbsp;'
            f'<span style="color:{income_color};">收 {format_amount(summary["income"])}</span>'
            f'&nbsp;&nbsp;'
            f'<span style="color:{expense_color};">支 {format_amount(summary["expense"])}</span>'
            f'&nbsp;&nbsp;'
            f'<span style="color:{balance_color};">余 {format_amount(balance)}</span>'
        )

        # 加载当日账单
        transactions = list_transactions(
            start_date=self._selected_date,
            end_date=self._selected_date,
            limit=50,
        )

        self._clear_detail_items()

        if not transactions:
            empty_lbl = QLabel("暂无账单记录")
            empty_lbl.setObjectName("emptyDetailLabel")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setFixedHeight(60)
            # 在 stretch 之前插入
            count = self._detail_layout.count()
            self._detail_layout.insertWidget(count - 1, empty_lbl)
            return

        for tx in transactions:
            item = self._create_transaction_item(tx)
            count = self._detail_layout.count()
            self._detail_layout.insertWidget(count - 1, item)

    def _create_transaction_item(self, tx: dict) -> QFrame:
        """创建单条账单明细行。"""
        item = QFrame()
        item.setObjectName("transactionItem")
        item.setFixedHeight(56)

        layout = QHBoxLayout(item)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(12)

        # 左侧：分类图标 + 名称
        icon = tx.get("category_icon", "📌") or "📌"
        name = tx.get("category_name", "未分类") or "未分类"
        left_label = QLabel(f"{icon} {name}")
        left_label.setObjectName("txCategoryLabel")
        left_label.setFixedWidth(160)
        layout.addWidget(left_label)

        # 中间：备注
        note = tx.get("note", "") or ""
        mid_label = QLabel(note)
        mid_label.setObjectName("txNoteLabel")
        layout.addWidget(mid_label, 1)

        # 右侧：金额
        amount = tx.get("amount", 0)
        tx_type = tx.get("type", "expense")
        if tx_type == "income":
            amount_text = f"+{amount:.2f}"
            amount_color = "#10b981"
        else:
            amount_text = f"-{amount:.2f}"
            amount_color = "#ef4444"

        right_label = QLabel(amount_text)
        right_label.setObjectName("txAmountLabel")
        right_label.setStyleSheet(f"color: {amount_color}; font-weight: bold; font-size: 14px;")
        right_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right_label.setFixedWidth(100)
        layout.addWidget(right_label)

        return item

    def _clear_detail_items(self) -> None:
        """清除明细列表中所有账单项（保留末尾 stretch）。"""
        while self._detail_layout.count() > 1:
            item = self._detail_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # ─── 交互处理 ──────────────────────────────────────────────────────────

    def _on_day_clicked(self, cell: DayCell) -> None:
        """点击日期格子。"""
        # 取消旧选中
        for c in self._cells.values():
            c.set_selected(False)

        # 选中当前
        cell.set_selected(True)
        self._selected_date = cell.date_str
        self._update_day_detail()

    def _prev_month(self) -> None:
        """上一个月。"""
        self._month -= 1
        if self._month < 1:
            self._month = 12
            self._year -= 1
        self.refresh()

    def _next_month(self) -> None:
        """下一个月。"""
        self._month += 1
        if self._month > 12:
            self._month = 1
            self._year += 1
        self.refresh()

    # ─── 数据查询 ──────────────────────────────────────────────────────────

    @staticmethod
    def _get_daily_amounts(start_date: str, end_date: str) -> dict[str, dict]:
        """
        批量查询日期范围内每日收支金额。

        一次性 SQL 查询比逐日 get_summary 高效得多。

        Returns:
            {"2026-06-01": {"income": 100.0, "expense": 50.0}, ...}
        """
        from core.database import get_connection
        conn = get_connection()

        result: dict[str, dict] = {}

        # 每日收入
        income_rows = conn.execute(
            """SELECT date, SUM(amount) as total
               FROM transactions
               WHERE type = 'income' AND date BETWEEN ? AND ?
               GROUP BY date""",
            (start_date, end_date),
        ).fetchall()

        # 每日支出
        expense_rows = conn.execute(
            """SELECT date, SUM(amount) as total
               FROM transactions
               WHERE type = 'expense' AND date BETWEEN ? AND ?
               GROUP BY date""",
            (start_date, end_date),
        ).fetchall()

        for row in income_rows:
            d = row["date"]
            if d not in result:
                result[d] = {"income": 0.0, "expense": 0.0}
            result[d]["income"] = round(row["total"], 2)

        for row in expense_rows:
            d = row["date"]
            if d not in result:
                result[d] = {"income": 0.0, "expense": 0.0}
            result[d]["expense"] = round(row["total"], 2)

        return result
