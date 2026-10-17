"""Temporary test settings: isolated SQLite so the shared Postgres is untouched."""
from myblog.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
