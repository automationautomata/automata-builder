import json
import os
from os.path import join

from data import STYLESHEETS_DIR


def load_stylesheet(filename: str):
    if not filename.endswith(".qss"):
        filename = f"{filename}.qss"

    path = join(STYLESHEETS_DIR, filename)
    with open(path, "r", encoding='utf-8',) as stylesheet_file:
        return stylesheet_file.read()


def load_stylesheets():
    style_files = [
        entry for entry in os.listdir(STYLESHEETS_DIR) if entry.endswith(".qss")
    ]

    if len(style_files) == 0:
        raise Exception("There is no styles")

    return "\n".join(load_stylesheet(file) for file in style_files)


def json_to_file(data: dict, path: str, filename: str) -> bool:
    try:
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
    except (OSError, IOError):
        return False

    return True
