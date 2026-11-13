import os
from pathlib import Path

base = Path(os.environ["LOCALAPPDATA"]) / "BibliotecaCristopolis"

arquivos = {
    "Banco SQLite": base / "data" / "biblioteca.db",
    "Chave de criptografia": base / "data" / "chave_backup.key",
    "Credenciais OAuth": base / "client_secret.json",
    "Token Google Drive": base / "token.json",
}

for nome, caminho in arquivos.items():
    situacao = "OK" if caminho.is_file() else "AUSENTE"
    print(f"{nome}: {situacao}")



id_pasta = os.environ.get("BIBLIOTECA_DRIVE_FOLDER_ID")

if id_pasta:
    print("Pasta de backup do Google Drive: CONFIGURADA")
else:
    print("Pasta de backup do Google Drive: NÃO CONFIGURADA")
    print(
        "Configure a variável BIBLIOTECA_DRIVE_FOLDER_ID "
        "no Windows e reinicie o terminal ou programa."
    )
