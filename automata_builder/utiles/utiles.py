import json
import os
from os.path import dirname, join
from threading import Event
from typing import Any, Callable, Generator, Optional, TypeVar

from matplotlib import pyplot as plt
from PyQt6.QtCore import QDir, QObject, QThread, pyqtSignal

from .data import IMAGES_DIRS, STYLESHEETS_DIR


def load_stylesheet(filename: str):
    if not filename.endswith(".qss"):
        filename = f"{filename}.qss"

    path = join(STYLESHEETS_DIR, filename)
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def load_stylesheets():
    style_files = [
        entry for entry in os.listdir(STYLESHEETS_DIR) if entry.endswith(".qss")
    ]

    if len(style_files) == 0:
        raise Exception("There is no styles")

    return "\n".join(load_stylesheet(file) for file in style_files)


def save_json(data: dict, path: str, filename: str) -> None:
    if not os.path.isdir(path):
        os.mkdir(path)

    base_ext = ".json"
    name, ext = os.path.splitext(filename)
    if not ext:
        ext = base_ext

    ind = sum(filename in entry for entry in os.listdir(path))
    if ind != 0:
        name = f"{name} {ind}"

    filepath = os.path.join(path, f"{name}{ext}")

    with open(filepath, mode="w+") as f:
        f.write(json.dumps(data))


def register_resources():
    for dir in IMAGES_DIRS:
        QDir.addSearchPath(dirname(dir), dir)


def generate_colors(n: int) -> Generator:
    cmap = plt.get_cmap("tab20")
    for i in range(n):
        yield cmap(i % cmap.N)


class textfilter:
    def __init__(
        self,
        condition: Callable[[str], bool],
        get_text: Callable[[], str],
        set_text: Callable[[str], Any],
    ) -> None:
        self.prev_text = get_text()

        self.set_text = set_text
        self.get_text = get_text
        self.condition = condition

    def __call__(self) -> None:
        text = self.get_text()
        if self.condition(text):
            self.prev_text = text
            return
        self.set_text(self.prev_text)


T = TypeVar("T")
E = TypeVar("E")
StoppableFunction = Callable[[Event, T], E]


class WorkerThread(QThread):
    finished = pyqtSignal()
    result_ready = pyqtSignal(object)

    def __init__(
        self,
        func: StoppableFunction,
        parent: Optional[QObject] = None,
        *func_args,
        **func_kwargs,
    ) -> None:
        super().__init__(parent)
        self.cond = Event()
        self.func = func
        self.args = func_args
        self.kwargs = func_kwargs

    def run(self):
        result = self.func(self.cond, *self.args, **self.kwargs)
        self.result_ready.emit(result)
        self.finished.emit()

    def stop(self) -> None:
        self.cond.set()
