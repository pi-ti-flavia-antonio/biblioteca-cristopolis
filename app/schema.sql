CREATE TABLE IF NOT EXISTS categoria (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT NOT NULL UNIQUE,
    descricao    TEXT
);

CREATE TABLE IF NOT EXISTS livro (
    id_livro         INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo           TEXT    NOT NULL,
    autor            TEXT    NOT NULL,
    isbn             TEXT,
    ano_publicacao   INTEGER,
    id_categoria     INTEGER REFERENCES categoria (id_categoria) ON DELETE SET NULL,
    quantidade_total INTEGER NOT NULL CHECK (quantidade_total >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_livro_isbn ON livro (isbn) WHERE isbn IS NOT NULL;

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT NOT NULL,
    cpf          TEXT,
    telefone     TEXT,
    email        TEXT,
    endereco     TEXT,
    tipo_usuario TEXT
);

CREATE TABLE IF NOT EXISTS funcionario (
    id_funcionario INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT NOT NULL,
    cargo          TEXT,
    login          TEXT NOT NULL UNIQUE,
    senha_hash     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS emprestimo (
    id_emprestimo           INTEGER PRIMARY KEY AUTOINCREMENT,
    data_emprestimo         TEXT    NOT NULL,
    data_devolucao_prevista TEXT    NOT NULL,
    data_devolucao_real     TEXT,
    status                  TEXT    NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'devolvido')),
    id_usuario              INTEGER NOT NULL REFERENCES usuario (id_usuario),
    id_livro                INTEGER NOT NULL REFERENCES livro (id_livro) ON DELETE RESTRICT,
    id_funcionario          INTEGER REFERENCES funcionario (id_funcionario)
);

CREATE INDEX IF NOT EXISTS ix_emprestimo_livro_status ON emprestimo (id_livro, status);

CREATE TABLE IF NOT EXISTS reserva (
    id_reserva   INTEGER PRIMARY KEY AUTOINCREMENT,
    data_reserva TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa', 'cancelada', 'concluida')),
    id_usuario   INTEGER NOT NULL REFERENCES usuario (id_usuario),
    id_livro     INTEGER NOT NULL REFERENCES livro (id_livro) ON DELETE RESTRICT,
    aviso_visto  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_reserva_livro_status ON reserva (id_livro, status);
