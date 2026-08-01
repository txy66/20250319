"""
ui/categories.py - 分类管理页面

功能：
- 以表格展示所有分类（按类型分组）
- 支持新增、编辑、删除分类
- 内置默认分类标记保护，不允许删除
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog,
    QLineEdit, QComboBox,
)
from PyQt6.QtCore import Qt

from core.category import list_categories, create_category, update_category, delete_category


class CategoryDialog(QDialog):
    """新增/编辑分类对话框。"""

    def __init__(self, parent=None, *, cat_id: int = None, cat_name: str = "",
                 cat_type: str = "expense", cat_icon: str = "", is_default: bool = False):
        super().__init__(parent)
        self._cat_id = cat_id
        self.setWindowTitle("编辑分类" if cat_id else "新增分类")
        self.setMinimumWidth(360)
        self._is_default = is_default

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # 类型选择（仅新增时可改）
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("类型："))
        self._type_combo = QComboBox()
        self._type_combo.addItem("支出", "expense")
        self._type_combo.addItem("收入", "income")
        idx = 0 if cat_type == "expense" else 1
        self._type_combo.setCurrentIndex(idx)
        self._type_combo.setEnabled(cat_id is None)  # 编辑时锁定类型
        type_row.addWidget(self._type_combo, 1)
        layout.addLayout(type_row)

        # 分类名称
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("名称："))
        self._name_edit = QLineEdit(cat_name)
        self._name_edit.setPlaceholderText("输入分类名称")
        name_row.addWidget(self._name_edit, 1)
        layout.addLayout(name_row)

        # 图标
        icon_row = QHBoxLayout()
        icon_row.addWidget(QLabel("图标："))
        self._icon_edit = QLineEdit(cat_icon)
        self._icon_edit.setPlaceholderText("输入 emoji 图标，如 🍜")
        self._icon_edit.setMaxLength(4)
        icon_row.addWidget(self._icon_edit, 1)
        layout.addLayout(icon_row)

        # 默认分类提示
        if is_default:
            tip = QLabel("⚠️ 此为内置默认分类，仅可修改图标")
            tip.setStyleSheet("color: #f59e0b; font-size: 12px;")
            layout.addWidget(tip)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入分类名称")
            return

        icon = self._icon_edit.text().strip()
        cat_type = self._type_combo.currentData()

        try:
            if self._cat_id:
                update_category(self._cat_id, name=name, icon=icon)
            else:
                create_category(name=name, type=cat_type, icon=icon)
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败：{e}")


class CategoriesPage(QWidget):
    """分类管理页面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("categoriesPage")
        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 标题 ──
        title = QLabel("🏷️ 分类管理")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # ── 工具栏 ──
        toolbar = QHBoxLayout()
        toolbar.addStretch()

        add_btn = QPushButton("➕ 新增分类")
        add_btn.setObjectName("addBtn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        # ── 分类表格 ──
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["图标", "名称", "类型", "操作"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 80)
        self._table.setColumnWidth(2, 100)
        self._table.setColumnWidth(3, 170)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table, 1)

    def refresh(self) -> None:
        """刷新分类列表。"""
        categories = list_categories()
        self._table.setRowCount(len(categories))

        for row, cat in enumerate(categories):
            # 图标
            icon_item = QTableWidgetItem(cat.get("icon", "") or "")
            icon_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, icon_item)

            # 名称
            name_item = QTableWidgetItem(cat["name"])
            if cat.get("is_default"):
                name_item.setText(f"{cat['name']}  (默认)")
            self._table.setItem(row, 1, name_item)

            # 类型
            type_text = "支出" if cat["type"] == "expense" else "收入"
            type_item = QTableWidgetItem(type_text)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if cat["type"] == "income":
                type_item.setForeground(Qt.GlobalColor.green)
            else:
                type_item.setForeground(Qt.GlobalColor.red)
            self._table.setItem(row, 2, type_item)

            # 操作按钮：编辑 + 删除
            btn_widget = QWidget()
            btn_widget.setStyleSheet("background: transparent; border: none;")
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(8)

            edit_btn = QPushButton("编辑")
            edit_btn.setFixedSize(64, 30)
            edit_btn.setStyleSheet(
                "QPushButton {"
                "  background-color: #ffffff;"
                "  color: #374151;"
                "  border: 1px solid #d1d5db;"
                "  border-radius: 6px;"
                "  padding: 0px;"
                "  font-size: 13px;"
                "  font-weight: bold;"
                "}"
                "QPushButton:hover {"
                "  background-color: #f9fafb;"
                "  border-color: #9ca3af;"
                "}"
                "QPushButton:pressed {"
                "  background-color: #f3f4f6;"
                "}"
            )
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(
                lambda checked, cid=cat["id"], cn=cat["name"],
                ct=cat["type"], ci=cat.get("icon", ""),
                cd=bool(cat.get("is_default")): self._on_edit(cid, cn, ct, ci, cd)
            )
            btn_layout.addWidget(edit_btn)

            del_btn = QPushButton("删除")
            del_btn.setFixedSize(64, 30)
            del_btn.setStyleSheet(
                "QPushButton {"
                "  background-color: #ef4444;"
                "  color: #ffffff;"
                "  border: none;"
                "  border-radius: 6px;"
                "  padding: 0px;"
                "  font-size: 13px;"
                "  font-weight: bold;"
                "}"
                "QPushButton:hover {"
                "  background-color: #dc2626;"
                "}"
                "QPushButton:pressed {"
                "  background-color: #b91c1c;"
                "}"
            )
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(
                lambda checked, cid=cat["id"], cn=cat["name"]: self._on_delete(cid, cn)
            )
            btn_layout.addWidget(del_btn)

            self._table.setCellWidget(row, 3, btn_widget)

            # 行高
            self._table.setRowHeight(row, 44)

    def _on_add(self) -> None:
        """新增分类。"""
        dlg = CategoryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_edit(self, cat_id: int, name: str, cat_type: str, icon: str, is_default: bool) -> None:
        """编辑分类。"""
        dlg = CategoryDialog(
            self, cat_id=cat_id, cat_name=name,
            cat_type=cat_type, cat_icon=icon, is_default=is_default,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_delete(self, cat_id: int, name: str) -> None:
        """删除分类。"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除分类「{name}」吗？\n\n"
            f"如果该分类下有交易记录，将无法删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                delete_category(cat_id)
                self.refresh()
            except ValueError as e:
                QMessageBox.warning(self, "无法删除", str(e))
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败：{e}")
