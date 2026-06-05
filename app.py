"""应用主控：托盘图标、窗口管理、快捷键."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QShortcut
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QKeySequence

from data import DataStore
from theme import THEMES
from overlay import OverlayPanel
from editor import EditorWindow


def _create_tray_icon_pixmap():
    """生成托盘图标（红色底 + 白色'备'字）."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setBrush(QColor(255, 71, 87))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, 64, 64, 12, 12)
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Microsoft YaHei", 36, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignCenter, "备")
    painter.end()
    return pix


class App:
    """应用主控."""

    def __init__(self):
        self._store = DataStore()
        self._overlay = OverlayPanel(self._store)
        self._editor = EditorWindow(self._store)

        # 数据变更 → 刷新 overlay
        self._editor.data_changed.connect(self._overlay.refresh)

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(QIcon(_create_tray_icon_pixmap()))
        self._tray.setToolTip("工作备忘录")
        self._tray.activated.connect(self._on_tray_activated)
        self._build_tray_menu()
        self._tray.show()

        # 默认显示 overlay，隐藏编辑器
        self._overlay.show()

        # 注册全局快捷键 Ctrl+Alt+Q 退出（parent=None 确保全局生效）
        self._hotkey = QShortcut(QKeySequence("Ctrl+Alt+Q"), None)
        self._hotkey.activated.connect(self._quit)

    def _build_tray_menu(self):
        menu = QMenu()

        show_action = menu.addAction("显示编辑")
        show_action.triggered.connect(self._editor.show)

        # 主题子菜单
        theme_menu = menu.addMenu("主题")
        for key in THEMES:
            action = theme_menu.addAction(THEMES[key].name)
            action.triggered.connect(
                lambda checked, k=key: self._switch_theme(k)
            )

        # 屏幕选择子菜单
        screen_menu = menu.addMenu("显示屏幕")
        screens = QApplication.screens()
        for i, s in enumerate(screens):
            name = s.name()
            # 标记当前选中的屏幕
            label = f"屏幕 {i + 1}  {name}"
            if i == self._store.screen_index:
                label += "  ✓"
            action = screen_menu.addAction(label)
            action.triggered.connect(
                lambda checked, idx=i: self._switch_screen(idx)
            )

        menu.addSeparator()
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self._quit)

        self._tray.setContextMenu(menu)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._editor.show()
            self._editor.activateWindow()

    def _switch_theme(self, key: str):
        self._store.theme = key
        self._editor._apply_theme()
        self._editor.load_tasks()  # 刷新行样式以匹配新主题
        self._overlay.refresh()

    def _switch_screen(self, idx: int):
        self._store.screen_index = idx
        self._overlay.refresh()
        # 重建菜单以更新选中标记
        self._build_tray_menu()

    def _quit(self):
        self._tray.hide()
        self._editor.close()
        self._overlay.close()
        QApplication.quit()
