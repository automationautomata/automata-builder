import os
from os.path import join

import yaml

from .data import BASE_LANG, LOCALE_DIR


def load_locales(path):
    """
    Loads and merges all YAML files in the specified directory.
    If no YAML files are found, returns an empty dictionary.
    """
    # Find all YAML files in the directory
    yaml_files = [f for f in os.listdir(path) if f.endswith((".yml", ".yaml"))]

    # If no YAML files are found, return an empty dictionary
    if not yaml_files:
        return {}

    # Load and merge all YAML files
    merged_data = {}
    for yaml_file in yaml_files:
        file_path = join(path, yaml_file)
        lang, _ = yaml_file.split(".")
        with open(file_path, "r", encoding="utf-8") as file:
            # Load YAML data, default to empty dict if None
            data = yaml.safe_load(file) or {}
            merged_data[lang] = data

    return merged_data


locale = load_locales(LOCALE_DIR)

current_lang = BASE_LANG


def getlocale(name):
    return locale[current_lang][name]
