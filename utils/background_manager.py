"""
utils/background_manager.py - 自定义背景管理器

职责：
1. 维护 4 张内置背景图元数据（id / 显示名 / 文件名）
2. 对接 theme_manager 统一配置（theme_config.json），读取/更新背景相关字段
3. 提供图片处理函数：
   - 缩放到目标尺寸（cover 模式：等比例铺满、不拉伸变形、允许裁剪）
   - 降低亮度（叠加半透明黑色遮罩）
   - 应用透明度
4. 单例接口：get_background_manager()

设计要点：
- 图片处理输出 RGBA8888，确保透明度可控
- 模糊/柔化效果通过 QPainter 的渲染提示 + 暗化遮罩实现，
  无需引入 PIL/OpenCV 等额外依赖
- 配置持久化委托给 ThemeManager 统一管理
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor


# ─── 资源路径 ───────────────────────────────────────────────────────────────

_APP_ROOT: Path = Path(__file__).resolve().parent.parent
_ASSETS_DIR: Path = _APP_ROOT / "assets" / "backgrounds"


# ─── 内置背景预设 ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BackgroundPreset:
    """单张背景预设。"""
    id: str           # 内部 id（也用于持久化）
    name: str         # 中文显示名
    file: str         # assets/backgrounds 下的文件名


BACKGROUND_PRESETS: tuple[BackgroundPreset, ...] = (
    BackgroundPreset("tulips",    "郁金香花海", "tulips.jpg"),
    BackgroundPreset("water",     "蓝色水波",   "water.jpg"),
    BackgroundPreset("forest",    "雾气森林",   "forest.jpg"),
    BackgroundPreset("milky_way", "银河星空",   "milky_way.jpg"),
)

# id -> 预设 的快速查找表
PRESET_MAP: dict[str, BackgroundPreset] = {p.id: p for p in BACKGROUND_PRESETS}


def get_preset(preset_id: str) -> BackgroundPreset:
    """根据 id 获取预设，未匹配时返回第一张作为默认。"""
    return PRESET_MAP.get(preset_id) or BACKGROUND_PRESETS[0]


# ─── 配置 → 委托给 ThemeManager 统一管理 ────────────────────────────────────

# 背景相关字段已统一存储在 theme_config.json，
# 读写操作通过 ThemeManager 单例进行。


# ─── 图片处理 ──────────────────────────────────────────────────────────────

def get_source_pixmap(preset_id: str) -> Optional[QPixmap]:
    """
    加载指定预设的原图（不缩放不处理）。
    文件缺失时返回 None。
    """
    preset = get_preset(preset_id)
    path = _ASSETS_DIR / preset.file
    if not path.exists():
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    return pixmap


def process_background(
    source: QPixmap,
    target_size: QSize,
    opacity_percent: int,
) -> QPixmap:
    """
    把源图处理成可直接用作窗口背景的 pixmap。

    步骤：
    1. 按 cover 模式等比例缩放（短边贴合目标尺寸，长边超出裁剪）
    2. 居中绘制到目标画布
    3. 叠加半透明黑色遮罩降低亮度（柔和化）
    4. 应用用户透明度（数值越大，背景越明显）

    Args:
        source: 原图 pixmap
        target_size: 目标画布尺寸（通常等于窗口客户区尺寸）
        opacity_percent: 0~100，0=完全透明（不可见），100=完全不透明（无效果）
    """
    if source.isNull() or target_size.width() <= 0 or target_size.height() <= 0:
        return QPixmap()

    # 限制到合法范围
    opacity_percent = max(0, min(100, opacity_percent))

    # ── 1. cover 模式缩放：等比例放大到完全覆盖目标尺寸 ──
    scaled = source.scaled(
        target_size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )

    # ── 2. 创建目标画布（透明底，方便叠遮罩）──
    canvas = QPixmap(target_size)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    try:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 计算居中位置（cover 模式下图片可能比目标大，需要居中裁剪）
        x = (target_size.width() - scaled.width()) // 2
        y = (target_size.height() - scaled.height()) // 2

        # ── 3. 绘制原图（应用用户透明度）──
        # opacity_percent 越高代表背景越可见，所以映射为 0.0~1.0
        user_opacity = opacity_percent / 100.0
        painter.setOpacity(user_opacity)
        painter.drawPixmap(x, y, scaled)
        painter.setOpacity(1.0)

        # ── 4. 叠加半透明黑色遮罩降低亮度（柔化视觉冲击力）──
        # 即使透明度设为 100%，也保留一定程度的暗化，避免前景文字与背景冲突。
        # 透明度数值越高，背景越显眼，遮罩越淡；反之遮罩越重。
        # 公式：darken_alpha = 110 - opacity_percent * 0.6 → 110(0%) → 50(100%)
        darken_alpha = max(40, int(110 - opacity_percent * 0.6))
        painter.fillRect(canvas.rect(), QColor(0, 0, 0, darken_alpha))
    finally:
        painter.end()

    return canvas


def make_thumbnail(
    source: QPixmap,
    size: QSize,
) -> QPixmap:
    """
    为设置对话框生成缩略图：
    cover 缩放 + 轻度暗化（保持选择时可辨识度，但不抢眼）。
    """
    if source.isNull():
        return QPixmap()

    scaled = source.scaled(
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )

    canvas = QPixmap(size)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    try:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        x = (size.width() - scaled.width()) // 2
        y = (size.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        # 缩略图始终保持适度暗化，保证前景文字可读
        painter.fillRect(canvas.rect(), QColor(0, 0, 0, 30))
        # 边框，便于在对话框中区分
        painter.setPen(QColor(255, 255, 255, 80))
        painter.drawRect(canvas.rect().adjusted(0, 0, -1, -1))
    finally:
        painter.end()

    return canvas


# ─── 单例 ──────────────────────────────────────────────────────────────────

class BackgroundManager:
    """
    背景管理器单例。
    通过 get_background_manager() 获取实例，
    在窗口启动时读取配置、调用 process_background 生成背景 pixmap。
    """

    def __init__(self) -> None:
        # 延迟导入，避免循环依赖
        from utils.theme_manager import get_theme_manager
        self._tm = get_theme_manager()

    # ── 配置访问（从 ThemeManager 统一配置中读取） ──

    @property
    def enabled(self) -> bool:
        return self._tm.config.bg_enabled

    @property
    def preset_id(self) -> str:
        return self._tm.config.bg_preset_id

    @property
    def opacity(self) -> int:
        return self._tm.config.bg_opacity

    def update(self, enabled: bool, preset_id: str, opacity: int) -> None:
        """更新背景配置并持久化。"""
        if preset_id not in PRESET_MAP:
            preset_id = "tulips"
        opacity = max(0, min(100, opacity))
        self._tm.update(bg_enabled=bool(enabled), bg_preset_id=preset_id, bg_opacity=opacity)

    # ── 背景生成 ──

    def render(self, target_size: QSize) -> QPixmap:
        """
        根据当前配置生成窗口背景 pixmap。
        当未启用时返回空 pixmap（调用方应展示默认纯色背景）。
        """
        if not self.enabled:
            return QPixmap()
        source = get_source_pixmap(self.preset_id)
        if source is None:
            return QPixmap()
        return process_background(source, target_size, self.opacity)


# ─── 单例获取 ──────────────────────────────────────────────────────────────

_manager: Optional[BackgroundManager] = None


def get_background_manager() -> BackgroundManager:
    """获取 BackgroundManager 单例。"""
    global _manager
    if _manager is None:
        _manager = BackgroundManager()
    return _manager


def reset_background_manager() -> None:
    """重置单例（主要用于测试）。"""
    global _manager
    _manager = None


# ─── 调试辅助 ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow

    app = QApplication(sys.argv)

    mgr = get_background_manager()
    print(f"背景: enabled={mgr.enabled}, preset={mgr.preset_id}, opacity={mgr.opacity}")
    print("可用预设:", [(p.id, p.name) for p in BACKGROUND_PRESETS])

    win = QMainWindow()
    win.resize(900, 600)

    bg = mgr.render(win.size())
    if not bg.isNull():
        label = QLabel(win)
        label.setPixmap(bg)
        label.setScaledContents(True)
        label.setGeometry(0, 0, 900, 600)
        label.lower()

    win.show()
    sys.exit(app.exec())