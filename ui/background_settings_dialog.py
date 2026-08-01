"""
ui/background_settings_dialog.py - 背景设置对话框

功能：
- 4 张内置背景的缩略图选择（带单选按钮）
- 透明度滑块（0~100，实时显示百分比）
- 启用开关（关闭 = 恢复默认纯色背景）
- 实时预览（用户调整任何控件，立即看到处理后的效果）
- 应用 / 取消（只有按"应用"才写入配置）
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QRadioButton, QSlider, QCheckBox, QButtonGroup,
    QDialogButtonBox, QFrame, QSizePolicy,
)

from utils.background_manager import (
    BACKGROUND_PRESETS,
    get_background_manager,
    get_preset,
    get_source_pixmap,
    make_thumbnail,
    process_background,
)


class _ThumbCard(QFrame):
    """
    单个缩略图卡片：缩略图 + 名称 + 单选按钮。
    整体可点击切换（点击缩略图区域即选中）。
    """

    def __init__(
        self,
        preset_id: str,
        display_name: str,
        thumbnail: QPixmap,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._preset_id = preset_id
        self.setObjectName("bgThumbCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(180, 150)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # 缩略图（带选中边框效果）
        self._thumb = QLabel()
        self._thumb.setPixmap(thumbnail)
        self._thumb.setFixedSize(164, 96)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setScaledContents(False)
        layout.addWidget(self._thumb, alignment=Qt.AlignmentFlag.AlignCenter)

        # 单选按钮 + 名称（用 QHBox 让单选按钮 + 文字对齐）
        bottom = QHBoxLayout()
        bottom.setSpacing(4)
        bottom.setContentsMargins(0, 0, 0, 0)

        self._radio = QRadioButton(display_name)
        self._radio.setObjectName("bgThumbRadio")
        self._radio.setProperty("preset_id", preset_id)
        bottom.addWidget(self._radio)
        bottom.addStretch()

        layout.addLayout(bottom)

    @property
    def preset_id(self) -> str:
        return self._preset_id

    @property
    def radio(self) -> QRadioButton:
        return self._radio

    def set_selected(self, selected: bool) -> None:
        """更新视觉选中状态。"""
        self._radio.setChecked(selected)
        # 通过 dynamic property 切换样式
        self.setProperty("selected", "true" if selected else "false")
        # 触发样式重新解析
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        """点击卡片任意区域都切换到该预设。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._radio.setChecked(True)
            # 同时发出 toggled 信号让外部处理
            self._radio.toggled.emit(True)
        super().mousePressEvent(event)


class BackgroundSettingsDialog(QDialog):
    """背景设置对话框。"""

    THUMB_SIZE = QSize(164, 96)
    PREVIEW_SIZE = QSize(640, 360)  # 预览区域大小（16:9）

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🎨 背景设置")
        self.setMinimumSize(760, 620)
        self.setModal(True)

        self._manager = get_background_manager()
        self._initial_config = self._manager.config  # 保存进入时的配置，用于取消时恢复

        self._thumb_cards: dict[str, _ThumbCard] = {}
        self._radio_group = QButtonGroup(self)
        self._radio_group.setExclusive(True)

        self._build_ui()
        self._load_initial_values()
        self._update_preview()

    # ── UI 构建 ──

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        # ── 标题说明 ──
        title = QLabel("🎨 自定义背景")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        hint = QLabel("选择背景图、调节透明度，并实时预览效果。关闭开关后恢复默认纯色背景。")
        hint.setStyleSheet("color: #64748b; font-size: 12px;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # ── 缩略图选择区 ──
        thumbs_label = QLabel("背景图片")
        thumbs_label.setObjectName("fieldLabel")
        root.addWidget(thumbs_label)

        thumbs_row = QHBoxLayout()
        thumbs_row.setSpacing(12)
        thumbs_row.setContentsMargins(0, 0, 0, 0)

        for preset in BACKGROUND_PRESETS:
            source = get_source_pixmap(preset.id)
            if source is None:
                continue

            thumb = make_thumbnail(source, self.THUMB_SIZE)
            card = _ThumbCard(preset.id, preset.name, thumb, parent=self)
            self._radio_group.addButton(card.radio)
            card.radio.toggled.connect(self._on_preset_changed)
            self._thumb_cards[preset.id] = card
            thumbs_row.addWidget(card)

        thumbs_row.addStretch()
        root.addLayout(thumbs_row)

        # ── 透明度滑块 ──
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(8)

        opacity_label = QLabel("背景透明度")
        opacity_label.setObjectName("fieldLabel")
        opacity_label.setFixedWidth(80)
        opacity_row.addWidget(opacity_label)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(5)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setTickInterval(10)
        self._slider.setMinimumWidth(360)
        self._slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self._slider, 1)

        self._opacity_value = QLabel("35%")
        self._opacity_value.setObjectName("opacityValue")
        self._opacity_value.setFixedWidth(50)
        self._opacity_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        opacity_row.addWidget(self._opacity_value)

        root.addLayout(opacity_row)

        # ── 启用开关 ──
        switch_row = QHBoxLayout()
        self._enable_check = QCheckBox("启用自定义背景（关闭后恢复默认纯色背景）")
        self._enable_check.setChecked(False)
        self._enable_check.stateChanged.connect(self._on_enable_changed)
        switch_row.addWidget(self._enable_check)
        switch_row.addStretch()
        root.addLayout(switch_row)

        # ── 分隔 ──
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #e2e8f0; background: #e2e8f0; max-height: 1px;")
        root.addWidget(separator)

        # ── 实时预览 ──
        preview_label = QLabel("实时预览（当前设置下的效果）")
        preview_label.setObjectName("fieldLabel")
        root.addWidget(preview_label)

        self._preview = QLabel()
        self._preview.setObjectName("bgPreview")
        self._preview.setFixedSize(self.PREVIEW_SIZE)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._preview.setStyleSheet(
            "background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px;"
        )
        preview_container = QHBoxLayout()
        preview_container.addStretch()
        preview_container.addWidget(self._preview)
        preview_container.addStretch()
        root.addLayout(preview_container)

        # ── 底部按钮 ──
        button_box = QDialogButtonBox()
        self._apply_btn = QPushButton("应用")
        self._apply_btn.setObjectName("primaryBtn")
        self._apply_btn.setDefault(True)
        self._apply_btn.clicked.connect(self._on_apply)
        button_box.addButton(self._apply_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setObjectName("secondaryBtn")
        self._cancel_btn.clicked.connect(self.reject)
        button_box.addButton(self._cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(button_box)
        root.addLayout(button_layout)

    # ── 初始值加载 ──

    def _load_initial_values(self) -> None:
        """从当前配置回填到 UI。"""
        cfg = self._initial_config

        # 选中对应的卡片
        card = self._thumb_cards.get(cfg.preset_id)
        if card:
            card.set_selected(True)
        else:
            # 回退到第一张
            first_card = next(iter(self._thumb_cards.values()), None)
            if first_card:
                first_card.set_selected(True)

        self._slider.setValue(cfg.opacity)
        self._opacity_value.setText(f"{cfg.opacity}%")
        self._enable_check.setChecked(cfg.enabled)

    # ── 控件事件 ──

    def _on_preset_changed(self, checked: bool) -> None:
        if not checked:
            return
        sender = self.sender()
        preset_id = sender.property("preset_id") if sender else None
        if not preset_id:
            return

        # 更新所有卡片的视觉选中状态
        for pid, card in self._thumb_cards.items():
            card.set_selected(pid == preset_id)

        self._update_preview()

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_value.setText(f"{value}%")
        self._update_preview()

    def _on_enable_changed(self, state: int) -> None:
        # 开关变化时禁用/启用其他控件（视觉提示，但允许继续调节以预览）
        enabled = state == Qt.CheckState.Checked.value
        for card in self._thumb_cards.values():
            card.setEnabled(enabled)
        self._slider.setEnabled(enabled)
        self._update_preview()

    # ── 预览 ──

    def _update_preview(self) -> None:
        """根据当前 UI 状态生成预览图。"""
        # 关闭开关时显示一个标识
        if not self._enable_check.isChecked():
            placeholder = QPixmap(self.PREVIEW_SIZE)
            placeholder.fill(Qt.GlobalColor.transparent)
            from PyQt6.QtGui import QPainter, QColor, QFont
            painter = QPainter(placeholder)
            try:
                # 模拟默认纯色背景
                painter.fillRect(placeholder.rect(), QColor(245, 247, 250))
                painter.setPen(QColor(148, 163, 184))
                font = QFont()
                font.setPointSize(14)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(
                    placeholder.rect(),
                    Qt.AlignmentFlag.AlignCenter,
                    "背景已关闭\n（恢复默认纯色背景）",
                )
            finally:
                painter.end()
            self._preview.setPixmap(placeholder)
            return

        # 找到当前选中的预设
        current_preset_id = None
        for pid, card in self._thumb_cards.items():
            if card.radio.isChecked():
                current_preset_id = pid
                break
        if current_preset_id is None:
            current_preset_id = next(iter(self._thumb_cards.keys()), None)
        if current_preset_id is None:
            return

        source = get_source_pixmap(current_preset_id)
        if source is None:
            return

        processed = process_background(source, self.PREVIEW_SIZE, self._slider.value())
        self._preview.setPixmap(processed)

    # ── 应用 / 取消 ──

    def _on_apply(self) -> None:
        """把当前 UI 配置写入管理器（持久化），然后关闭对话框。"""
        current_preset_id = None
        for pid, card in self._thumb_cards.items():
            if card.radio.isChecked():
                current_preset_id = pid
                break

        if current_preset_id is None:
            # 兜底：未选中任何卡片时取消
            self.reject()
            return

        self._manager.update(
            enabled=self._enable_check.isChecked(),
            preset_id=current_preset_id,
            opacity=self._slider.value(),
        )
        self.accept()

    def reject(self) -> None:
        """取消时不做任何修改（已应用的也会保留，因为用户已经主动点击了应用）。"""
        super().reject()