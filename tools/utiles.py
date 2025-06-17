import json
import os
from os.path import join

from data import SAVE_DIR, STYLESHEETS_DIR, VIEW_FILE_NAME


def load_stylesheet(filename: str):
    if not filename.endswith(".qss"):
        filename = f"{filename}.qss"

    path = join(STYLESHEETS_DIR, filename)
    with open(path, "r") as stylesheet_file:
        return stylesheet_file.read()


def load_stylesheets():
    style_files = [
        entry for entry in os.listdir(STYLESHEETS_DIR) if entry.endswith(".qss")
    ]

    if len(style_files) == 0:
        raise Exception("There is no styles")

    return "\n".join(load_stylesheet(file) for file in style_files)


def save_view(data: dict) -> None:
    if not os.path.isdir(SAVE_DIR):
        os.mkdir(SAVE_DIR)
    ind = len(os.listdir(SAVE_DIR))
    filepath = os.path.join(SAVE_DIR, f"{VIEW_FILE_NAME} {ind}")

    with open(filepath, mode="w+") as f:
        f.write(json.dumps(data))
