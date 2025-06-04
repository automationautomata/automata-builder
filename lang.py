import os
from functools import reduce
from os.path import dirname, join

import yaml


def load_locales(path):
    """
    Loads and merges all YAML files in the specified directory.
    If no YAML files are found, returns an empty dictionary.
    """
    # Find all YAML files in the directory
    yaml_files = [
        f for f in os.listdir(path) if f.endswith(".yml") or f.endswith(".yaml")
    ]

    # If no YAML files are found, return an empty dictionary
    if not yaml_files:
        return {}

    # Recursive dictionary merge
    def merge(d1, d2):
        for key, value in d2.items():
            if key in d1 and isinstance(d1[key], dict) and isinstance(value, dict):
                # If both values are dictionaries, merge them recursively
                merge(d1[key], value)
            else:
                # Otherwise, overwrite or add the value from d2 to d1
                d1[key] = value
        return d1

    # Load and merge all YAML files
    merged_data = {}
    for yaml_file in yaml_files:
        file_path = join(path, yaml_file)
        with open(file_path, "r", encoding="utf-8") as file:
            # Load YAML data, default to empty dict if None
            data = yaml.safe_load(file) or {}
            merged_data = merge(merged_data, data)

        return merged_data


def get_locale_str(dictionary, keys, default=None):
    return reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        keys.split("."),
        dictionary,
    )


locale = load_locales(join(dirname(__file__), "locale"))
getstr = lambda lang, path: get_locale_str(locale, f"{lang}.{path}")  # noqa: E731
