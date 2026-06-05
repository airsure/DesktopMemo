"""编辑主界面：任务列表、拖拽排序、分类管理."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QCheckBox, QLabel, QMenu, QAction, QApplication,
)

from data import DataStore, Task, CATEGORIES, CATEGORY_LABELS
from theme import get_theme, CATEGORY_COLORS


class EditorWindow(QMainWindow):
    """编辑主界面."""

    data_changed = pyqtSignal()

    def __init__(self, store: DataStore):
        super().__init__()
        self._store = store
        self._init_ui()
        self._apply_theme()
        self.load_tasks()

    def _init_ui(self):
        self.setWindowTitle("工作备忘录")
        self.resize(420, 560)
        self.setMinimumSize(340, 400)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 输入栏
        input_layout = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("输入新任务...")
        self._input.returnPressed.connect(self._add_task)

        self._category_combo = QComboBox()
        for cat in CATEGORIES:
            self._category_combo.addItem(CATEGORY_LABELS[cat], cat)

        self._add_btn = QPushButton("+")
        self._add_btn.setFixedWidth(32)
        self._add_btn.clicked.connect(self._add_task)

        input_layout.addWidget(self._input)
        input_layout.addWidget(self._category_combo)
        input_layout.addWidget(self._add_btn)
        layout.addLayout(input_layout)

        # 任务列表
        self._list = QListWidget()
        self._list.setDragDropMode(self._list.InternalMove)
        self._list.setDefaultDropAction(Qt.MoveAction)
        self._list.model().rowsMoved.connect(self._on_reorder)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._list)

    def _add_task(self):
        text = self._input.text().strip()
        if not text:
            return
        category = self._category_combo.currentData()
        self._store.add_task(text, category)
        self._input.clear()
        self.load_tasks()
        self.data_changed.emit()

    def load_tasks(self):
        """从 store 重新加载任务列表."""
        self._list.clear()
        tasks = sorted(self._store.tasks, key=lambda t: t.sort)
        for task in tasks:
            self._add_task_row(task)

    def _add_task_row(self, task: Task):
        """向列表添加一行任务."""
        item = QListWidgetItem()
        item.setData(Qt.UserRole, task.id)
        item.setFlags(
            Qt.ItemIsSelectable
            | Qt.ItemIsEnabled
            | Qt.ItemIsDragEnabled
            | Qt.ItemIsDropEnabled
        )

        row = _TaskRow(task, self._store)
        row.checkbox.stateChanged.connect(
            lambda state, tid=task.id: self._on_check(tid, state)
        )

        item.setSizeHint(row.sizeHint())
        self._list.addItem(item)
        self._list.setItemWidget(item, row)

    def _on_check(self, task_id: str, state: int):
        done = state == Qt.Checked
        self._store.update_task(task_id, done=done)
        self.load_tasks()
        self.data_changed.emit()

    def _on_reorder(self, *args):
        """拖拽排序后重新编号（不发射信号，避免干扰拖拽操作）."""
        task_ids = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            task_ids.append(item.data(Qt.UserRole))
        self._store.reorder(task_ids)

    def _show_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        task_id = item.data(Qt.UserRole)
        task = next((t for t in self._store.tasks if t.id == task_id), None)
        if not task:
            return

        menu = QMenu(self)

        # 切换分类子菜单
        cat_menu = menu.addMenu("切换分类")
        for cat in CATEGORIES:
            if cat != task.category:
                action = cat_menu.addAction(CATEGORY_LABELS[cat])
                action.triggered.connect(
                    lambda checked, tid=task_id, c=cat: self._change_category(tid, c)
                )

        menu.addSeparator()
        del_action = menu.addAction("删除")
        del_action.triggered.connect(
            lambda: self._delete_task(task_id)
        )

        menu.exec_(self._list.viewport().mapToGlobal(pos))

    def _change_category(self, task_id: str, category: str):
        self._store.update_task(task_id, category=category)
        self.load_tasks()
        self.data_changed.emit()

    def _delete_task(self, task_id: str):
        self._store.delete_task(task_id)
        self.load_tasks()
        self.data_changed.emit()

    def _apply_theme(self):
        theme = get_theme(self._store.theme)
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme.editor_bg};
                color: {theme.editor_text};
                font-size: 13px;
            }}
            QLineEdit {{
                background-color: {theme.input_bg};
                color: {theme.input_text};
                border: 1px solid {theme.editor_border};
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 13px;
            }}
            QComboBox {{
                background-color: {theme.input_bg};
                color: {theme.input_text};
                border: 1px solid {theme.editor_border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border-color: {theme.accent};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.editor_bg};
                color: {theme.editor_text};
                border: 1px solid {theme.editor_border};
                border-radius: 4px;
                selection-background-color: {theme.accent};
                selection-color: white;
                padding: 4px;
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {theme.accent};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {theme.accent_hover};
            }}
            QListWidget {{
                background-color: transparent;
                border: none;
                font-size: 13px;
            }}
        """)

    def closeEvent(self, event):
        """关闭窗口 -> 最小化到托盘."""
        self.hide()
        event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key_Delete:
            item = self._list.currentItem()
            if item:
                self._delete_task(item.data(Qt.UserRole))
        else:
            super().keyPressEvent(event)


class _TaskRow(QWidget):
    """单行任务控件：拖拽手柄 + 圆点 + 复选框 + 文本."""

    def __init__(self, task: Task, store: DataStore):
        super().__init__()
        self.task_id = task.id
        self._store = store
        self._init_ui(task, store.theme)

    def _init_ui(self, task: Task, theme_key: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        theme = get_theme(theme_key)
        color = CATEGORY_COLORS.get(task.category, theme.text_primary)

        # 拖拽手柄
        handle = QLabel("☰")
        handle.setStyleSheet(f"color: {theme.editor_text}; opacity: 0.5; font-size: 12px;")
        handle.setFixedWidth(16)
        layout.addWidget(handle)

        # 分类圆点
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        dot.setFixedWidth(14)
        layout.addWidget(dot)

        # 复选框
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(task.done)
        self.checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {theme.editor_border};
                border-radius: 3px;
                background: {theme.input_bg};
            }}
            QCheckBox::indicator:checked {{
                background: {theme.accent};
                border-color: {theme.accent};
            }}
        """)
        layout.addWidget(self.checkbox)

        # 任务文本
        text_label = QLabel(task.text)
        if task.done:
            text_label.setStyleSheet(
                f"color: {theme.editor_text};"
                "text-decoration: line-through;"
                "font-size: 13px;"
            )
        else:
            text_label.setStyleSheet(f"color: {theme.editor_text}; font-size: 13px;")
        layout.addWidget(text_label, stretch=1)

        # 分类标签
        cat_label = QLabel(CATEGORY_LABELS.get(task.category, ""))
        cat_label.setStyleSheet(f"""
            color: {color};
            font-size: 12px;
            background: transparent;
            border: 1px solid {color};
            border-radius: 8px;
            padding: 1px 8px;
        """)
        layout.addWidget(cat_label)

        # 双击编辑
        text_label.setCursor(Qt.IBeamCursor)
        text_label.mouseDoubleClickEvent = lambda e: self._start_edit(text_label, task)

    def _start_edit(self, label: QLabel, task: Task):
        theme = get_theme(self._store.theme)
        edit = QLineEdit(task.text)
        edit.setStyleSheet(f"""
            background: {theme.input_bg};
            color: {theme.input_text};
            border: 1px solid {theme.accent};
            border-radius: 2px;
            font-size: 13px;
        """)
        edit.selectAll()
        # 替换 label
        idx = self.layout().indexOf(label)
        self.layout().removeWidget(label)
        label.hide()
        self.layout().insertWidget(idx, edit)
        edit.setFocus()
        self._editing = (edit, label, task, idx)

        edit.returnPressed.connect(self._finish_edit)

        # Escape 取消编辑
        edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if hasattr(self, '_editing') and self._editing and obj == self._editing[0]:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Escape:
                    self._cancel_edit()
                    return True
            elif event.type() == QEvent.FocusOut:
                # 失焦时自动保存
                self._finish_edit()
                return True
        return super().eventFilter(obj, event)

    def _finish_edit(self):
        if not hasattr(self, '_editing') or self._editing is None:
            return
        edit_w, orig_label, orig_task, orig_idx = self._editing
        new_text = edit_w.text().strip()
        if new_text and new_text != orig_task.text:
            self._store.update_task(orig_task.id, text=new_text)
            editor = self.window()
            if isinstance(editor, EditorWindow):
                editor.load_tasks()
                editor.data_changed.emit()
        self._cleanup_edit()

    def _cancel_edit(self):
        self._cleanup_edit()

    def _cleanup_edit(self):
        if not hasattr(self, '_editing') or self._editing is None:
            return
        edit_w, orig_label, orig_task, orig_idx = self._editing
        # Remove edit widget
        idx = self.layout().indexOf(edit_w)
        if idx >= 0:
            self.layout().removeWidget(edit_w)
        edit_w.deleteLater()
        # Restore original label
        orig_label.show()
        self.layout().insertWidget(orig_idx, orig_label)
        self._editing = None
