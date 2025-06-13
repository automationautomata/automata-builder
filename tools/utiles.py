import os
from os.path import dirname, join

STYLESHEETS_DIR = join(dirname(dirname(__file__)), "styles")

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
