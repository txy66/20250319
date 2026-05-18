"""
ui/records.py - 记录列表页

功能：
- 以表格展示交易记录（按日期降序）
- 支持按类型、分类、日期范围、关键词筛选
- 支持编辑和删除操作
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QDateEdit, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog,
)
from PyQt6.QtCore import Qt, QDate

from core.transaction import list_transactions, delete_transaction, count_transactions
from core.category import list_categories
from utils.formatter import format_amount
from ui.add_record import AddRecordDialog


class RecordsPage(QWidget):
    """收支记录列表页。"""

    PAGE_SIZE = 50  # 每页显示条数

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_offset = 0
        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 标题 ──
        title = QLabel("📋 收支记录")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # ── 筛选栏 ──
        filter_frame = QWidget()
        filter_frame.setObjectName("filterBar")
        filter_layout = QGridLayout(filter_frame)
        filter_layout.setSpacing(8)
        filter_layout.setContentsMargins(12, 8, 12, 8)

        # 类型筛选
        filter_layout.addWidget(QLabel("类型："), 0, 0)
        self._type_combo = QComboBox()
        self._type_combo.addItem("全部", "")
        self._type_combo.addItem("支出", "expense")
        self._type_combo.addItem("收入", "income")
        self._type_combo.setFixedWidth(100)
        filter_layout.addWidget(self._type_combo, 0, 1)

        # 分类筛选
        filter_layout.addWidget(QLabel("分类："), 0, 2)
        self._cat_combo = QComboBox()
        self._cat_combo.addItem("全部分类", "")
        cats = list_categories()
        for cat in cats:
            label = "支出" if cat["type"] == "expense" else "收入"
            self._cat_combo.addItem(f"{cat['icon']} {cat['name']}（{label}）", cat["id"])
        self._cat_combo.setFixedWidth(160)
        filter_layout.addWidget(self._cat_combo, 0, 3)

        # 开始日期
        filter_layout.addWidget(QLabel("开始："), 1, 0)
        self._start_date = QDateEdit()
        self._start_date.setCalendarPopup(True)
        self._start_date.setDisplayFormat("yyyy-MM-dd")
        self._start_date.setDate(QDate.currentDate().addMonths(-1))
        self._start_date.setFixedWidth(130)
        filter_layout.addWidget(self._start_date, 1, 1)

        # 结束日期
        filter_layout.addWidget(QLabel("结束："), 1, 2)
        self._end_date = QDateEdit()
        self._end_date.setCalendarPopup(True)
        self._end_date.setDisplayFormat("yyyy-MM-dd")
        self._end_date.setDate(QDate.currentDate())
        self._end_date.setFixedWidth(130)
        filter_layout.addWidget(self._end_date, 1, 3)

        # 关键词搜索
        filter_layout.addWidget(QLabel("搜索："), 1, 4)
        self._keyword_input = QLineEdit()
        self._keyword_input.setPlaceholderText("备注关键词...")
        self._keyword_input.setFixedWidth(140)
        filter_layout.addWidget(self._keyword_input, 1, 5)

        # 按钮行
        btn_layout = QHBoxLayout()

        self._search_btn = QPushButton("🔍 查询")
        self._search_btn.clicked.connect(self._on_search)
        btn_layout.addWidget(self._search_btn)

        self._reset_btn = QPushButton("重置")
        self._reset_btn.setObjectName("secondaryBtn")
        self._reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(self._reset_btn)

        btn_layout.addStretch()

        self._add_expense_btn = QPushButton("➕ 新增支出")
        self._add_expense_btn.setObjectName("addBtn")
        self._add_expense_btn.clicked.connect(lambda: self._on_add("expense"))
        btn_layout.addWidget(self._add_expense_btn)

        self._add_income_btn = QPushButton("➕ 新增收入")
        self._add_income_btn.setObjectName("addBtn")
        self._add_income_btn.clicked.connect(lambda: self._on_add("income"))
        btn_layout.addWidget(self._add_income_btn)

        layout.addWidget(filter_frame)
        layout.addLayout(btn_layout)

        # ── 表格 ──
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["ID", "类型", "分类", "金额", "日期", "备注", "操作"]
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        # 列宽
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(6, 170)  # 操作列固定宽度

        layout.addWidget(self._table)

        # ── 分页 ──
        page_layout = QHBoxLayout()

        self._prev_btn = QPushButton("上一页")
        self._prev_btn.setObjectName("secondaryBtn")
        self._prev_btn.clicked.connect(self._on_prev_page)
        page_layout.addWidget(self._prev_btn)

        self._page_label = QLabel("")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_layout.addWidget(self._page_label)

        self._next_btn = QPushButton("下一页")
        self._next_btn.setObjectName("secondaryBtn")
        self._next_btn.clicked.connect(self._on_next_page)
        page_layout.addWidget(self._next_btn)

        page_layout.addStretch()

        self._count_label = QLabel("")
        page_layout.addWidget(self._count_label)

        layout.addLayout(page_layout)

    # ── 数据加载 ──

    def _get_filter_params(self) -> dict:
        """收集筛选参数。"""
        tx_type = self._type_combo.currentData()
        cat_id = self._cat_combo.currentData()
        start = self._start_date.date().toString("yyyy-MM-dd")
        end = self._end_date.date().toString("yyyy-MM-dd")
        keyword = self._keyword_input.text().strip() or None

        params = {
            "start_date": start,
            "end_date": end,
            "limit": self.PAGE_SIZE,
            "offset": self._current_offset,
        }
        if tx_type:
            params["type"] = tx_type
        if cat_id:
            params["category_id"] = cat_id
        if keyword:
            params["keyword"] = keyword
        return params

    def refresh(self) -> None:
        """刷新表格数据。"""
        params = self._get_filter_params()
        total = count_transactions(**{k: v for k, v in params.items() if k not in ("limit", "offset")})
        records = list_transactions(**params)

        self._table.setRowCount(len(records))

        for row_idx, tx in enumerate(records):
            # ID
            id_item = QTableWidgetItem(str(tx["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row_idx, 0, id_item)

            # 类型
            type_text = "收入" if tx["type"] == "income" else "支出"
            type_item = QTableWidgetItem(type_text)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if tx["type"] == "income":
                type_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                type_item.setForeground(Qt.GlobalColor.red)
            self._table.setItem(row_idx, 1, type_item)

            # 分类
            icon = tx.get("category_icon") or ""
            name = tx.get("category_name") or ""
            cat_item = QTableWidgetItem(f"{icon} {name}")
            cat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row_idx, 2, cat_item)

            # 金额
            amount_item = QTableWidgetItem(format_amount(tx["amount"]))
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if tx["type"] == "income":
                amount_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                amount_item.setForeground(Qt.GlobalColor.red)
            self._table.setItem(row_idx, 3, amount_item)

            # 日期
            date_item = QTableWidgetItem(tx["date"])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row_idx, 4, date_item)

            # 备注
            note_item = QTableWidgetItem(tx["note"] or "")
            self._table.setItem(row_idx, 5, note_item)

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(6, 0, 6, 0)
            btn_layout.setSpacing(8)

            edit_btn = QPushButton("编辑")
            edit_btn.setFixedSize(70, 28)
            edit_btn.setObjectName("secondaryBtn")
            edit_btn.setToolTip("编辑这条记录")
            edit_btn.clicked.connect(lambda checked, r=row_idx, tx_id=tx["id"]: self._on_edit(tx_id))
            btn_layout.addWidget(edit_btn)

            del_btn = QPushButton("删除")
            del_btn.setFixedSize(70, 28)
            del_btn.setObjectName("dangerBtn")
            del_btn.setToolTip("删除这条记录")
            del_btn.clicked.connect(lambda checked, tx_id=tx["id"]: self._on_delete(tx_id))
            btn_layout.addWidget(del_btn)

            self._table.setCellWidget(row_idx, 6, btn_widget)

        # 分页状态
        total_pages = max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        current_page = self._current_offset // self.PAGE_SIZE + 1
        self._page_label.setText(f"第 {current_page} / {total_pages} 页")
        self._count_label.setText(f"共 {total} 条记录")

        self._prev_btn.setEnabled(self._current_offset > 0)
        self._next_btn.setEnabled(self._current_offset + self.PAGE_SIZE < total)

        # 行高
        self._table.resizeRowsToContents()

    # ── 事件处理 ──

    def _on_search(self) -> None:
        """查询按钮。"""
        self._current_offset = 0
        self.refresh()

    def _on_reset(self) -> None:
        """重置筛选条件。"""
        self._type_combo.setCurrentIndex(0)
        self._cat_combo.setCurrentIndex(0)
        self._start_date.setDate(QDate.currentDate().addMonths(-1))
        self._end_date.setDate(QDate.currentDate())
        self._keyword_input.clear()
        self._current_offset = 0
        self.refresh()

    def _on_add(self, tx_type: str) -> None:
        """新增记录。"""
        dialog = AddRecordDialog(self, default_type=tx_type)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_edit(self, tx_id: int) -> None:
        """编辑记录。"""
        dialog = AddRecordDialog(self, tx_id=tx_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_delete(self, tx_id: int) -> None:
        """删除记录（需确认）。"""
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这条记录吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_transaction(tx_id)
            self.refresh()

    def _on_prev_page(self) -> None:
        self._current_offset = max(0, self._current_offset - self.PAGE_SIZE)
        self.refresh()

    def _on_next_page(self) -> None:
        self._current_offset += self.PAGE_SIZE
        self.refresh()
