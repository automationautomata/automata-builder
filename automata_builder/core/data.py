from os.path import dirname, join

import userpaths

BASE_LANG = "en"

BASE_DIR = dirname(dirname(__file__))

LOCALE_DIR = join(BASE_DIR, "locale")

STYLESHEETS_DIR = join(BASE_DIR, "styles")

RESOURCES_DIRS = (join(BASE_DIR, "images"),)

DATA_DIR = join(userpaths.get_my_documents(), "automata builder")

SESSIONS_DIR = join(DATA_DIR, "sessions")

VIEW_FILE_NAME = "automata"

SESSION_EXT = "session"

AUTOMATA_EXT = "automata"
