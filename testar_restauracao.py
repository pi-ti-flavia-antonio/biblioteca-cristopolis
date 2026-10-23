
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

BANCOS = {
    "Original": BASE_DIR / "data" / "biblioteca.db",
    "Restaurado": (
        BASE_DIR
        / "data"
        / "teste_restauracao"
        / "biblioteca_restaurada.db"
    ),
}


def contar_registros(caminho):
    with sqlite3.connect(caminho) as banco:
        integridade = banco.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integridade != "ok":
            raise RuntimeError(
                f"Banco com problema: {caminho}"
            )

        tabelas = banco.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        contagens = {}

        for (tabela,) in tabelas:
            nome_seguro = '"' + tabela.replace('"', '""') + '"'
            quantidade = banco.execute(
                f"SELECT COUNT(*) FROM {nome_seguro}"
            ).fetchone()[0]

            contagens[tabela] = quantidade

        return contagens


def main():
    resultados = {
        nome: contar_registros(caminho)
        for nome, caminho in BANCOS.items()
    }

    original = resultados["Original"]
    restaurado = resultados["Restaurado"]

    print("Comparação de registros")
    print("-" * 42)

    todas_tabelas = sorted(set(original) | set(restaurado))
    iguais = True

    for tabela in todas_tabelas:
        qtd_original = original.get(tabela, 0)
        qtd_restaurado = restaurado.get(tabela, 0)
        status = "OK" if qtd_original == qtd_restaurado else "DIFERENTE"

        if status != "OK":
            iguais = False

        print(
            f"{tabela}: original={qtd_original}, "
            f"restaurado={qtd_restaurado} [{status}]"
        )

    print("-" * 42)

    if iguais:
        print("SUCESSO: todas as contagens são iguais.")
    else:
        print("ATENÇÃO: existem diferenças entre os bancos.")


if __name__ == "__main__":
    main()
