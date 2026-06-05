"""应用主控：托盘图标、窗口管理、快捷键."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, QShortcut,
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QKeySequence

from data import DataStore, CATEGORIES, CATEGORY_LABELS, DEFAULT_CATEGORY_COLORS
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

        # 注册快捷键 Ctrl+Alt+Q 退出
        self._hotkey = QShortcut(QKeySequence("Ctrl+Alt+Q"), self._editor)
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

        # 颜色设置
        color_action = menu.addAction("颜色设置")
        color_action.triggered.connect(self._show_color_dialog)

        # 屏幕选择子菜单
        screen_menu = menu.addMenu("显示屏幕")
        screens = QApplication.screens()
        for i, s in enumerate(screens):
            name = s.name()
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

    def _show_color_dialog(self):
        """显示分类颜色设置对话框."""
        dlg = QDialog()
        dlg.setWindowTitle("分类颜色设置")
        dlg.resize(300, 280)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("点击颜色块修改各分类的文字颜色")
        title.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(title)

        color_buttons = {}
        colors = dict(self._store.category_colors)

        for cat in CATEGORIES:
            row = QHBoxLayout()
            label = QLabel(f"  {CATEGORY_LABELS[cat]}")
            label.setFont(QFont("Microsoft YaHei", 12))
            label.setStyleSheet(f"color: {colors[cat]};")
            row.addWidget(label)
            row.addStretch()

            btn = QPushButton("  ■  ")
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {colors[cat]};
                    font-size: 20px;
                    border: 2px solid {colors[cat]};
                    border-radius: 4px;
                    background: transparent;
                    padding: 2px 10px;
                }}
                QPushButton:hover {{
                    background: rgba(128,128,128,0.2);
                }}
            """)

            def make_callback(c=cat, b=btn, l=label):
                def callback():
                    from PyQt5.QtWidgets import QColorDialog
                    qcolor = QColorDialog.getColor(QColor(colors[c]), dlg, f"选择{CATEGORY_LABELS[c]}颜色")
                    if qcolor.isValid():
                        colors[c] = qcolor.name()
                        b.setStyleSheet(f"""
                            QPushButton {{
                                color: {colors[c]};
                                font-size: 20px;
                                border: 2px solid {colors[c]};
                                border-radius: 4px;
                                background: transparent;
                                padding: 2px 10px;
                            }}
                            QPushButton:hover {{
                                background: rgba(128,128,128,0.2);
                            }}
                        """)
                        l.setStyleSheet(f"color: {colors[c]};")
                return callback

            btn.clicked.connect(make_callback())
            row.addWidget(btn)
            layout.addLayout(row)

        layout.addStretch()

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(lambda: self._reset_colors(dlg, color_buttons, colors))
        btn_row.addWidget(reset_btn)

        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c; color: white;
                border: none; border-radius: 4px;
                padding: 6px 20px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1177bb; }
        """)
        ok_btn.clicked.connect(lambda: self._apply_colors(colors, dlg))
        btn_row.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)
        dlg.exec_()

    def _reset_colors(self, dlg, buttons, colors_dict):
        """恢复默认颜色."""
        for cat in CATEGORIES:
            colors_dict[cat] = DEFAULT_CATEGORY_COLORS[cat]

    def _apply_colors(self, colors: dict, dlg: QDialog):
        """应用颜色设置."""
        self._store.set_category_colors(colors)
        self._editor._apply_theme()
        self._editor.load_tasks()
        self._overlay.refresh()
        dlg.accept()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._editor.show()
            self._editor.activateWindow()

    def _switch_theme(self, key: str):
        self._store.theme = key
        self._editor._apply_theme()
        self._editor.load_tasks()
        self._overlay.refresh()

    def _switch_screen(self, idx: int):
        self._store.screen_index = idx
        self._overlay.refresh()
        self._build_tray_menu()

    def _quit(self):
        self._tray.hide()
        self._editor.close()
        self._overlay.close()
        QApplication.quit()
