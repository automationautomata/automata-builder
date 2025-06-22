from os.path import dirname, join

BASE_DIR = dirname(dirname(__file__))

SAVES_DIR = join(BASE_DIR, "saves")

LOCALE_DIR = join(BASE_DIR, "locale")

STYLESHEETS_DIR = join(BASE_DIR, "styles")

VIEW_FILE_NAME = "automata"

BASE_LANG = 'en'

SESSION_EXT = 'session'