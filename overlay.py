"""桌面显示面板：右侧 overlay，鼠标穿透，桌面层级."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt5.QtGui import QFont, QFontMetrics

from data import DataStore
from theme import get_theme

FONT_SIZE = 13


class OverlayPanel(QWidget):
    """桌面右侧任务显示面板."""

    refresh_requested = pyqtSignal()

    def __init__(self, store: DataStore):
        super().__init__()
        self._store = store
        self._init_ui()
        self._apply_theme()
        self.refresh()

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowStaysOnBottomHint
            | Qt.FramelessWindowHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)

        self._label = QLabel()
        self._label.setTextFormat(Qt.RichText)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._layout.addWidget(self._label)

    def _measure_text(self):
        """测量最长文本宽度和总行数."""
        font = QFont("Microsoft YaHei", FONT_SIZE)
        fm = QFontMetrics(font)
        tasks = self._store.get_active_tasks()

        max_width = 40  # 最小宽度
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

        # 面板宽度 = 文字宽度 + 左右边距，限制在屏幕1/3以内
        panel_width = max(160, min(max_text_width + 48, screen.width() // 3))

        # 面板高度 = 行数 × 行高 + 上下边距，限制在屏幕70%以内
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
