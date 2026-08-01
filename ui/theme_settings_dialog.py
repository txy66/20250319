"""
ui/theme_settings_dialog.py — 主题与背景联合设置对话框

布局结构：
┌──────────────────────────────────────────────┐
│  🎨 外观设置                                  │
│  ┌─ 主题色彩 ────┬─ 背景图片 ────────────┐  │
│  │  6 个渐变色块   │  4 张缩略图           │  │
│  │  带选中光晕     │  透明度滑块 + 实时预览 │  │
│  └───────────────┴────────────────────────┘  │
│                  [取消] [应用]                 │
└──────────────────────────────────────────────┘

联动规则：
- 纯色主题与背景图片同时生效
- 图片背景位于底层，控件色彩由纯色主题控制
- 支持关闭图片背景，仅保留纯色主题
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen, QBrush
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QCheckBox, QDialogButtonBox,
    QFrame, QTabWidget, QWidget, QButtonGroup, QRadioButton,
)

from utils.theme_manager import THEMES, ThemeTokens, get_theme_manager
from utils.background_manager import (
    BACKGROUND_PRESETS, get_background_manager, get_preset,
    get_source_pixmap, make_thumbnail, process_background,
)


# ═══════════════════════════════════════════════════════════════════════
# 主题渐变色块卡片
# ═══════════════════════════════════════════════════════════════════════

class _ColorSwatch(QFrame):
    """主题色块卡片：4 阶渐变条 + 名称 + 描述。点击选中。"""

    clicked = pyqtSignal(object)  # 发射 self

    def __init__(self, theme: ThemeTokens, parent=None) -> None:
        super().__init__(parent)
        self._theme_id = theme.id
        self._theme = theme
        self.setObjectName("themeSwatchCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(200, 156)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        # ── 自绘渐变色条 ──
        self._bar = _GradientBar(theme, parent=self)
        self._bar.setFixedSize(180, 56)
        layout.addWidget(self._bar, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── 名称 ──
        name_label = QLabel(theme.name)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # ── 描述 ──
        desc_label = QLabel(theme.description)
        desc_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

    @property
    def theme_id(self) -> str:
        return self._theme_id

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        # 同时更新渐变条选中态
        self._bar.set_selected(selected)

    def mouseReleaseEvent(self, event) -> None:
        """整卡点击触发选中。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self)
        super().mouseReleaseEvent(event)


class _GradientBar(QWidget):
    """自绘渐变色条：展示主题色彩从浅到深的变化。"""

    def __init__(self, theme: ThemeTokens, parent=None) -> None:
        super().__init__(parent)
        self._colors = [
            QColor(theme.primary_50),
            QColor(theme.primary_100),
            QColor(theme.primary_500),
            QColor(theme.primary_700),
        ]
        self._selected = False

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = 8  # 圆角

        # 渐变背景
        gradient = QLinearGradient(0, 0, w, 0)
        step = 1.0 / (len(self._colors) - 1)
        for i, c in enumerate(self._colors):
            gradient.setColorAt(i * step, c)

        path = painter.clipPath()  # placeholder
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, r, r)

        # 选中态：发光边框
        if self._selected:
            pen = QPen(self._colors[2], 2.5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(1, 1, w - 2, h - 2, r, r)

            # 轻微光晕
            glow = QColor(self._colors[2])
            glow.setAlpha(40)
            pen2 = QPen(glow, 5)
            painter.setPen(pen2)
            painter.drawRoundedRect(3, 3, w - 6, h - 6, r, r)

        painter.end()


# ═══════════════════════════════════════════════════════════════════════
# 背景缩略图卡片
# ═══════════════════════════════════════════════════════════════════════

class _BgThumbCard(QFrame):
    """背景缩略图卡片。"""

    THUMB_SIZE = QSize(164, 96)

    def __init__(self, preset_id: str, display_name: str, thumbnail: QPixmap, parent=None) -> None:
        super().__init__(parent)
        self._preset_id = preset_id
        self.setObjectName("bgThumbCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(180, 150)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        self._thumb = QLabel()
        self._thumb.setPixmap(thumbnail)
        self._thumb.setFixedSize(self.THUMB_SIZE.width(), self.THUMB_SIZE.height())
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._thumb, alignment=Qt.AlignmentFlag.AlignCenter)

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
        self._radio.setChecked(selected)
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._radio.setChecked(True)
            self._radio.toggled.emit(True)
        super().mouseReleaseEvent(event)


# ═══════════════════════════════════════════════════════════════════════
# 联合设置对话框
# ═══════════════════════════════════════════════════════════════════════

class ThemeSettingsDialog(QDialog):
    """外观设置对话框（主题色彩 + 背景图片）。"""

    PREVIEW_SIZE = QSize(640, 280)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🎨 外观设置")
        self.setMinimumSize(860, 640)
        self.setModal(True)

        self._tm = get_theme_manager()
        self._bm = get_background_manager()
        self._initial_config = self._tm.config
        self._swatch_cards: dict[str, _ColorSwatch] = {}
        self._bg_cards: dict[str, _BgThumbCard] = {}

        self._build_ui()
        self._load_values()

    # ── 构建 ──

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🎨 外观设置")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        # ── 标签页 ──
        tabs = QTabWidget()
        tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #e2e8f0; border-radius: 8px; }")

        # == Tab 1: 主题色彩 ==
        theme_tab = QWidget()
        theme_layout = QVBoxLayout(theme_tab)
        theme_layout.setSpacing(12)
        theme_layout.setContentsMargins(12, 12, 12, 8)

        hint = QLabel("选择主题后，按钮、边框、输入框焦点等控件色彩将统一跟随变化")
        hint.setStyleSheet("color: #64748b; font-size: 12px;")
        hint.setWordWrap(True)
        theme_layout.addWidget(hint)

        # 色块网格：3 列，用 QVBoxLayout + QHBoxLayout row
        for i in range(0, len(THEMES), 3):
            row = QHBoxLayout()
            row.setSpacing(14)
            row.setContentsMargins(8, 0, 8, 0)

            for j in range(3):
                idx = i + j
                if idx >= len(THEMES):
                    break
                theme = THEMES[idx]
                card = _ColorSwatch(theme, parent=self)
                card.clicked.connect(self._on_theme_swatch_clicked)
                self._swatch_cards[theme.id] = card
                row.addWidget(card)

            row.addStretch()
            theme_layout.addLayout(row)

        theme_layout.addStretch()
        tabs.addTab(theme_tab, "🎨 主题色彩")

        # == Tab 2: 背景图片 ==
        bg_tab = QWidget()
        bg_layout = QVBoxLayout(bg_tab)
        bg_layout.setSpacing(12)
        bg_layout.setContentsMargins(12, 12, 12, 8)

        bg_hint = QLabel("背景图片置于底层。控件颜色由选中的纯色主题控制。")
        bg_hint.setStyleSheet("color: #64748b; font-size: 12px;")
        bg_hint.setWordWrap(True)
        bg_layout.addWidget(bg_hint)

        # 缩略图
        thumbs_label = QLabel("背景图片")
        thumbs_label.setObjectName("fieldLabel")
        bg_layout.addWidget(thumbs_label)

        thumbs_row = QHBoxLayout()
        thumbs_row.setSpacing(14)
        thumbs_row.setContentsMargins(8, 0, 8, 0)

        self._bg_radio_group = QButtonGroup(self)
        self._bg_radio_group.setExclusive(True)

        for preset in BACKGROUND_PRESETS:
            source = get_source_pixmap(preset.id)
            if source is None:
                continue
            thumb = make_thumbnail(source, _BgThumbCard.THUMB_SIZE)
            card = _BgThumbCard(preset.id, preset.name, thumb, parent=self)
            self._bg_radio_group.addButton(card.radio)
            card.radio.toggled.connect(self._on_bg_preset_changed)
            self._bg_cards[preset.id] = card
            thumbs_row.addWidget(card)

        thumbs_row.addStretch()
        bg_layout.addLayout(thumbs_row)

        # 透明度
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

        bg_layout.addLayout(opacity_row)

        # 开关
        switch_row = QHBoxLayout()
        self._enable_check = QCheckBox("启用背景图片（关闭后仅显示纯色主题）")
        self._enable_check.stateChanged.connect(self._on_bg_enable_changed)
        switch_row.addWidget(self._enable_check)
        switch_row.addStretch()
        bg_layout.addLayout(switch_row)

        # 分隔
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e2e8f0; background: #e2e8f0; max-height: 1px;")
        bg_layout.addWidget(sep)

        # 预览
        preview_label = QLabel("背景预览")
        preview_label.setObjectName("fieldLabel")
        bg_layout.addWidget(preview_label)

        self._preview = QLabel()
        self._preview.setObjectName("bgPreview")
        self._preview.setFixedSize(self.PREVIEW_SIZE)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet(
            "background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px;"
        )
        pc = QHBoxLayout()
        pc.addStretch()
        pc.addWidget(self._preview)
        pc.addStretch()
        bg_layout.addLayout(pc)

        bg_layout.addStretch()
        tabs.addTab(bg_tab, "🖼️ 背景图片")

        root.addWidget(tabs)

        # ── 底部按钮 ──
        btn_box = QDialogButtonBox()
        self._apply_btn = QPushButton("应用")
        self._apply_btn.setDefault(True)
        self._apply_btn.clicked.connect(self._on_apply)
        btn_box.addButton(self._apply_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addButton(cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_box)
        root.addLayout(btn_layout)

        self._update_bg_preview()

    # ── 加载 ──

    def _load_values(self) -> None:
        cfg = self._initial_config

        card = self._swatch_cards.get(cfg.theme_id)
        if card:
            card.set_selected(True)

        bg_card = self._bg_cards.get(cfg.bg_preset_id)
        if bg_card:
            bg_card.set_selected(True)
        self._slider.setValue(cfg.bg_opacity)
        self._opacity_value.setText(f"{cfg.bg_opacity}%")
        self._enable_check.setChecked(cfg.bg_enabled)
        self._set_bg_controls_enabled(cfg.bg_enabled)

    # ── 事件 ──

    def _on_theme_swatch_clicked(self, card: _ColorSwatch) -> None:
        for c in self._swatch_cards.values():
            c.set_selected(c.theme_id == card.theme_id)

    def _on_bg_preset_changed(self, checked: bool) -> None:
        if not checked:
            return
        sender = self.sender()
        pid = sender.property("preset_id") if sender else None
        if not pid:
            return
        for c in self._bg_cards.values():
            c.set_selected(c.preset_id == pid)
        self._update_bg_preview()

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_value.setText(f"{value}%")
        self._update_bg_preview()

    def _on_bg_enable_changed(self, state: int) -> None:
        enabled = state == Qt.CheckState.Checked.value
        self._set_bg_controls_enabled(enabled)
        self._update_bg_preview()

    def _set_bg_controls_enabled(self, enabled: bool) -> None:
        for c in self._bg_cards.values():
            c.setEnabled(enabled)
        self._slider.setEnabled(enabled)

    # ── 预览 ──

    def _update_bg_preview(self) -> None:
        if not self._enable_check.isChecked():
            placeholder = QPixmap(self.PREVIEW_SIZE)
            placeholder.fill(QColor(245, 247, 250))
            painter = QPainter(placeholder)
            try:
                painter.setPen(QColor(148, 163, 184))
                f = QFont()
                f.setPointSize(13)
                f.setBold(True)
                painter.setFont(f)
                painter.drawText(
                    placeholder.rect(),
                    Qt.AlignmentFlag.AlignCenter,
                    "背景已关闭\n（仅显示纯色主题）",
                )
            finally:
                painter.end()
            self._preview.setPixmap(placeholder)
            return

        pid = None
        for preset_id, card in self._bg_cards.items():
            if card.radio.isChecked():
                pid = preset_id
                break
        if pid is None:
            pid = next(iter(self._bg_cards.keys()), None)
        if pid is None:
            return

        source = get_source_pixmap(pid)
        if source is None:
            return
        self._preview.setPixmap(process_background(source, self.PREVIEW_SIZE, self._slider.value()))

    # ── 应用 ──

    def _current_theme_id(self) -> str:
        for tid, card in self._swatch_cards.items():
            if card.property("selected") == "true":
                return tid
        return self._initial_config.theme_id

    def _current_bg_preset_id(self) -> str:
        for pid, card in self._bg_cards.items():
            if card.radio.isChecked():
                return pid
        return self._initial_config.bg_preset_id

    def _on_apply(self) -> None:
        self._tm.update(
            theme_id=self._current_theme_id(),
            bg_enabled=self._enable_check.isChecked(),
            bg_preset_id=self._current_bg_preset_id(),
            bg_opacity=self._slider.value(),
        )
        self.accept()

    def reject(self) -> None:
        super().reject()
