"""桌面显示面板：右侧 overlay，鼠标穿透，桌面层级."""
from __future__ import annotations

import sys
import traceback
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QElapsedTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt5.QtGui import QFont, QFontMetrics

from data import DataStore
from theme import get_theme

FONT_SIZE = 13
TOPMOST_INTERVAL = 5 * 60 * 1000
FOREGROUND_CHECK_INTERVAL = 300
SCREEN_CHECK_INTERVAL = 3 * 1000
MIN_TOPMOST_DURATION = 2000

DEBUG = False

def _log(msg: str):
    if DEBUG:
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}", flush=True)


# ── 预初始化 ctypes，设置正确的函数签名 ──

def _init_win32():
    """初始化 Win32 API 函数签名（64位兼容），成功返回 user32/kernel32，失败返回 None."""
    if sys.platform != 'win32':
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # BOOL SetWindowPos(HWND, HWND, int, int, int, int, UINT)
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND,
        wintypes.INT, wintypes.INT,
        wintypes.INT, wintypes.INT,
        wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL

    # BOOL ShowWindow(HWND, int)
    user32.ShowWindow.argtypes = [wintypes.HWND, wintypes.INT]
    user32.ShowWindow.restype = wintypes.BOOL

    # HWND GetForegroundWindow()
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND

    # LONG GetWindowLongW(HWND, int)
    user32.GetWindowLongW.argtypes = [wintypes.HWND, wintypes.INT]
    user32.GetWindowLongW.restype = wintypes.LONG

    # LONG SetWindowLongW(HWND, int, LONG)
    user32.SetWindowLongW.argtypes = [wintypes.HWND, wintypes.INT, wintypes.LONG]
    user32.SetWindowLongW.restype = wintypes.LONG

    # DWORD GetLastError()
    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD

    return user32, kernel32


_WIN32 = _init_win32()


def _get_last_error() -> int:
    if _WIN32 is None:
        return -1
    _, kernel32 = _WIN32
    return kernel32.GetLastError()


class OverlayPanel(QWidget):
    """桌面右侧任务显示面板."""

    refresh_requested = pyqtSignal()

    def __init__(self, store: DataStore):
        super().__init__()
        _log("OverlayPanel.__init__ 开始")
        self._store = store
        self._click_through_done = False
        self._preferred_screen_name: str = ""
        self._is_topmost = False
        self._topmost_since = QElapsedTimer()

        self._init_ui()
        self._apply_theme()
        self.refresh()

        # 记录用户初始选择的屏幕名称（后续不会被 fallback 覆写）
        screens = QApplication.screens()
        idx = min(self._store.screen_index, len(screens) - 1)
        self._preferred_screen_name = screens[idx].name() if screens else ""
        _log(f"初始首选屏幕: '{self._preferred_screen_name}' (index={idx})")

        app = QApplication.instance()
        if app:
            app.screenAdded.connect(self._on_screen_changed)
            app.screenRemoved.connect(self._on_screen_changed)

        self._screen_timer = QTimer(self)
        self._screen_timer.timeout.connect(self._check_screen)
        self._screen_timer.start(SCREEN_CHECK_INTERVAL)

        self._fg_timer = QTimer(self)
        self._fg_timer.timeout.connect(self._check_foreground)
        self._fg_timer.start(FOREGROUND_CHECK_INTERVAL)

        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self._bring_to_front)
        self._topmost_timer.start(TOPMOST_INTERVAL)

        QTimer.singleShot(1000, self._bring_to_front)
        _log("OverlayPanel.__init__ 完成")

    # ═══════════════════════════════════════════════════════════
    #  屏幕切换
    # ═══════════════════════════════════════════════════════════

    def _on_screen_changed(self, screen):
        _log(f"信号: _on_screen_changed({screen.name()})")
        self._dump_screens()
        self._restore_preferred_screen()

    def _check_screen(self):
        try:
            screens = QApplication.screens()
            if not screens:
                return
            idx = self._store.screen_index
            if idx >= len(screens):
                _log(f"⚠ 索引越界: idx={idx} >= len={len(screens)}")
                self._restore_preferred_screen()
                return
            geo = screens[idx].availableGeometry()
            if geo.width() < 100 or geo.height() < 100:
                _log(f"⚠ 几何异常: 屏幕{idx} {geo.width()}x{geo.height()}")
                self._move_to_available_screen(screens)
                return
            if self._preferred_screen_name and screens[idx].name() != self._preferred_screen_name:
                _log(f"⚠ 不在首选屏幕: 当前={screens[idx].name()} 首选={self._preferred_screen_name}")
                self._restore_preferred_screen()
        except Exception:
            _log(f"⚠ _check_screen 异常:\n{traceback.format_exc()}")

    def _move_to_available_screen(self, screens):
        for i, s in enumerate(screens):
            if i == self._store.screen_index:
                continue
            geo = s.availableGeometry()
            if geo.width() >= 100 and geo.height() >= 100:
                _log(f"→ 移至屏幕{i}: {s.name()}")
                self._store.screen_index = i
                self.refresh()
                return
        _log("⚠ 无可用屏幕")

    def set_preferred_screen(self):
        """用户手动切换屏幕后调用，更新首选屏幕名称。"""
        screens = QApplication.screens()
        idx = self._store.screen_index
        if 0 <= idx < len(screens):
            self._preferred_screen_name = screens[idx].name()
            _log(f"用户切换首选屏幕: [{idx}] {self._preferred_screen_name}")

    def _restore_preferred_screen(self):
        """按名称匹配恢复首选屏幕，失败则回退到索引 0。

        重要：fallback 时不会更新 _preferred_screen_name，
        保留用户原始选择以便屏幕重新连接时能找回来。"""
        screens = QApplication.screens()
        if not screens:
            return
        # 优先按名称匹配用户原始选择
        if self._preferred_screen_name:
            for i, s in enumerate(screens):
                if s.name() == self._preferred_screen_name:
                    if self._store.screen_index != i:
                        _log(f"→ 恢复首选屏幕{i}: {s.name()}")
                        self._store.screen_index = i
                        self.refresh()
                    return
            _log(f"⚠ 首选屏幕 '{self._preferred_screen_name}' 不在列表中，尝试回退")
        # 回退：当前索引越界时切到屏幕 0（不更新 _preferred_screen_name）
        if self._store.screen_index >= len(screens):
            _log(f"→ 索引回退: {self._store.screen_index} → 0")
            self._store.screen_index = 0
            self.refresh()

    def _dump_screens(self):
        screens = QApplication.screens()
        _log(f"  [屏幕列表] 共{len(screens)}个, idx={self._store.screen_index}, preferred='{self._preferred_screen_name}'")
        for i, s in enumerate(screens):
            geo = s.availableGeometry()
            cur = "←当前" if i == self._store.screen_index else ""
            pref = "★首选" if s.name() == self._preferred_screen_name else ""
            _log(f"    [{i}] {s.name()} {geo.width()}x{geo.height()} {cur}{pref}")

    # ═══════════════════════════════════════════════════════════
    #  Z-order 管理：使用 Qt WindowStaysOnTopHint（更可靠）
    # ═══════════════════════════════════════════════════════════

    def _bring_to_front(self):
        """通过 Qt flag + Win32 API 双保险置顶."""
        _log(f"_bring_to_front: is_topmost={self._is_topmost}")

        # 方案1：Qt WindowStaysOnTopHint
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.show()  # 必需：window flag 变更后需要重新 show
        self._is_topmost = True
        self._topmost_since.start()
        _log(f"  Qt WindowStaysOnTopHint=True, show() 执行完毕")

        # 方案2：Win32 API 补充（如果 Qt flag 不够）
        if _WIN32 is not None:
            user32, _ = _WIN32
            hwnd = self._get_valid_hwnd()
            if hwnd is not None:
                ret = user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0,
                                          0x0002 | 0x0001 | 0x0010)
                err = _get_last_error() if ret == 0 else 0
                _log(f"  Win32 SetWindowPos(TOPMOST) → ret={ret}, err={err}")

    def _check_foreground(self):
        if not self._is_topmost:
            return
        if self._topmost_since.isValid() and self._topmost_since.elapsed() < MIN_TOPMOST_DURATION:
            return
        if _WIN32 is None:
            return
        try:
            user32, _ = _WIN32
            foreground = user32.GetForegroundWindow()
            our_hwnd = int(self.winId())
            if foreground and foreground != our_hwnd:
                _log(f"前台切换: overlay={our_hwnd} foreground={foreground} → 让位")

                # 方案1：Qt flag
                self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
                self.show()

                # 方案2：Win32 降为非置顶
                ret = user32.SetWindowPos(our_hwnd, -2, 0, 0, 0, 0,
                                          0x0002 | 0x0001 | 0x0010)
                err = _get_last_error() if ret == 0 else 0
                _log(f"  SetWindowPos(NOTOPMOST) → ret={ret}, err={err}")

                self._is_topmost = False
        except Exception:
            _log(f"⚠ _check_foreground 异常:\n{traceback.format_exc()}")

    def _get_valid_hwnd(self):
        try:
            hwnd = int(self.winId())
            return hwnd if hwnd != 0 else None
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════════════════════

    def _init_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint  # 初始就是置顶的
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._label = QLabel()
        self._label.setTextFormat(Qt.RichText)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._layout.addWidget(self._label)

    def _ensure_click_through(self):
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
            _log(f"_ensure_click_through: hwnd={hwnd}, 原样式=0x{ex_style:08X}")
            ex_style |= WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            _log(f"_ensure_click_through: 新样式=0x{ex_style:08X}")
            self._click_through_done = True
        except Exception:
            _log(f"⚠ _ensure_click_through 异常:\n{traceback.format_exc()}")

    # ═══════════════════════════════════════════════════════════
    #  布局与渲染
    # ═══════════════════════════════════════════════════════════

    def _measure_text(self):
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
        # 注意：不在这里更新 _preferred_screen_name
        # 它只在 __init__ 初始化和用户手动切换屏幕时更新
        # 避免 fallback 时覆写用户的原始选择
        max_text_width, line_height, line_count = self._measure_text()
        panel_width = max(160, min(max_text_width + 48, screen.width() // 3))
        panel_height = min(line_count * line_height + 36, int(screen.height() * 0.7))
        x = screen.right() - panel_width - 10
        y = screen.top() + (screen.height() - panel_height) // 2
        self.setGeometry(x, y, panel_width, panel_height)
        _log(f"_position: screen={idx}({self._preferred_screen_name}) pos=({x},{y}) {panel_width}x{panel_height}")

    def _refresh(self):
        theme = get_theme(self._store.theme)
        font = QFont("Microsoft YaHei", FONT_SIZE)
        tasks = self._store.get_active_tasks()
        if not tasks:
            self._label.setFont(font)
            self._label.setAlignment(Qt.AlignCenter)
            c = theme.text_primary.lstrip("#")
            if len(c) == 6:
                r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
                self._label.setText(f'<span style="color:rgba({r},{g},{b},128);">暂无进行中的任务</span>')
            else:
                self._label.setText(f'<span style="color:{theme.text_primary};">暂无进行中的任务</span>')
        else:
            self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lines = []
            for task in tasks:
                color = self._store.category_colors.get(task.category, theme.text_primary)
                lines.append(f'<span style="color:{color};">●  {task.text}</span>')
            self._label.setFont(font)
            self._label.setText("<br>".join(lines))
        self._position()

    def _apply_theme(self):
        theme = get_theme(self._store.theme)
        self.setStyleSheet(f"background: {theme.overlay_bg}; border-radius: 12px;")

    def refresh(self):
        self._apply_theme()
        self._refresh()
        self._ensure_click_through()
