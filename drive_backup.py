
from pathlib import Path

from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from caminhos import pasta_dados
import sys
import os


BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_CREDENCIAIS = (
    pasta_dados().parent / "client_secret.json"
    if getattr(sys, "frozen", False)
    else BASE_DIR / "client_secret.json"
)


ARQUIVO_TOKEN = (
    pasta_dados().parent / "token.json"
    if getattr(sys, "frozen", False)
    else BASE_DIR / "token.json"
)

ESCOPO = ["https://www.googleapis.com/auth/drive.file"]

ID_PASTA_BACKUP = os.environ.get("BIBLIOTECA_DRIVE_FOLDER_ID")


def conectar_google_drive():
    credenciais = None

    if ARQUIVO_TOKEN.exists():
        credenciais = Credentials.from_authorized_user_file(
            str(ARQUIVO_TOKEN),
            ESCOPO,
        )

    if credenciais and credenciais.expired and credenciais.refresh_token:
        credenciais.refresh(Request())

    if not credenciais or not credenciais.valid:
        fluxo = InstalledAppFlow.from_client_secrets_file(
            str(ARQUIVO_CREDENCIAIS),
            ESCOPO,
        )

        credenciais = fluxo.run_local_server(port=0)

    ARQUIVO_TOKEN.write_text(
        credenciais.to_json(),
        encoding="utf-8",
    )

    servico = build("drive", "v3", credentials=credenciais)

    resultado = servico.about().get(
        fields="user(displayName,emailAddress)"
    ).execute()

    usuario = resultado.get("user", {})

    print("Conexão com o Google Drive realizada com sucesso!")
    print(f"Conta: {usuario.get('emailAddress', 'não identificada')}")

    return servico

def enviar_backup(servico, caminho_backup):
    caminho_backup = Path(caminho_backup)

    if not caminho_backup.is_file():
        raise FileNotFoundError(
            f"Backup não encontrado: {caminho_backup}"
        )

    metadados = {
        "name": caminho_backup.name,
        "mimeType": "application/octet-stream",
}

    if not ID_PASTA_BACKUP:
        raise RuntimeError(
            "A pasta de backup do Google Drive não foi configurada."
        )

    metadados["parents"] = [ID_PASTA_BACKUP]

    arquivo = MediaFileUpload(
        str(caminho_backup),
        mimetype="application/octet-stream",
        resumable=True,
    )

    resultado = servico.files().create(
        body=metadados,
        media_body=arquivo,
        fields="id,name",
    ).execute()

    print("Backup enviado ao Google Drive com sucesso!")
    print(f"Nome: {resultado['name']}")
    print(f"ID: {resultado['id']}")

    return resultado




if __name__ == "__main__":
    from backup import criar_backup
    from criptografia import criptografar_backup
    from controle_backups import (
    registrar_envio,
    ja_enviado,
    limpar_backups_antigos,
)

    # 1. Cria e criptografa um novo backup local
    caminho_backup = criar_backup()

    try:
        caminho_criptografado = criptografar_backup(caminho_backup)
    finally:
        # Remove a cópia temporária sem criptografia
        # somente quando o arquivo criptografado existe
        caminho_esperado = caminho_backup.with_suffix(".db.enc")

        if caminho_esperado.is_file():
            caminho_backup.unlink(missing_ok=True)

    # 2. Localiza os backups criptografados pendentes
    pasta_backups = pasta_dados() / "backups"

    falha_envio = False

    pendentes = sorted(
        arquivo
        for arquivo in pasta_backups.glob("biblioteca_*.db.enc")
        if not ja_enviado(arquivo.name)
    )

    print(f"\nBackups pendentes: {len(pendentes)}")

    if not pendentes:
        print("Nenhum backup pendente.")
    else:
        # 3. Tenta conectar ao Google Drive
        try:
            servico = conectar_google_drive()
        except Exception as erro:
            falha_envio = True
            print(f"Não foi possível conectar ao Google Drive: {erro}")
            print("Os backups criptografados permanecem salvos.")
        else:
            # 4. Envia cada backup pendente
            for arquivo in pendentes:
                try:
                    resultado = enviar_backup(servico, arquivo)

                    registrar_envio(
                        arquivo.name,
                        resultado["id"]
                    )

                    print(f"Envio registrado: {arquivo.name}")

                except Exception as erro:
                    falha_envio = True
                    print(f"Falha no envio de {arquivo.name}: {erro}")
                    print("O arquivo será mantido para nova tentativa.")



            # Mantém até 7 backups locais já enviados.
            # Backups pendentes não são excluídos.
    limpar_backups_antigos(pasta_backups, manter=7)
    if falha_envio:
        print("ATENÇÃO: houve falhas no envio de backups.")
        raise SystemExit(1)

    print("Processo de backup finalizado com sucesso.")