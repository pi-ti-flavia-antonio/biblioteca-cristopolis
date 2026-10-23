
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

BANCO_ORIGINAL = BASE_DIR / "data" / "biblioteca.db"
BANCO_RECUPERADO = (
    BASE_DIR
    / "data"
    / "teste_restauracao"
    / "biblioteca_drive_recuperada.db"
)

TABELAS = [
    "categoria",
    "livro",
    "usuario",
    "emprestimo",
    "reserva",
    "funcionario",
]


def contar_registros(caminho_banco):
    if not caminho_banco.is_file():
        raise FileNotFoundError(f"Banco não encontrado: {caminho_banco}")

    conexao = sqlite3.connect(
        caminho_banco.as_uri() + "?mode=ro",
        uri=True,
    )

    try:
        return {
            tabela: conexao.execute(
                f"SELECT COUNT(*) FROM {tabela}"
            ).fetchone()[0]
            for tabela in TABELAS
        }
    finally:
        conexao.close()


original = contar_registros(BANCO_ORIGINAL)
recuperado = contar_registros(BANCO_RECUPERADO)

print("\nCOMPARAÇÃO DOS REGISTROS")
print("-" * 48)
print(f"{'Tabela':<16} {'Original':>10} {'Recuperado':>12}")
print("-" * 48)

for tabela in TABELAS:
    print(
        f"{tabela:<16} "
        f"{original[tabela]:>10} "
        f"{recuperado[tabela]:>12}"
    )

print("-" * 48)

if original == recuperado:
    print("As quantidades de registros são iguais!")
else:
    print("Existem diferenças entre as quantidades.")
    print("Verifique a data do backup recuperado.")
