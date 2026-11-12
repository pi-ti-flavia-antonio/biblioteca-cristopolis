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


def _atualizar_bancos_antigos(db):
    """Bancos criados antes de uma coluna existir ganham a coluna, sem perder dados."""
    novas_colunas = (
        ("reserva", "aviso_visto", "INTEGER NOT NULL DEFAULT 0"),
        ("usuario", "ativo", "INTEGER NOT NULL DEFAULT 1"),
        ("livro", "edicao", "TEXT"),
        ("funcionario", "email_recuperacao", "TEXT"),
        ("usuario", "numero_carteirinha", "INTEGER"),
    )
    for tabela, coluna, definicao in novas_colunas:
        colunas = {linha["name"] for linha in db.execute(f"PRAGMA table_info({tabela})")}
        if coluna not in colunas:
            with db:
                db.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")

    # Cada número de carteirinha só pode existir uma vez. O índice fica aqui, e não no schema,
    # porque um banco antigo só ganha a coluna logo acima.
    with db:
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_usuario_carteirinha ON usuario (numero_carteirinha) "
            "WHERE numero_carteirinha IS NOT NULL"
        )

    # O prazo padrão passou de 30 para 15 dias: empréstimos ativos feitos com o prazo antigo
    # ganham o novo. Só mexe nos que têm exatamente 30 dias, então repetir não altera nada.
    with db:
        db.execute(
            "UPDATE emprestimo SET data_devolucao_prevista = date(data_emprestimo, '+15 days') "
            "WHERE status = 'ativo' AND date(data_devolucao_prevista) = date(data_emprestimo, '+30 days')"
        )


def init_db():
    db = get_db()
    db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    _atualizar_bancos_antigos(db)


def init_app(app):
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
