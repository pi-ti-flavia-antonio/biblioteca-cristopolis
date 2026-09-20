import sqlite3
from pathlib import Path

from flask import current_app, g

from .texto import normalizar

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_db():
    if "db" not in g:
        conexao = sqlite3.connect(current_app.config["DATABASE"])
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.create_function("normalizar", 1, normalizar, deterministic=True)
        g.db = conexao
    return g.db


def close_db(_erro=None):
    conexao = g.pop("db", None)
    if conexao is not None:
        conexao.close()


def init_db():
    get_db().executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def init_app(app):
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
