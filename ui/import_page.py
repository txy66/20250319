"""
ui/import_page.py - 银行账单导入页面

功能：
- 选择 Excel/CSV 账单文件
- 配置列映射（指定源文件各列对应的数据字段）
- 预览解析结果
- 执行导入并显示结果
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QGroupBox, QProgressBar,
)
from PyQt6.QtCore import Qt

from core.importer import (
    parse_file, import_records, ColumnMapping,
    detect_file_type,
)
from core.category import list_categories


class ImportPage(QWidget):
    """银行账单导入页面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("importPage")

        self._file_path: str = ""
        self._preview_records: list[dict] = []
        self._all_rows: list[tuple] = []  # 用于获取表头列名

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 标题 ──
        title = QLabel("📁 导入账单")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # ── 文件选择区 ──
        file_group = QGroupBox("选择文件")
        file_group.setObjectName("card")
        file_layout = QHBoxLayout(file_group)
        file_layout.setContentsMargins(12, 8, 12, 8)

        self._file_label = QLabel("未选择文件")
        self._file_label.setStyleSheet("color: #94a3b8;")
        file_layout.addWidget(self._file_label, 1)

        browse_btn = QPushButton("选择文件")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(browse_btn)

        layout.addWidget(file_group)

        # ── 列映射配置 ──
        mapping_group = QGroupBox("列映射配置")
        mapping_group.setObjectName("card")
        mapping_layout = QGridLayout(mapping_group)
        mapping_layout.setSpacing(8)
        mapping_layout.setContentsMargins(12, 8, 12, 8)

        self._col_inputs: dict[str, QLineEdit] = {}

        fields = [
            ("日期列", "date_col", "交易日期对应的列名或序号"),
            ("金额列", "amount_col", "金额对应的列名或序号"),
            ("备注列", "note_col", "备注/摘要列（可选）"),
            ("分类列", "category_col", "分类/商户列（可选）"),
            ("类型列", "type_col", "收支类型列（可选）"),
        ]

        for i, (label, key, tip) in enumerate(fields):
            mapping_layout.addWidget(QLabel(f"{label}："), i, 0)
            edit = QLineEdit()
            edit.setPlaceholderText(tip)
            edit.setMaximumWidth(300)
            mapping_layout.addWidget(edit, i, 1)

        layout.addWidget(mapping_group)

        # ── 操作按钮 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        preview_btn = QPushButton("👁 预览")
        preview_btn.setObjectName("secondaryBtn")
        preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        preview_btn.clicked.connect(self._on_preview)
        btn_row.addWidget(preview_btn)

        self._import_btn = QPushButton("📥 开始导入")
        self._import_btn.setObjectName("addBtn")
        self._import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._import_btn.setEnabled(False)
        self._import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(self._import_btn)

        layout.addLayout(btn_row)

        # ── 结果区 ──
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        layout.addWidget(self._result_label)

        # ── 预览表格 ──
        self._preview_table = QTableWidget()
        self._preview_table.setColumnCount(5)
        self._preview_table.setHorizontalHeaderLabels(["日期", "类型", "金额", "分类", "备注"])
        self._preview_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._preview_table.setColumnWidth(0, 100)
        self._preview_table.setColumnWidth(1, 60)
        self._preview_table.setColumnWidth(2, 100)
        self._preview_table.setColumnWidth(3, 80)
        self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.verticalHeader().setVisible(False)
        self._preview_table.setMaximumHeight(300)
        layout.addWidget(self._preview_table)

        layout.addStretch()

    def refresh(self) -> None:
        """刷新页面（切换到此页面时调用）。"""
        pass

    # ─── 交互处理 ──────────────────────────────────────────────────────────

    def _on_browse(self) -> None:
        """选择账单文件。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择账单文件", "",
            "Excel 文件 (*.xlsx);;CSV 文件 (*.csv);;所有文件 (*)",
        )
        if not file_path:
            return

        self._file_path = file_path
        file_name = Path(file_path).name
        self._file_label.setText(f"📄 {file_name}")
        self._file_label.setStyleSheet("color: #1e293b; font-weight: bold;")

        # 读取表头行，填充列名提示
        try:
            ftype = detect_file_type(file_path)
            if ftype.value == "xlsx":
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                ws = wb.active
                header_row = next(ws.iter_rows(values_only=True), ())
                wb.close()
            else:
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    import csv
                    reader = csv.reader(f)
                    header_row = next(reader, ())

            # 自动填入表头列名提示
            tips = {
                "date_col": self._guess_col(header_row, ["日期", "交易时间", "交易日期", "记账日期", "时间"]),
                "amount_col": self._guess_col(header_row, ["金额", "交易金额", "支出", "收入", "发生额", "交易额"]),
                "note_col": self._guess_col(header_row, ["摘要", "备注", "交易摘要", "描述", "用途", "商户", "对方"]),
                "category_col": self._guess_col(header_row, ["分类", "类别", "商户分类", "科目"]),
                "type_col": self._guess_col(header_row, ["类型", "收支", "交易类型", "收/支"]),
            }
            for key, val in tips.items():
                edit = self._col_inputs.get(key)
                if edit and not edit.text():
                    edit.setPlaceholderText(f"{val}（当前: 自动检测到列名）")
                    if val:
                        edit.setText(val)

        except Exception as e:
            self._result_label.setText(f"⚠️ 读取文件头失败：{e}")
            self._result_label.setStyleSheet("color: #ef4444;")

    def _on_preview(self) -> None:
        """预览解析结果。"""
        if not self._file_path:
            QMessageBox.warning(self, "提示", "请先选择文件")
            return

        mapping = self._get_mapping()
        if not mapping.date_col or not mapping.amount_col:
            QMessageBox.warning(self, "提示", "请至少填写日期列和金额列")
            return

        try:
            records = parse_file(self._file_path, mapping)
            self._preview_records = records

            self._preview_table.setRowCount(len(records))
            cats = {c["id"]: c for c in list_categories()}

            for row, rec in enumerate(records):
                self._preview_table.setItem(row, 0, QTableWidgetItem(rec.get("date", "")))

                type_text = "收入" if rec.get("type") == "income" else "支出"
                type_item = QTableWidgetItem(type_text)
                type_item.setForeground(Qt.GlobalColor.green if type_text == "收入" else Qt.GlobalColor.red)
                self._preview_table.setItem(row, 1, type_item)

                amount = rec.get("amount", 0)
                self._preview_table.setItem(row, 2, QTableWidgetItem(f"{amount:.2f}"))

                cat = cats.get(rec.get("category_id", 0))
                cat_name = f"{cat['icon']} {cat['name']}" if cat else "未知"
                self._preview_table.setItem(row, 3, QTableWidgetItem(cat_name))

                self._preview_table.setItem(row, 4, QTableWidgetItem(rec.get("note", "")))

                self._preview_table.setRowHeight(row, 36)

            self._import_btn.setEnabled(len(records) > 0)
            self._result_label.setText(f"✅ 解析成功，共 {len(records)} 条记录，预览前 100 条")
            self._result_label.setStyleSheet("color: #10b981;")

        except Exception as e:
            self._result_label.setText(f"❌ 解析失败：{e}")
            self._result_label.setStyleSheet("color: #ef4444;")
            self._import_btn.setEnabled(False)

    def _on_import(self) -> None:
        """执行导入。"""
        if not self._preview_records:
            QMessageBox.warning(self, "提示", "没有可导入的记录")
            return

        reply = QMessageBox.question(
            self, "确认导入",
            f"即将导入 {len(self._preview_records)} 条记录，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        result = import_records(self._preview_records)

        msg = (
            f"导入完成：\n"
            f"  总计：{result.total_rows} 条\n"
            f"  成功：{result.imported} 条\n"
            f"  跳过：{result.skipped} 条"
        )
        if result.errors:
            error_lines = [f"  行 {e.row}: {e.message}" for e in result.errors[:10]]
            if len(result.errors) > 10:
                error_lines.append(f"  ... 还有 {len(result.errors) - 10} 条错误")
            msg += "\n\n错误详情：\n" + "\n".join(error_lines)

        QMessageBox.information(self, "导入结果", msg)

        # 清空预览
        self._preview_records = []
        self._preview_table.setRowCount(0)
        self._import_btn.setEnabled(False)
        self._result_label.setText(f"✅ 已成功导入 {result.imported} 条记录")
        self._result_label.setStyleSheet("color: #10b981; font-weight: bold;")

    # ─── 辅助方法 ──────────────────────────────────────────────────────────

    def _get_mapping(self) -> ColumnMapping:
        """从 UI 输入获取列映射配置。"""
        return ColumnMapping(
            date_col=self._col_inputs.get("date_col", QLineEdit()).text().strip(),
            amount_col=self._col_inputs.get("amount_col", QLineEdit()).text().strip(),
            note_col=self._col_inputs.get("note_col", QLineEdit()).text().strip(),
            category_col=self._col_inputs.get("category_col", QLineEdit()).text().strip(),
            type_col=self._col_inputs.get("type_col", QLineEdit()).text().strip(),
        )

    @staticmethod
    def _guess_col(header_row: tuple, keywords: list[str]) -> str:
        """从表头行中猜测最匹配的列名。"""
        if not header_row:
            return ""
        for cell in header_row:
            if cell is None:
                continue
            cell_str = str(cell).strip()
            for kw in keywords:
                if kw in cell_str:
                    return cell_str
        return ""
