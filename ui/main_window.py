"""
ui/main_window.py - 主窗口（含侧边导航）

作为应用的顶层窗口，包含左侧侧边导航和右侧内容区域。
Phase 1 阶段实现了收支记录页面的导航，其余页面为占位。
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from core.database import init_db, close_connection
from ui.records import RecordsPage


class MainWindow(QMainWindow):
    """FinanceApp 主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("💰 个人财务管理")
        self.setMinimumSize(1000, 700)
        self.resize(1100, 750)

        # 初始化数据库
        init_db()

        # 构建 UI
        self._init_ui()
        self._apply_style()

    def _init_ui(self) -> None:
        """构建主界面。"""
        central = QWidget()
        self.setCentralWidget(central)

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

        # 应用标题
        app_label = QLabel("💰 个人财务管理")
        app_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white; padding: 8px 0;")
        sidebar_layout.addWidget(app_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #334155;")
        sidebar_layout.addWidget(line)

        # 导航按钮
        nav_items = [
            ("📊", "仪表盘", "dashboard"),
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

        # 版本号
        version_label = QLabel("v0.2.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 4px 0;")
        sidebar_layout.addWidget(version_label)

        main_layout.addWidget(sidebar)

        # ── 内容区域 ──
        self._stack = QStackedWidget()
        self._stack.setObjectName("contentArea")

        # 各页面
        self._pages: dict[str, QWidget] = {}

        # 收支记录页（Phase 1 实现）
        records_page = RecordsPage()
        self._pages["records"] = records_page
        self._stack.addWidget(records_page)

        # 其他页面占位
        for page_id, page_name in [
            ("dashboard", "仪表盘"),
            ("add_record", "新增记录"),
            ("import", "导入账单"),
            ("categories", "分类管理"),
            ("ai_analysis", "AI 分析"),
        ]:
            placeholder = self._create_placeholder_page(page_name, page_id)
            self._pages[page_id] = placeholder
            self._stack.addWidget(placeholder)

        main_layout.addWidget(self._stack, 1)

        # 默认显示记录页
        self._switch_page("records")

    def _create_placeholder_page(self, name: str, page_id: str) -> QWidget:
        """创建占位页面。"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(f"{name}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #94a3b8; font-weight: bold;")
        layout.addWidget(label)

        sub = QLabel("该功能将在后续阶段实现 ✨")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("font-size: 14px; color: #cbd5e1; margin-top: 8px;")
        layout.addWidget(sub)

        return page

    def _switch_page(self, page_id: str) -> None:
        """切换侧边栏导航页面。"""
        # 更新按钮选中状态
        for btn, pid in self._nav_buttons:
            btn.setChecked(pid == page_id)

        # 特殊处理：新增记录按钮打开对话框而非切换页面
        if page_id == "add_record":
            # 确保记录页保持选中
            for btn, pid in self._nav_buttons:
                btn.setChecked(pid == "records")
            self._open_add_record_dialog()
            return

        # 切换页面
        page = self._pages.get(page_id)
        if page:
            self._stack.setCurrentWidget(page)

            # 切换到记录页时刷新
            if page_id == "records":
                page.refresh()

    def _open_add_record_dialog(self) -> None:
        """打开新增记录对话框。"""
        from ui.add_record import AddRecordDialog
        dialog = AddRecordDialog(self)
        if dialog.exec() == AddRecordDialog.DialogCode.Accepted:
            # 切换到记录页并刷新
            self._switch_page("records")

    def _apply_style(self) -> None:
        """加载 QSS 样式表。"""
        import os
        style_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def closeEvent(self, event) -> None:
        """窗口关闭时清理资源。"""
        close_connection()
        event.accept()
