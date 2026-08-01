"""
ui/main_window.py — 主窗口（含侧边导航 + 动态主题 + 自定义背景）

作为应用的顶层窗口，包含左侧侧边导航、右侧内容区域，以及最底层的
自定义背景层。主题色彩和背景配置由 utils/theme_manager 统一管理，
启动时自动加载上次保存的设置。
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap

from core.database import init_db, close_connection
from ui.records import RecordsPage
from ui.dashboard import DashboardPage
from ui.calendar_page import CalendarPage
from ui.categories import CategoriesPage
from ui.import_page import ImportPage
from ui.ai_analysis import AIAnalysisPage
from ui.theme_settings_dialog import ThemeSettingsDialog
from utils.theme_manager import get_theme_manager
from utils.background_manager import get_background_manager


class MainWindow(QMainWindow):
    """FinanceApp 主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("💰 个人财务管理")
        self.setMinimumSize(1000, 700)
        self.resize(1100, 750)

        init_db()
        self._init_ui()
        self._apply_theme()
        self._refresh_background()

    # ── UI 构建 ──

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        # ── 背景标签（最底层，不加入 layout，绝对定位）──
        self._bg_label = QLabel(central)
        self._bg_label.setObjectName("bgLayer")
        self._bg_label.setScaledContents(True)
        self._bg_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._bg_label.setGeometry(central.rect())
        self._bg_label.lower()

        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── 侧边栏 ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(4)
        sidebar_layout.setContentsMargins(4, 12, 4, 12)

        app_label = QLabel("💰 个人财务管理")
        app_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white; padding: 8px 0;")
        sidebar_layout.addWidget(app_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #334155;")
        sidebar_layout.addWidget(line)

        nav_items = [
            ("📊", "仪表盘", "dashboard"),
            ("📅", "日历", "calendar"),
            ("📋", "收支记录", "records"),
            ("➕", "新增记录", "add_record"),
            ("📁", "导入账单", "import"),
            ("🏷️", "分类管理", "categories"),
            ("🤖", "AI 分析", "ai_analysis"),
        ]

        self._nav_buttons: list[tuple[QPushButton, str]] = []

        for icon, text, page_id in nav_items:
            btn = QPushButton(f"  {icon}  {text}")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, pid=page_id: self._switch_page(pid))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append((btn, page_id))

        sidebar_layout.addStretch()

        self._settings_btn = QPushButton("  🎨  外观设置")
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.clicked.connect(self._open_appearance_settings)
        sidebar_layout.addWidget(self._settings_btn)

        version_label = QLabel("v0.3.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 4px 0;")
        sidebar_layout.addWidget(version_label)

        main_layout.addWidget(sidebar)

        # ── 内容区 ──
        self._stack = QStackedWidget()
        self._stack.setObjectName("contentArea")

        self._pages: dict[str, QWidget] = {}

        dashboard_page = DashboardPage()
        self._pages["dashboard"] = dashboard_page
        self._stack.addWidget(dashboard_page)

        calendar_page = CalendarPage()
        self._pages["calendar"] = calendar_page
        self._stack.addWidget(calendar_page)

        records_page = RecordsPage()
        self._pages["records"] = records_page
        self._stack.addWidget(records_page)

        categories_page = CategoriesPage()
        self._pages["categories"] = categories_page
        self._stack.addWidget(categories_page)

        import_page = ImportPage()
        self._pages["import"] = import_page
        self._stack.addWidget(import_page)

        ai_page = AIAnalysisPage()
        self._pages["ai_analysis"] = ai_page
        self._stack.addWidget(ai_page)

        for page_id, page_name in [("add_record", "新增记录")]:
            placeholder = self._create_placeholder_page(page_name, page_id)
            self._pages[page_id] = placeholder
            self._stack.addWidget(placeholder)

        main_layout.addWidget(self._stack, 1)

        self._switch_page("dashboard")

    def _create_placeholder_page(self, name: str, page_id: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(f"{name}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #94a3b8; font-weight: bold;")
        layout.addWidget(label)
        sub = QLabel("该功能将在后续版本实现 ✨")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("font-size: 14px; color: #cbd5e1; margin-top: 8px;")
        layout.addWidget(sub)
        return page

    def _switch_page(self, page_id: str) -> None:
        for btn, pid in self._nav_buttons:
            btn.setChecked(pid == page_id)

        if page_id == "add_record":
            for btn, pid in self._nav_buttons:
                btn.setChecked(pid == "records")
            self._open_add_record_dialog()
            return

        page = self._pages.get(page_id)
        if page:
            self._stack.setCurrentWidget(page)
            if page_id == "records":
                page.refresh()
            if page_id == "dashboard":
                page.refresh()
            if page_id == "calendar":
                page.refresh()
            if page_id == "categories":
                page.refresh()

    def _open_add_record_dialog(self) -> None:
        from ui.add_record import AddRecordDialog
        dialog = AddRecordDialog(self)
        if dialog.exec() == AddRecordDialog.DialogCode.Accepted:
            self._switch_page("records")

    # ── 外观设置 ──

    def _open_appearance_settings(self) -> None:
        """打开主题+背景设置对话框。"""
        for btn, _ in self._nav_buttons:
            btn.setChecked(False)

        dialog = ThemeSettingsDialog(self)
        if dialog.exec() == ThemeSettingsDialog.DialogCode.Accepted:
            # 用户点了应用 → 全量刷新
            self._apply_theme()
            self._refresh_background()

        # 恢复当前页面选中态
        current_id = None
        idx = self._stack.currentIndex()
        if idx >= 0:
            current_widget = self._stack.widget(idx)
            for pid, w in self._pages.items():
                if w is current_widget:
                    current_id = pid
                    break
        for btn, pid in self._nav_buttons:
            btn.setChecked(pid == current_id)

    def _apply_theme(self) -> None:
        """从 theme_manager 获取动态 QSS 并应用到窗口。"""
        qss = get_theme_manager().stylesheet()
        self.setStyleSheet(qss)

    # ── 背景 ──

    def _refresh_background(self) -> None:
        """重新生成背景 pixmap。"""
        central = self.centralWidget()
        size = central.size() if central else self.size()
        if size.width() <= 0 or size.height() <= 0:
            size = self.size()

        pixmap = get_background_manager().render(QSize(size.width(), size.height()))
        if pixmap.isNull():
            self._bg_label.clear()
            self._bg_label.setStyleSheet("")
        else:
            self._bg_label.setPixmap(pixmap)
            self._bg_label.setStyleSheet("background: transparent;")

    # ── 事件 ──

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        central = self.centralWidget()
        if central is not None:
            self._bg_label.setGeometry(central.rect())
        self._refresh_background()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_background()

    # ── 清理 ──

    def closeEvent(self, event) -> None:
        close_connection()
        event.accept()
