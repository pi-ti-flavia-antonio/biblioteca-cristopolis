
import os
import sys
from pathlib import Path

# Localiza a raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

# Permite importar os módulos da raiz
sys.path.insert(0, str(RAIZ_PROJETO))

import drive_backup


if __name__ == "__main__":
    pasta = (
        Path(os.environ["LOCALAPPDATA"])
        / "BibliotecaCristopolis"
    )

    drive_backup.ARQUIVO_CREDENCIAIS = (
        pasta / "client_secret.json"
    )

    drive_backup.ARQUIVO_TOKEN = (
        pasta / "token.json"
    )

    print("Iniciando autenticação do Google Drive...")

    drive_backup.conectar_google_drive()

    print("Autenticação concluída com sucesso!")