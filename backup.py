
import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import closing

from caminhos import caminho_banco, pasta_dados

BANCO_ORIGINAL = caminho_banco()
PASTA_BACKUPS = pasta_dados() / "backups"



def criar_backup():
    if not BANCO_ORIGINAL.exists():
        raise FileNotFoundError(
            f"Banco de dados não encontrado: {BANCO_ORIGINAL}"
        )

    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)

    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    arquivo_backup = PASTA_BACKUPS / f"biblioteca_{data_hora}.db"

    try:
        # Cria o backup e fecha as conexões corretamente
        with closing(sqlite3.connect(BANCO_ORIGINAL)) as origem:
            with closing(sqlite3.connect(arquivo_backup)) as destino:
                origem.backup(destino)

        # Verifica a integridade e fecha a conexão
        with closing(sqlite3.connect(arquivo_backup)) as verificacao:
            resultado = verificacao.execute(
                "PRAGMA integrity_check"
            ).fetchone()

        if resultado is None or resultado[0] != "ok":
            raise RuntimeError(
                "O backup não passou na verificação."
            )

        print("Backup criado e verificado com sucesso!")
        print(f"Arquivo: {arquivo_backup}")
        print(f"Tamanho: {arquivo_backup.stat().st_size} bytes")

        return arquivo_backup

    except Exception:
        arquivo_backup.unlink(missing_ok=True)
        raise



if __name__ == "__main__":
    criar_backup()
