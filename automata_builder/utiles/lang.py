import os
from os.path import join

import yaml

from automata_builder.utiles.data import BASE_LANG, LOCALE_DIR


def load_locales(path):
    """
    Loads and merges all YAML files in the specified directory.
    If no YAML files are found, returns an empty dictionary.
    """
    yaml_files = [f for f in os.listdir(path) if f.endswith((".yml", ".yaml"))]

    if not yaml_files:
        return {}

    merged_data = {}
    for yaml_file in yaml_files:
        file_path = join(path, yaml_file)
        lang, _ = yaml_file.split(".")
        with open(file_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
            merged_data[lang] = data

    return merged_data


locale = load_locales(LOCALE_DIR)

current_lang = BASE_LANG


def getlocale(name):
    return locale[current_lang][name]
