"""数据层：Task 数据类和 JSON 文件读写."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Optional


CATEGORIES = ["now", "fire", "follow", "done", "memo"]

CATEGORY_LABELS = {
    "now": "进行中",
    "fire": "紧急",
    "follow": "跟进",
    "done": "已完成",
    "memo": "备忘",
}

DEFAULT_CATEGORY_COLORS = {
    "now": "#ff4757",
    "fire": "#ff6348",
    "follow": "#1e90ff",
    "done": "#2ed573",
    "memo": "#ff6b81",
}


@dataclass
class Task:
    """单条任务."""
    text: str
    category: str = "now"
    done: bool = False
    sort: int = 0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "category": self.category,
            "done": self.done,
            "sort": self.sort,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Task:
        return cls(
            id=d.get("id", uuid.uuid4().hex[:8]),
            text=d["text"],
            category=d.get("category", "now"),
            done=d.get("done", False),
            sort=d.get("sort", 0),
        )


class DataStore:
    """JSON 文件数据存储."""

    def __init__(self, filepath: Optional[str] = None):
        if filepath is None:
            filepath = os.path.join(os.path.expanduser("~"), "备忘.json")
        self._filepath = filepath
        self._tasks: list[Task] = []
        self._theme: str = "dark"
        self._screen_index: int = 0
        self._category_colors: dict = dict(DEFAULT_CATEGORY_COLORS)
        self._load()

    @property
    def tasks(self) -> list[Task]:
        return self._tasks

    @property
    def theme(self) -> str:
        return self._theme

    @theme.setter
    def theme(self, value: str):
        self._theme = value
        self._save()

    @property
    def screen_index(self) -> int:
        return self._screen_index

    @screen_index.setter
    def screen_index(self, value: int):
        self._screen_index = value
        self._save()

    @property
    def category_colors(self) -> dict:
        return dict(self._category_colors)

    def set_category_colors(self, colors: dict):
        """批量设置分类颜色并保存."""
        self._category_colors = dict(colors)
        self._save()

    def _load(self):
        if not os.path.exists(self._filepath):
            self._save()
            return
        with open(self._filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._theme = data.get("theme", "dark")
        self._screen_index = data.get("screen_index", 0)
        saved_colors = data.get("category_colors", {})
        self._category_colors = {**DEFAULT_CATEGORY_COLORS, **saved_colors}
        self._tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        self._renumber()

    def _save(self):
        data = {
            "version": 1,
            "theme": self._theme,
            "screen_index": self._screen_index,
            "category_colors": self._category_colors,
            "tasks": [t.to_dict() for t in self._tasks],
        }
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_task(self, text: str, category: str = "now") -> Task:
        task = Task(text=text, category=category, sort=len(self._tasks))
        self._tasks.append(task)
        self._save()
        return task

    def update_task(self, task_id: str, **kwargs):
        for t in self._tasks:
            if t.id == task_id:
                for k, v in kwargs.items():
                    if hasattr(t, k):
                        setattr(t, k, v)
                self._save()
                return

    def delete_task(self, task_id: str):
        self._tasks = [t for t in self._tasks if t.id != task_id]
        self._renumber()
        self._save()

    def reorder(self, task_ids: list[str]):
        """按传入的 ID 顺序重新编号 sort 字段."""
        order_map = {tid: i for i, tid in enumerate(task_ids)}
        for t in self._tasks:
            if t.id in order_map:
                t.sort = order_map[t.id]
        self._save()

    def get_active_tasks(self) -> list[Task]:
        """获取未完成的任务，按 sort 排序."""
        return sorted(
            [t for t in self._tasks if not t.done],
            key=lambda t: t.sort,
        )

    def _renumber(self):
        for i, t in enumerate(self._tasks):
            t.sort = i
