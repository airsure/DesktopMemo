# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Windows 桌面备忘录工具——读取桌面上的 `备忘.txt` 文件，将任务列表渲染到背景图片上，并设置为 Windows 桌面壁纸。程序以系统托盘图标形式常驻后台，每 10 秒自动检测文件变更并刷新壁纸。

## 运行方式

```bash
# 直接运行（开发调试）
python 桌面备忘.py

# 打包为 exe（使用 PyInstaller）
pyinstaller --onefile --noconsole 桌面备忘.py
```

## 运行依赖

- Python 3.x
- `Pillow`（PIL）— 图片处理和文字渲染
- `pystray` — 系统托盘图标
- `pywin32` — Windows API（快捷键注册、消息循环）
- Windows 平台专用（依赖 `ctypes.windll` 和 `win32gui`/`win32con`/`win32api`）

## 架构说明

整个应用是单文件 `桌面备忘.py`，约 260 行，分为以下几个功能模块：

### 1. 数据来源（`get_user_paths` / `get_work_text`）
- 从 `~/Desktop/备忘.txt` 读取任务列表，每行一个任务
- 任务按前缀符号分类：
  - `★` — 当前任务（红色）
  - `▲` — 紧急任务（橙色）
  - `□` — 跟进任务（蓝色）
  - `√` — 已完成（绿色）
  - `备` — 备忘录（粉色）
- 背景图片取自 `~/Pictures/背景图片.jpg`，输出到 `~/Pictures/工作备忘背景.jpg`

### 2. 图片渲染（`pic_text` / `main`）
- `main()` 是核心函数：读取背景图 → 计算任务文字的整体尺寸 → 计算统一左对齐坐标（最长文字右边界距屏幕右侧 30px）→ 按优先级顺序（now > fire > follow > done > memo）绘制所有任务 → 保存输出图片
- 字体降级链：微软雅黑 20px → 宋体 → 黑体 → PIL 默认字体

### 3. 壁纸更新（`check_update`）
- 首次运行时生成图片并调用 `SystemParametersInfoW(20, ...)` 设置为壁纸
- 之后每 10 秒轮询 `备忘.txt` 是否有变化，有变化则重新生成并更新壁纸

### 4. 托盘图标（`create_tray_icon`）
- 使用 pystray 创建系统托盘图标，右键菜单可退出程序

### 5. 退出机制（`force_quit` / `hide_console` / `register_hotkey`）
- `force_quit` 使用 `os._exit(0)` 强制退出，并通过 `atexit` 注册确保清理
- 打包为 exe 时自动隐藏控制台窗口
- 注册 `Ctrl+Alt+Q` 全局快捷键退出程序

## 文件路径约定

所有路径基于用户主目录（`~`）：
| 用途 | 路径 |
|------|------|
| 任务列表 | `~/Desktop/备忘.txt` |
| 背景图片 | `~/Pictures/背景图片.jpg` |
| 输出壁纸 | `~/Pictures/工作备忘背景.jpg` |

## 注意事项

- 仅在 Windows 上运行，依赖多个 Windows 专属 API
- `SystemParametersInfoW(20, 0, image_path, 0)` 中的 `20` 对应 `SPI_SETDESKWALLPAPER`，需要 `.jpg` 格式的图片路径
- `os._exit(0)` 用于绕过 Python 正常的退出流程，确保托盘线程能被强制终止
