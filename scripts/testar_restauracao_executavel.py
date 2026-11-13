
import os
import sqlite3
import sys
from pathlib import Path

# Permite executar o script dentro da pasta scripts/
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROJETO))

import criptografia

base = (
    Path(os.environ["LOCALAPPDATA"])
    / "BibliotecaCristopolis"
    / "data"
)

# Utilizar a chave já existente
criptografia.ARQUIVO_CHAVE = base / "chave_backup.key"

if not criptografia.ARQUIVO_CHAVE.is_file():
    raise FileNotFoundError(
        "Chave de criptografia não encontrada."
    )

# Solicitar o caminho do backup criptografado
caminho = input(
    "Informe o caminho do backup .db.enc: "
).strip().strip('"')

origem = Path(caminho)

if not origem.is_file() or not origem.name.endswith(".db.enc"):
    raise FileNotFoundError(
        "Backup criptografado não encontrado ou inválido."
    )

# Restaurar em pasta isolada
pasta_teste = base / "teste_restauracao"
pasta_teste.mkdir(parents=True, exist_ok=True)

destino = pasta_teste / "biblioteca_restaurada_drive.db"

if destino.exists():
    raise FileExistsError(
        "Já existe um banco restaurado de teste. "
        "Nenhum arquivo foi substituído."
    )

# Descriptografar backup
criptografia.descriptografar_backup(origem, destino)

# Verificar integridade
with sqlite3.connect(
    f"file:{destino.as_posix()}?mode=ro",
    uri=True
) as conexao:
    integridade = conexao.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    livros = conexao.execute(
        "SELECT COUNT(*) FROM livro"
    ).fetchone()[0]

    leitores = conexao.execute(
        "SELECT COUNT(*) FROM usuario"
    ).fetchone()[0]

print("Integridade:", integridade)
print("Livros recuperados:", livros)
print("Leitores recuperados:", leitores)

if integridade != "ok":
    raise RuntimeError(
        "Falha na integridade do banco restaurado."
    )

print("Teste de restauração concluído com sucesso!")
