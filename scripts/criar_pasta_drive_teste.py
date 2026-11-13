
import os
import sys
from pathlib import Path

# Localiza a raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

# Permite importar os módulos da raiz
sys.path.insert(0, str(RAIZ_PROJETO))

import drive_backup


pasta_app = (
    Path(os.environ["LOCALAPPDATA"])
    / "BibliotecaCristopolis"
)

drive_backup.ARQUIVO_CREDENCIAIS = (
    pasta_app / "client_secret.json"
)

drive_backup.ARQUIVO_TOKEN = (
    pasta_app / "token.json"
)

servico = drive_backup.conectar_google_drive()

metadados = {
    "name": "BibliotecaCristopolis-Testes-API",
    "mimeType": "application/vnd.google-apps.folder",
}

pasta = servico.files().create(
    body=metadados,
    fields="id,name",
).execute()

print("Pasta criada:", pasta["name"])
print("ID da pasta:", pasta["id"])
