"""主题定义：暗夜 / 明亮 / 毛玻璃."""
from __future__ import annotations


CATEGORY_COLORS = {
    "now": "#ff4757",
    "fire": "#ff6348",
    "follow": "#1e90ff",
    "done": "#2ed573",
    "memo": "#ff6b81",
}


class Theme:
    """单个主题的样式配置."""

    def __init__(self, name: str, overlay_bg: str, editor_bg: str,
                 editor_text: str, editor_border: str, row_hover: str,
                 input_bg: str, input_text: str, text_primary: str,
                 accent: str, accent_hover: str):
        self.name = name
        self.overlay_bg = overlay_bg
        self.editor_bg = editor_bg
        self.editor_text = editor_text
        self.editor_border = editor_border
        self.row_hover = row_hover
        self.input_bg = input_bg
        self.input_text = input_text
        self.text_primary = text_primary
        self.accent = accent
        self.accent_hover = accent_hover


THEMES = {
    "dark": Theme(
        name="暗夜",
        overlay_bg="rgba(20, 20, 35, 0.88)",
        editor_bg="#2b2b2b",
        editor_text="#cccccc",
        editor_border="#444444",
        row_hover="#3a3a3a",
        input_bg="#444444",
        input_text="#ffffff",
        text_primary="#dddddd",
        accent="#0e639c",
        accent_hover="#1177bb",
    ),
    "light": Theme(
        name="明亮",
        overlay_bg="rgba(255, 255, 255, 0.90)",
        editor_bg="#f5f5f5",
        editor_text="#333333",
        editor_border="#dddddd",
        row_hover="#e8e8e8",
        input_bg="#ffffff",
        input_text="#333333",
        text_primary="#333333",
        accent="#0e639c",
        accent_hover="#1177bb",
    ),
    "glass": Theme(
        name="毛玻璃",
        overlay_bg="rgba(30, 30, 45, 0.55)",
        editor_bg="rgba(30, 30, 30, 0.92)",
        editor_text="#dddddd",
        editor_border="rgba(255, 255, 255, 0.15)",
        row_hover="rgba(255, 255, 255, 0.08)",
        input_bg="rgba(255, 255, 255, 0.12)",
        input_text="#ffffff",
        text_primary="#ffffff",
        accent="#0e639c",
        accent_hover="#1177bb",
    ),
}


def get_theme(key: str) -> Theme:
    return THEMES.get(key, THEMES["dark"])
