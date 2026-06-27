"""桌面显示面板：右侧 overlay，鼠标穿透，桌面层级."""
from __future__ import annotations

import sys

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt5.QtGui import QFont, QFontMetrics

from data import DataStore
from theme import get_theme

FONT_SIZE = 13
# 定时器间隔（毫秒）
TOPMOST_INTERVAL = 5 * 60 * 1000      # 每5分钟提升 Z-order
SCREEN_CHECK_INTERVAL = 3 * 1000       # 每3秒检查屏幕是否恢复
TOPMOST_DROP_DELAY = 500               # TOPMOST→NOTOPMOST 延迟（毫秒）


class OverlayPanel(QWidget):
    """桌面右侧任务显示面板."""

    refresh_requested = pyqtSignal()

    def __init__(self, store: DataStore):
        super().__init__()
        self._store = store
        self._click_through_done = False
        self._preferred_screen_name: str = ""
        self._init_ui()
        self._apply_theme()
        self.refresh()

        # 监听屏幕增减信号（物理连接/断开）
        app = QApplication.instance()
        if app:
            app.screenAdded.connect(self._on_screen_changed)
            app.screenRemoved.connect(self._on_screen_changed)

        # 定期轮询：检测信号未覆盖的屏幕变化（如显示器开关机）
        self._screen_check_timer = QTimer(self)
        self._screen_check_timer.timeout.connect(self._check_screen_availability)
        self._screen_check_timer.start(SCREEN_CHECK_INTERVAL)

        # 每5分钟将 overlay 提升到 Z-order 顶部
        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self._bring_to_front)
        self._topmost_timer.start(TOPMOST_INTERVAL)
        # 启动 1 秒后首次执行（等窗口完全就绪）
        QTimer.singleShot(1000, self._bring_to_front)

    # ─── 屏幕切换 ────────────────────────────────────────────

    def _on_screen_changed(self, screen):
        """屏幕增减信号处理：尝试恢复到用户选择的屏幕."""
        self._restore_preferred_screen()

    def _check_screen_availability(self):
        """定期轮询：检测屏幕是否恢复（处理信号遗漏的情况）."""
        screens = QApplication.screens()
        # 检查当前屏幕索引是否有效
        if self._store.screen_index >= len(screens):
            self._restore_preferred_screen()
            return
        # 检查是否在首选屏幕上，不在则尝试恢复
        current_name = screens[self._store.screen_index].name()
        if self._preferred_screen_name and current_name != self._preferred_screen_name:
            self._restore_preferred_screen()

    def _restore_preferred_screen(self):
        """尝试根据屏幕名称找回用户选择的屏幕，失败则回退到索引0."""
        screens = QApplication.screens()
        if not screens:
            return
        # 优先按名称匹配
        if self._preferred_screen_name:
            for i, s in enumerate(screens):
                if s.name() == self._preferred_screen_name:
                    if self._store.screen_index != i:
                        self._store.screen_index = i
                        self.refresh()
                    return
        # 回退：索引越界时重置为 0
        if self._store.screen_index >= len(screens):
            self._store.screen_index = 0
            self.refresh()

    # ─── Z-order 管理 ────────────────────────────────────────

    def _bring_to_front(self):
        """将 overlay 提升到 Z-order 顶部。

        策略：先设为 TOPMOST 强制突破所有 Z-order 限制，
        500ms 后降回 NOTOPMOST（保持在非置顶窗口最上层）。
        这样用户点击其他窗口时该窗口可以正常覆盖 overlay。
        """
        if sys.platform != 'win32':
            return
        hwnd = self._get_valid_hwnd()
        if hwnd is None:
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
            SW_SHOWNOACTIVATE = 4
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            HWND_TOPMOST = -1

            # 确保窗口可见（对 tool window 很重要）
            user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)

            # 设为 TOPMOST
            user32.SetWindowPos(
                hwnd, HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
            # 延迟后降回非置顶（保持 Z-order 顶部位置）
            QTimer.singleShot(TOPMOST_DROP_DELAY, lambda: self._drop_from_topmost(hwnd))
        except Exception:
            pass

    def _drop_from_topmost(self, hwnd: int):
        """从 TOPMOST 降回非置顶层级的顶部."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            HWND_NOTOPMOST = -2
            user32.SetWindowPos(
                hwnd, HWND_NOTOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
        except Exception:
            pass

    def _get_valid_hwnd(self):
        """获取有效的原生窗口句柄，失败返回 None."""
        try:
            hwnd = int(self.winId())
            if hwnd == 0:
                return None
            return hwnd
        except Exception:
            return None

    # ─── UI 初始化 ────────────────────────────────────────────

    def _init_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)

        self._label = QLabel()
        self._label.setTextFormat(Qt.RichText)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._layout.addWidget(self._label)

    def _ensure_click_through(self):
        """通过 Windows API 确保窗口完全穿透鼠标点击."""
        if self._click_through_done or sys.platform != 'win32':
            return
        try:
            import ctypes

            hwnd = int(self.winId())

            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080

            user32 = ctypes.windll.user32
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

            self._click_through_done = True
        except Exception:
            pass

    # ─── 布局与渲染 ──────────────────────────────────────────

    def _measure_text(self):
        """测量最长文本宽度和总行数."""
        font = QFont("Microsoft YaHei", FONT_SIZE)
        fm = QFontMetrics(font)
        tasks = self._store.get_active_tasks()

        max_width = 40
        for task in tasks:
            w = fm.horizontalAdvance(f"●  {task.text}")
            max_width = max(max_width, w)

        line_height = fm.height() + 6
        line_count = max(len(tasks), 1)
        return max_width, line_height, line_count

    def _position(self):
        screens = QApplication.screens()
        idx = max(0, min(self._store.screen_index, len(screens) - 1))
        screen = screens[idx].availableGeometry()

        # 记住当前屏幕名称，用于屏幕热插拔时自动恢复
        self._preferred_screen_name = screens[idx].name()

        max_text_width, line_height, line_count = self._measure_text()

        panel_width = max(160, min(max_text_width + 48, screen.width() // 3))
        panel_height = min(line_count * line_height + 36, int(screen.height() * 0.7))

        x = screen.right() - panel_width - 10
        y = screen.top() + (screen.height() - panel_height) // 2
        self.setGeometry(x, y, panel_width, panel_height)

    def _refresh(self):
        """重新渲染任务列表."""
        theme = get_theme(self._store.theme)
        font = QFont("Microsoft YaHei", FONT_SIZE)

        tasks = self._store.get_active_tasks()
        if not tasks:
            self._label.setFont(font)
            self._label.setAlignment(Qt.AlignCenter)
            c = theme.text_primary.lstrip("#")
            if len(c) == 6:
                r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
                self._label.setText(
                    f'<span style="color:rgba({r},{g},{b},128);">暂无进行中的任务</span>'
                )
            else:
                self._label.setText(
                    f'<span style="color:{theme.text_primary};">暂无进行中的任务</span>'
                )
        else:
            self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lines = []
            for task in tasks:
                color = self._store.category_colors.get(task.category, theme.text_primary)
                lines.append(f'<span style="color:{color};">●  {task.text}</span>')
            text = "<br>".join(lines)
            self._label.setFont(font)
            self._label.setText(text)

        self._position()

    def _apply_theme(self):
        theme = get_theme(self._store.theme)
        self.setStyleSheet(
            f"background: {theme.overlay_bg}; border-radius: 12px;"
        )

    def refresh(self):
        self._apply_theme()
        self._refresh()
        self._ensure_click_through()
