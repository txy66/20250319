"""
ui/ai_analysis.py - AI 智能分析页面

功能：
- 配置 DeepSeek API Key
- 选择分析时间段
- 调用 AI 生成省钱建议
- 以 Markdown 渲染展示分析结果
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QLineEdit,
    QTextBrowser, QMessageBox, QGroupBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core.ai_analyzer import (
    analyze_savings, gather_savings_data,
    load_api_key, save_api_key,
    load_provider, save_provider,
    load_model, save_model,
    PROVIDERS,
)


class AnalysisWorker(QThread):
    """后台线程调用 AI 分析，避免阻塞 UI。"""

    finished = pyqtSignal(str)   # 成功时返回结果文本
    error = pyqtSignal(str)      # 失败时返回错误信息

    def __init__(self, api_key: str, data: dict):
        super().__init__()
        self._api_key = api_key
        self._data = data

    def run(self) -> None:
        try:
            result = analyze_savings(self._api_key, self._data)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AIAnalysisPage(QWidget):
    """AI 智能分析页面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aiAnalysisPage")

        self._worker: AnalysisWorker | None = None

        self._init_ui()
        self._load_config()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 标题 ──
        title = QLabel("🤖 AI 智能分析")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # ── API 配置 ──
        key_group = QGroupBox("API 配置")
        key_group.setObjectName("card")
        key_layout = QVBoxLayout(key_group)
        key_layout.setContentsMargins(12, 10, 12, 10)
        key_layout.setSpacing(8)

        # 第一行：服务商 + 模型
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("服务商："))
        self._provider_combo = QComboBox()
        for pid, p in PROVIDERS.items():
            self._provider_combo.addItem(p["name"], pid)
        # 选中已保存的服务商
        saved_provider = load_provider()
        for i in range(self._provider_combo.count()):
            if self._provider_combo.itemData(i) == saved_provider:
                self._provider_combo.setCurrentIndex(i)
                break
        self._provider_combo.setFixedWidth(120)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_row.addWidget(self._provider_combo)

        provider_row.addWidget(QLabel("模型："))
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(200)
        self._refresh_model_combo()
        provider_row.addWidget(self._model_combo, 1)
        key_layout.addLayout(provider_row)

        # 第二行：API Key
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API Key："))
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText("输入 API Key（如 sk-xxxx）")
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        key_row.addWidget(self._key_edit, 1)

        # 显示/隐藏按钮
        self._toggle_key_btn = QPushButton("👁")
        self._toggle_key_btn.setFixedSize(36, 32)
        self._toggle_key_btn.setObjectName("secondaryBtn")
        self._toggle_key_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_key_btn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self._toggle_key_btn)

        save_key_btn = QPushButton("保存")
        save_key_btn.setFixedWidth(60)
        save_key_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_key_btn.clicked.connect(self._save_config)
        key_row.addWidget(save_key_btn)
        key_layout.addLayout(key_row)

        layout.addWidget(key_group)

        # ── 分析参数 ──
        param_group = QGroupBox("分析参数")
        param_group.setObjectName("card")
        param_layout = QHBoxLayout(param_group)
        param_layout.setContentsMargins(12, 8, 12, 8)

        param_layout.addWidget(QLabel("分析时段："))
        self._period_combo = QComboBox()
        self._period_combo.addItem("最近 1 个月", 1)
        self._period_combo.addItem("最近 3 个月", 3)
        self._period_combo.addItem("最近 6 个月", 6)
        self._period_combo.addItem("最近 12 个月", 12)
        self._period_combo.setCurrentIndex(1)  # 默认 3 个月
        self._period_combo.setFixedWidth(160)
        param_layout.addWidget(self._period_combo)

        param_layout.addStretch()

        self._analyze_btn = QPushButton("🔍 开始分析")
        self._analyze_btn.setObjectName("addBtn")
        self._analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._analyze_btn.clicked.connect(self._on_analyze)
        param_layout.addWidget(self._analyze_btn)

        layout.addWidget(param_group)

        # ── 状态提示 ──
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # ── 结果展示区 ──
        self._result_browser = QTextBrowser()
        self._result_browser.setObjectName("aiResultBrowser")
        self._result_browser.setOpenExternalLinks(True)
        self._result_browser.setPlaceholderText(
            "AI 分析结果将在此展示...\n\n"
            "💡 首次使用请先配置 API Key\n"
            "支持：硅基流动 / DeepSeek 官方 / OpenAI"
        )
        layout.addWidget(self._result_browser, 1)

        # 模型切换时自动保存
        self._model_combo.currentIndexChanged.connect(
            lambda: save_model(self._model_combo.currentData()) if self._model_combo.currentData() else None
        )

    def refresh(self) -> None:
        """刷新页面。"""
        pass

    # ─── 交互处理 ──────────────────────────────────────────────────────────

    def _load_config(self) -> None:
        """加载已保存的 API Key。"""
        key = load_api_key()
        if key:
            self._key_edit.setText(key)

    def _refresh_model_combo(self) -> None:
        """根据当前选中的服务商刷新模型下拉框。"""
        pid = self._provider_combo.currentData()
        p = PROVIDERS.get(pid, {})
        models = p.get("models", [])
        saved_model = load_model()

        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        for m in models:
            self._model_combo.addItem(m, m)
        # 选中已保存的模型（若属于该服务商），否则选第一个
        idx = 0
        for i in range(self._model_combo.count()):
            if self._model_combo.itemData(i) == saved_model:
                idx = i
                break
        self._model_combo.setCurrentIndex(idx)
        self._model_combo.blockSignals(False)

    def _on_provider_changed(self) -> None:
        """切换服务商时，刷新模型列表并保存。"""
        pid = self._provider_combo.currentData()
        save_provider(pid)
        self._refresh_model_combo()
        # 同步保存当前模型
        if self._model_combo.currentData():
            save_model(self._model_combo.currentData())

    def _save_config(self) -> None:
        """保存 API Key + 服务商 + 模型。"""
        key = self._key_edit.text().strip()
        if key:
            save_api_key(key)
        # 保存服务商和模型
        pid = self._provider_combo.currentData()
        if pid:
            save_provider(pid)
        model = self._model_combo.currentData()
        if model:
            save_model(model)

        if key:
            provider_name = PROVIDERS.get(pid, {}).get("name", pid)
            self._status_label.setText(f"✅ 配置已保存（{provider_name} · {model}）")
            self._status_label.setStyleSheet("color: #10b981;")
        else:
            self._status_label.setText("⚠️ 请输入 API Key")
            self._status_label.setStyleSheet("color: #f59e0b;")

    def _toggle_key_visibility(self) -> None:
        """切换 API Key 显示/隐藏。"""
        if self._key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self._key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_key_btn.setText("🔒")
        else:
            self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_key_btn.setText("👁")

    def _on_analyze(self) -> None:
        """开始 AI 分析。"""
        # 检查 API Key
        api_key = self._key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "提示", "请先配置 DeepSeek API Key")
            self._key_edit.setFocus()
            return

        # 保存 key
        save_api_key(api_key)

        # 获取分析时段
        months = self._period_combo.currentData()

        # 在主线程中先聚合数据（避免子线程跨线程访问 SQLite）
        try:
            data = gather_savings_data(months)
        except Exception as e:
            QMessageBox.critical(self, "数据获取失败", f"聚合消费数据失败：{e}")
            return

        # 禁用按钮，显示加载状态
        self._analyze_btn.setEnabled(False)
        self._analyze_btn.setText("⏳ 分析中...")
        self._status_label.setText("🤖 正在分析您的消费数据，请稍候...")
        self._status_label.setStyleSheet("color: #3b82f6;")
        self._result_browser.setPlainText("分析中，请稍候...\n\n")

        # 启动后台线程
        self._worker = AnalysisWorker(api_key, data)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.start()

    def _on_analysis_done(self, result: str) -> None:
        """分析完成。"""
        self._analyze_btn.setEnabled(True)
        self._analyze_btn.setText("🔍 开始分析")

        self._result_browser.setMarkdown(result)
        self._status_label.setText("✅ 分析完成")
        self._status_label.setStyleSheet("color: #10b981;")

    def _on_analysis_error(self, error_msg: str) -> None:
        """分析失败。"""
        self._analyze_btn.setEnabled(True)
        self._analyze_btn.setText("🔍 开始分析")

        self._result_browser.setPlainText(f"❌ 分析失败\n\n{error_msg}")
        self._status_label.setText(f"❌ 分析失败：{error_msg[:50]}")
        self._status_label.setStyleSheet("color: #ef4444;")
