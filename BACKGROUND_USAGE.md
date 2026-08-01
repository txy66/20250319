# FinanceApp 外观系统 — 使用说明

## 功能概览

FinanceApp 外观系统由 **纯色主题** 和 **图片背景** 两套子系统组成，可独立或同时生效。

### 纯色主题系统
- **6 款内置主题**：天空蓝 / 翡翠绿 / 日落橙 / 紫罗兰 / 深海蓝 / 玫瑰粉
- **全局色彩联动**：选中主题后，按钮、边框、焦点指示器、控件外框统一跟随主题色变化
- **即时切换**：设置对话框中点击色块卡片，打开应用窗口即可预览效果
- **动态 QSS**：样式表由 Python 实时生成，无需维护静态 .qss 文件

### 图片背景系统
- **4 张内置风景背景**：郁金香花海 / 蓝色水波 / 雾气森林 / 银河星空
- **透明度调节**：0~100% 滑块，实时预览
- **自适应铺满**：cover 模式等比例缩放，不拉伸变形
- **融合优化**：自动降低亮度，保证前景文字和控件清晰
- **可开关**：关闭后仅显示纯色主题界面

### 联动规则
- 纯色主题与图片背景 **可同时生效**
- 图片背景位于 **底层**，控件色彩由 **纯色主题控制**
- 关闭图片背景 → 仅保留纯色主题界面
- 所有设置 **自动保存**，重启自动加载

## 文件变更清单

### 新增文件

| 文件 | 作用 |
|------|------|
| `utils/theme_manager.py` | 主题管理器：6 款主题定义、动态 QSS 生成、统一配置管理 |
| `ui/theme_settings_dialog.py` | 联合设置对话框："主题色彩" + "背景图片" 两个标签页 |
| `assets/backgrounds/*.jpg` | 4 张风景背景图 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `ui/main_window.py` | 启动加载 theme_config.json；外观设置按钮打开新对话框；应用主题后全量刷新 QSS + 背景 |
| `utils/background_manager.py` | 配置读写委托给 ThemeManager 统一管理，不再维护独立的 bg_config.json |
| `ui/styles.qss` | 不再被主窗口加载（主题 QSS 由 theme_manager 动态生成）。保留作为参考模板 |

### 可清理的旧文件

| 文件 | 说明 |
|------|------|
| `bg_config.json` | 旧背景配置文件，已被 `theme_config.json` 取代 |
| `ui/background_settings_dialog.py` | 旧纯背景对话框，已被 `theme_settings_dialog.py` 取代 |

## 配置存储

配置文件：`D:\workbuddy\0429\FinanceApp\theme_config.json`

```json
{
  "theme_id": "sky_blue",
  "bg_enabled": false,
  "bg_preset_id": "tulips",
  "bg_opacity": 35
}
```

| 字段 | 说明 |
|------|------|
| `theme_id` | 纯色主题 id（`sky_blue` / `emerald` / `sunset` / `violet` / `ocean` / `rose`） |
| `bg_enabled` | 是否启用图片背景 |
| `bg_preset_id` | 背景图 id（`tulips` / `water` / `forest` / `milky_way`） |
| `bg_opacity` | 背景透明度 0~100 |

## 使用方法

1. 启动应用：`python main.py`
2. 左侧导航栏底部点击 **🎨 外观设置**
3. 弹出对话框中：
   - **主题色彩** 标签页：点击色块卡片选择主题
   - **背景图片** 标签页：选择图片 + 调节透明度 + 勾选启用
4. 点击 **应用** 保存并立即生效
5. 取消关闭则不保存

## 内置主题预览

| 主题 | 主色 | 风格 |
|------|------|------|
| 天空蓝 (sky_blue) | `#3b82f6` | 清新专业，默认主题 |
| 翡翠绿 (emerald) | `#10b981` | 自然生机 |
| 日落橙 (sunset) | `#f97316` | 温暖活力 |
| 紫罗兰 (violet) | `#8b5cf6` | 优雅神秘 |
| 深海蓝 (ocean) | `#06b6d4` | 冷静沉稳 |
| 玫瑰粉 (rose) | `#ec4899` | 柔美温暖 |

## 架构设计

```
用户操作 → ThemeSettingsDialog
                │
                ├─ 主题色彩标签页 → ThemeManager.update(theme_id=...)
                │                         │
                │                         ├─ 写入 theme_config.json
                │                         └─ MainWindow._apply_theme()
                │                               └─ setStyleSheet(generate_stylesheet())
                │
                └─ 背景图片标签页 → ThemeManager.update(bg_*)
                                          │
                                          └─ MainWindow._refresh_background()
                                                └─ BackgroundManager.render()
```

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 设置对话框打不开 | PyQt6 未安装 | `pip install PyQt6>=6.6.0` |
| 背景图不显示 | `bg_enabled` 为 false 或图片缺失 | 检查设置 + `assets/backgrounds/` 目录 |
| 主题切换后颜色没变 | QSS 未正确应用 | 重启应用 |
| 启动报错 `theme_config.json` | JSON 格式损坏 | 删除该文件，重启自动生成默认配置 |
