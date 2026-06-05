"""桌面显示面板：右侧 overlay，鼠标穿透，置顶."""
from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
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
        self._layout.setContentsMargins(16, 20, 16, 20)
        self._layout.setSpacing(6)

    def _position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        panel_width = 260
        panel_height = screen.height() // 2
        x = screen.right() - panel_width - 10
        y = screen.top() + (screen.height() - panel_height) // 2
        self.setGeometry(x, y, panel_width, panel_height)

    def _refresh(self):
        """清空并重新渲染任务列表."""
        # 清除旧 widgets
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        theme = get_theme(self._store.theme)
        font = QFont("Microsoft YaHei", 11)

        tasks = self._store.get_active_tasks()
        if not tasks:
            # 无任务时显示提示
            hint = QLabel("暂无进行中的任务")
            hint.setFont(font)
            c = theme.text_primary.lstrip("#")
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            hint.setStyleSheet(f"color: rgba({r}, {g}, {b}, 0.5);")
            hint.setAlignment(Qt.AlignCenter)
            self._layout.addWidget(hint)
        else:
            for task in tasks:
                row = QLabel(f"●  {task.text}")
                row.setFont(font)
                color = CATEGORY_COLORS.get(task.category, theme.text_primary)
                row.setStyleSheet(f"color: {color};")
                self._layout.addWidget(row)

        self._layout.addStretch()

    def _apply_theme(self):
        theme = get_theme(self._store.theme)
        self.setStyleSheet(f"background: {theme.overlay_bg}; border-radius: 12px;")

    def refresh(self):
        self._apply_theme()
        self._refresh()
