# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Windows 桌面备忘录 v2——PyQt5 多窗口应用，由系统托盘控制。桌面右侧显示一个鼠标穿透的半透明 Overlay 面板，列出所有进行中的任务；双击托盘图标或从菜单打开编辑器进行任务的增删改查和拖拽排序。数据以 JSON 文件持久化。

## 运行方式

```bash
# 直接运行（开发调试）
python main.py

# 打包为 exe（使用 PyInstaller）
pyinstaller --onefile --noconsole main.py
```

## 运行依赖

- Python 3.x
- `PyQt5>=5.15.0`
- Windows 平台专用（依赖 `ctypes.windll` 实现鼠标穿透和窗口层级控制）

## 架构说明

应用由 6 个模块组成，入口 `main.py`：

### 1. `main.py` — 入口
- 创建 QApplication，设置 `quitOnLastWindowClosed=False`
- 实例化 `App` 并进入事件循环

### 2. `app.py` — 应用主控
- 创建托盘图标（红色底 + 白色"备"字）
- 管理三个窗口：OverlayPanel（始终显示）、EditorWindow（按需弹出）
- 托盘菜单：显示编辑 / 主题切换（暗夜/明亮/毛玻璃） / 颜色设置 / 选择屏幕 / 退出
- `Ctrl+Alt+Q` 全局快捷键退出
- 数据变更信号从 Editor 传递到 Overlay 刷新

### 3. `overlay.py` — 桌面显示面板
- 无边框 Tool 窗口，始终位于桌面层级
- 使用 Windows API（`WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW` + `SetWindowPos(HWND_BOTTOM)`）实现鼠标穿透
- 单个 QLabel 以 HTML rich text 渲染任务列表（● 圆点 + 分类颜色 + 任务文本）
- 动态计算面板尺寸：最长文本宽度决定面板宽度，行数决定高度
- 支持多屏幕选择

### 4. `editor.py` — 编辑界面
- QMainWindow 窗口，包含输入栏（文本 + 分类下拉 + 添加按钮）和任务列表
- 自定义 `_MemoListWidget`（继承 QListWidget）处理拖拽排序：dropEvent 后 100ms 延迟重建整个列表，避免 Qt InternalMove 破坏 setItemWidget 关联
- `_TaskRow` 控件：拖拽手柄 ☰ + 分类圆点 ● + 复选框 + 任务文本 + 分类标签
- 双击任务文本进入行内编辑（Enter 保存，Esc 取消，FocusOut 自动保存）
- 右键菜单：切换分类、删除
- 勾选复选框标记完成
- 可通过编辑的分类（`EDITABLE_CATEGORIES`）：now / fire / follow / memo（排除 done，完成状态由复选框控制）
- 关闭窗口 = 最小化到托盘，Esc 隐藏窗口，Delete 键删除选中任务

### 5. `data.py` — 数据层
- `Task` 数据类：id（UUID 前 8 位）、text、category、done、sort
- `DataStore`：JSON 文件读写（`~/备忘.json`），支持任务的增删改查和排序
- `get_active_tasks()` 返回未完成任务，按 sort 排序
- 分类颜色支持自定义，`category_colors` 属性返回 dict 副本防止外部直接修改
- 数据文件字段：version、theme、screen_index、category_colors、tasks

### 6. `theme.py` — 主题定义
- `Theme` 类：overlay_bg、editor_bg、editor_text、editor_border、row_hover、input_bg、input_text、text_primary、accent、accent_hover
- 三套主题（`THEMES` 字典）：
  - `dark`：深色背景，白色文字，`rgba(20,20,35,0.88)` overlay
  - `light`：浅色背景，深色文字，`rgba(255,255,255,0.90)` overlay
  - `glass`：半透明磨砂，`rgba(30,30,45,0.55)` overlay
- `get_theme(key)` 工厂函数，默认返回 dark

## 数据流

```
EditorWindow (用户操作)
  → DataStore (增删改查 + 保存 JSON)
  → data_changed 信号
  → OverlayPanel.refresh() (重新渲染)
  → App._switch_theme() / _apply_colors() 同时刷新 editor 和 overlay
```

## 文件路径约定

| 用途 | 路径 |
|------|------|
| 应用入口 | `./main.py` |
| 数据文件 | `~/备忘.json` |

## 关键实现细节

- 鼠标穿透依赖 Windows API，非 Qt 属性实现。在 `OverlayPanel._ensure_click_through()` 中设置扩展窗口样式并置底
- 拖拽排序后必须 `load_tasks()` 重建整个列表（`setItemWidget` 在 InternalMove 后会丢失关联）
- 主题切换和颜色变更后需要同时刷新 editor（`_apply_theme()` + `load_tasks()`）和 overlay（`refresh()`）
- 颜色设置对话框使用 `QColorDialog`，在 `app.py` 的 `_show_color_dialog()` 中实现，闭包捕获各分类按钮/标签引用
- `EditorWindow.closeEvent` 被重写为 `hide() + event.ignore()`，关闭即最小化到托盘
