import json
import os
import random as rnd
from threading import Event
from typing import Any, Callable, Generator, Optional, TypeVar

from matplotlib import pyplot as plt
from PyQt6.QtCore import QDir, QObject, QThread, pyqtSignal
import numpy

from .data import STYLESHEETS_DIR


def load_stylesheet(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()


def load_stylesheets(dir: str = STYLESHEETS_DIR) -> str:
    style_files = [entry for entry in os.listdir(dir) if entry.endswith(".qss")]

    if len(style_files) == 0:
        raise Exception("There is no styles")

    return "\n".join(load_stylesheet(os.path.join(dir, f)) for f in style_files)


def save_json(data: dict, dir: str, filename: str) -> None:
    if not os.path.isdir(dir):
        os.mkdir(dir)

    base_ext = ".json"
    name, ext = os.path.splitext(filename)
    if not ext:
        ext = base_ext

    ind = sum(filename in entry for entry in os.listdir(dir))
    if ind != 0:
        name = f"{name} {ind}"

    filepath = os.path.join(dir, f"{name}{ext}")

    with open(filepath, mode="w+") as f:
        f.write(json.dumps(data))


def register_resources(dir: str):
    for d in dir:
        QDir.addSearchPath(os.path.dirname(d), d)


def generate_colors(n: int) -> Generator:
    for _ in range(n):
        yield numpy.random.rand(3)


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


StoppableFunction = Callable[[Event, TypeVar("T")], TypeVar("E")]


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
