"""桌面显示面板：右侧 overlay，鼠标穿透，置顶."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt5.QtGui import QFont

from data import DataStore
from theme import get_theme, CATEGORY_COLORS


class OverlayPanel(QWidget):
    """桌面右侧任务显示面板."""

    refresh_requested = pyqtSignal()

    def __init__(self, store: DataStore):
        super().__init__()
        self._store = store
        self._init_ui()
        self._apply_theme()
        self._position()
        self.refresh_requested.connect(self._refresh)
        self.refresh()

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 18, 18, 18)

        # 单一 QLabel 承载所有任务文字，实现一体背景
        self._label = QLabel()
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._layout.addWidget(self._label)

    def _position(self):
        screens = QApplication.screens()
        idx = max(0, min(self._store.screen_index, len(screens) - 1))
        screen = screens[idx].availableGeometry()

        panel_width = 280
        # 动态高度：根据内容自适应，最大不超过屏幕的 60%
        max_height = int(screen.height() * 0.6)

        # 先估算行数来确定高度
        tasks = self._store.get_active_tasks()
        line_count = max(len(tasks), 1)
        estimated_height = min(line_count * 28 + 40, max_height)

        x = screen.right() - panel_width - 10
        y = screen.top() + (screen.height() - estimated_height) // 2
        self.setGeometry(x, y, panel_width, estimated_height)

    def _refresh(self):
        """重新渲染任务列表."""
        theme = get_theme(self._store.theme)
        font = QFont("Microsoft YaHei", 14)

        tasks = self._store.get_active_tasks()
        if not tasks:
            self._label.setFont(font)
            self._label.setAlignment(Qt.AlignCenter)
            c = theme.text_primary.lstrip("#")
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            self._label.setStyleSheet(f"color: rgba({r}, {g}, {b}, 0.5);")
            self._label.setText("暂无进行中的任务")
        else:
            self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            # 构建富文本，每条任务一行，不同颜色
            lines = []
            for task in tasks:
                color = CATEGORY_COLORS.get(task.category, theme.text_primary)
                # 对长文本进行智能截断（超过30字符换行由 wordWrap 处理）
                lines.append(
                    f'<span style="color:{color};">●  {task.text}</span>'
                )
            text = "<br>".join(lines)
            self._label.setFont(font)
            self._label.setStyleSheet(f"color: {theme.text_primary};")
            self._label.setText(text)

        # 刷新后重新调整位置（高度可能变化）
        self._position()

    def _apply_theme(self):
        theme = get_theme(self._store.theme)
        self.setStyleSheet(f"background: {theme.overlay_bg}; border-radius: 12px;")

    def refresh(self):
        self._apply_theme()
        self._refresh()
