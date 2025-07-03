from os.path import dirname, join

import userpaths

BASE_DIR = dirname(dirname(__file__))

SAVES_DIR = join(userpaths.get_my_documents(), "automata_viewer")

LOCALE_DIR = join(BASE_DIR, "locale")

SESSIONS_DIR = join(SAVES_DIR, "sessions")

STYLESHEETS_DIR = join(BASE_DIR, "styles")

VIEW_FILE_NAME = "automata"

BASE_LANG = "en"

SESSION_EXT = "session"

AUTOMATA_EXT = "automata"
