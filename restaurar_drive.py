
import sqlite3
from pathlib import Path
from contextlib import closing

from googleapiclient.http import MediaIoBaseDownload

from drive_backup import conectar_google_drive
from criptografia import descriptografar_backup


BASE_DIR = Path(__file__).resolve().parent

PASTA_RESTAURACAO = BASE_DIR / "data" / "teste_restauracao"

ARQUIVO_CRIPTOGRAFADO = (
    PASTA_RESTAURACAO / "biblioteca_drive.db.enc"
)

BANCO_RESTAURADO = (
    PASTA_RESTAURACAO / "biblioteca_drive_recuperada.db"
)

# ID do backup criptografado enviado ao Google Drive
ID_BACKUP = "1DVEhAH0Tj05wx5PRJk36LAy6YZuZGLmL"


def baixar_e_testar_backup():
    servico = conectar_google_drive()

    PASTA_RESTAURACAO.mkdir(
        parents=True,
        exist_ok=True
    )

    # Evita reutilizar arquivos de testes anteriores
    if ARQUIVO_CRIPTOGRAFADO.exists():
        raise FileExistsError(
            "Já existe um arquivo criptografado de teste."
        )

    if BANCO_RESTAURADO.exists():
        raise FileExistsError(
            "Já existe um banco recuperado de teste."
        )

    requisicao = servico.files().get_media(
        fileId=ID_BACKUP
    )

    with open(ARQUIVO_CRIPTOGRAFADO, "wb") as arquivo:
        downloader = MediaIoBaseDownload(
            arquivo,
            requisicao
        )

        concluido = False

        while not concluido:
            progresso, concluido = downloader.next_chunk()

            if progresso:
                print(
                    f"Download: {progresso.progress() * 100:.0f}%"
                )

    print("Backup criptografado baixado com sucesso!")

    # Descriptografa utilizando a chave local
    descriptografar_backup(
        ARQUIVO_CRIPTOGRAFADO,
        BANCO_RESTAURADO
    )

    # Confere a integridade do banco recuperado
    with closing(sqlite3.connect(
        f"file:{BANCO_RESTAURADO.as_posix()}?mode=ro",
        uri=True
    )) as banco:

        resultado = banco.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        if resultado is None or resultado[0] != "ok":
            raise RuntimeError(
                "O banco recuperado não passou na verificação."
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

        print("\nTabelas encontradas:")

        for tabela in tabelas:
            print(f"- {tabela[0]}")

    print("\nBackup recuperado com sucesso!")
    print(f"Banco restaurado: {BANCO_RESTAURADO}")
    print("Integridade: OK")


if __name__ == "__main__":
    baixar_e_testar_backup()
