
import os
import sys
from pathlib import Path

# Permite importar módulos da raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
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

ID_PASTA = os.environ.get("BIBLIOTECA_DRIVE_FOLDER_ID")

if not ID_PASTA:
    raise RuntimeError(
        "A variável BIBLIOTECA_DRIVE_FOLDER_ID "
        "não está configurada. Configure-a no Windows "
        "e reinicie o terminal."
    )

try:
    servico = drive_backup.conectar_google_drive()

    pasta = servico.files().get(
        fileId=ID_PASTA,
        fields="id,name,mimeType",
    ).execute()

    if pasta.get("mimeType") == "application/vnd.google-apps.folder":
        print("Pasta encontrada:", pasta["name"])
        print("Acesso de leitura: OK")
    else:
        print("O ID informado não corresponde a uma pasta.")

except Exception as erro:
    print("Não foi possível acessar a pasta.")
    print("Detalhes:", erro)
    raise SystemExit(1)
