"""
ui/add_record.py - 新增/编辑记录对话框

支持新增和编辑两种模式。
编辑模式下预填充已有数据，保存时执行更新操作。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QComboBox,
    QDateEdit, QTextEdit, QRadioButton, QButtonGroup,
    QDialogButtonBox, QMessageBox,
)
from PyQt6.QtCore import Qt, QDate

from core.transaction import create_transaction, update_transaction, get_transaction
from core.category import list_categories
from utils.date_helper import today_str


class AddRecordDialog(QDialog):
    """新增/编辑收支记录对话框。"""

    def __init__(
        self,
        parent=None,
        *,
        tx_id: Optional[int] = None,
        default_type: str = "expense",
    ):
        super().__init__(parent)
        self.tx_id = tx_id
        self._editing = tx_id is not None
        self._init_ui(default_type)

        if self._editing:
            self.setWindowTitle("编辑记录")
            self._load_data()
        else:
            self.setWindowTitle("新增记录")

    def _init_ui(self, default_type: str) -> None:
        """构建界面。"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 16)

        # ── 类型选择 ──
        type_layout = QHBoxLayout()
        type_label = QLabel("类型：")
        type_label.setFixedWidth(60)

        self._radio_expense = QRadioButton("支出")
        self._radio_income = QRadioButton("收入")
        self._type_group = QButtonGroup(self)
        self._type_group.addButton(self._radio_expense, 0)
        self._type_group.addButton(self._radio_income, 1)

        if default_type == "income":
            self._radio_income.setChecked(True)
        else:
            self._radio_expense.setChecked(True)

        type_layout.addWidget(type_label)
        type_layout.addWidget(self._radio_expense)
        type_layout.addWidget(self._radio_income)
        type_layout.addStretch()

        self._type_group.idClicked.connect(self._on_type_changed)

        # ── 表单 ──
        form = QFormLayout()
        form.setSpacing(10)
        form.setHorizontalSpacing(16)

        # 金额
        self._amount_input = QDoubleSpinBox()
        self._amount_input.setPrefix("¥")
        self._amount_input.setRange(0.01, 9999999.99)
        self._amount_input.setDecimals(2)
        self._amount_input.setSingleStep(10.0)
        form.addRow("金额 *：", self._amount_input)

        # 分类
        self._category_combo = QComboBox()
        form.addRow("分类 *：", self._category_combo)

        # 日期
        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        self._date_edit.setDate(QDate.fromString(today_str(), "yyyy-MM-dd"))
        form.addRow("日期 *：", self._date_edit)

        # 备注
        self._note_input = QLineEdit()
        self._note_input.setPlaceholderText("可选备注...")
        form.addRow("备注：", self._note_input)

        layout.addLayout(type_layout)
        layout.addLayout(form)

        # ── 按钮 ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, alignment=Qt.AlignmentFlag.AlignRight)

        # 初始化分类列表
        self._on_type_changed(self._type_group.checkedId())

        self.setFixedSize(420, 320)

    # ── 事件处理 ──

    def _on_type_changed(self, button_id: int) -> None:
        """类型切换时刷新分类下拉列表。"""
        tx_type = "income" if button_id == 1 else "expense"
        cats = list_categories(type=tx_type)
        self._category_combo.clear()
        for cat in cats:
            self._category_combo.addItem(f"{cat['icon']} {cat['name']}", cat["id"])

    def _load_data(self) -> None:
        """编辑模式：加载已有数据填充表单。"""
        tx = get_transaction(self.tx_id)
        if not tx:
            QMessageBox.critical(self, "错误", "记录不存在")
            self.reject()
            return

        # 类型
        if tx["type"] == "income":
            self._radio_income.setChecked(True)
        else:
            self._radio_expense.setChecked(True)

        # 金额
        self._amount_input.setValue(tx["amount"])

        # 分类（等类型刷新后再设置）
        cats = list_categories(type=tx["type"])
        self._category_combo.clear()
        for cat in cats:
            self._category_combo.addItem(f"{cat['icon']} {cat['name']}", cat["id"])
        # 找到对应分类
        for i in range(self._category_combo.count()):
            if self._category_combo.itemData(i) == tx["category_id"]:
                self._category_combo.setCurrentIndex(i)
                break

        # 日期
        self._date_edit.setDate(QDate.fromString(tx["date"], "yyyy-MM-dd"))

        # 备注
        self._note_input.setText(tx["note"] or "")

    def _on_save(self) -> None:
        """保存按钮处理。"""
        # 验证
        amount = self._amount_input.value()
        if amount <= 0:
            QMessageBox.warning(self, "提示", "请输入有效金额")
            return

        category_id = self._category_combo.currentData()
        if category_id is None:
            QMessageBox.warning(self, "提示", "请选择分类")
            return

        tx_type = "income" if self._type_group.checkedId() == 1 else "expense"
        tx_date = self._date_edit.date().toString("yyyy-MM-dd")
        note = self._note_input.text().strip()

        try:
            if self._editing:
                update_transaction(
                    self.tx_id,
                    type=tx_type,
                    amount=amount,
                    category_id=category_id,
                    date=tx_date,
                    note=note,
                )
            else:
                create_transaction(
                    type=tx_type,
                    amount=amount,
                    category_id=category_id,
                    date=tx_date,
                    note=note,
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
