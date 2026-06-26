"""桌面显示面板：右侧 overlay，鼠标穿透，桌面层级."""
from __future__ import annotations

import sys

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt5.QtGui import QFont, QFontMetrics

from data import DataStore
from theme import get_theme

FONT_SIZE = 13
TOPMOST_INTERVAL = 5 * 60 * 1000  # 每5分钟置顶一次


class OverlayPanel(QWidget):
    """桌面右侧任务显示面板."""

    refresh_requested = pyqtSignal()

    def __init__(self, store: DataStore):
        super().__init__()
        self._store = store
        self._click_through_done = False
        self._init_ui()
        self._apply_theme()
        self.refresh()

        # 监听屏幕增减，自动重新定位
        app = QApplication.instance()
        if app:
            app.screenAdded.connect(self._on_screen_changed)
            app.screenRemoved.connect(self._on_screen_changed)

        # 每5分钟将 overlay 提升到最上层
        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self._bring_to_front)
        self._topmost_timer.start(TOPMOST_INTERVAL)
        # 初始也执行一次，确保启动时在顶层
        QTimer.singleShot(500, self._bring_to_front)

    def _on_screen_changed(self, screen):
        """屏幕增减时刷新 overlay 位置."""
        screens = QApplication.screens()
        # 如果当前选择的屏幕已不可用，自动切到屏幕0
        if self._store.screen_index >= len(screens):
            self._store.screen_index = 0
        self.refresh()

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
            from ctypes import wintypes

            hwnd = int(self.winId())

            # WS_EX_TRANSPARENT: 窗口对鼠标透明
            # WS_EX_LAYERED: 支持分层窗口（透明背景必须）
            # WS_EX_NOACTIVATE: 不接收焦点
            # WS_EX_TOOLWINDOW: 不在任务栏显示
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

    def _bring_to_front(self):
        """将 overlay 临时置顶后恢复到正常层级顶部。

        效果：overlay 显示在所有非 TOPMOST 窗口之上，
        用户点击其他窗口后该窗口可正常覆盖 overlay，
        每5分钟自动重新提升。
        """
        if sys.platform != 'win32':
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            if hwnd == 0:
                return  # 窗口句柄尚未创建
            user32 = ctypes.windll.user32
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            # 置顶
            user32.SetWindowPos(
                hwnd, HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
            # 延迟100ms后恢复到非置顶层级的顶部，确保 Windows 完成 Z-order 排序
            QTimer.singleShot(100, lambda: self._drop_from_topmost(hwnd))
        except Exception:
            pass

    def _drop_from_topmost(self, hwnd: int):
        """从置顶降回正常层级顶部."""
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
