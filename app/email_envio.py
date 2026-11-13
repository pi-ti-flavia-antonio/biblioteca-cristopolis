"""Envio do código de recuperação de senha e do aviso de troca de senha pelo Gmail.

O Gmail e a senha de aplicativo ficam em `email.json`, na pasta de dados do
sistema (fora do Git). A senha fica criptografada com a mesma chave do backup,
quando essa chave existe. O arquivo é criado por `configurar_email.py`.
"""

import json
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

SERVIDOR = "smtp.gmail.com"
PORTA = 465
ESPERA_MAXIMA_SEGUNDOS = 15


class EmailNaoConfigurado(Exception):
    pass


class FalhaNoEnvio(Exception):
    pass


def _chave():
    """O Fernet da chave do backup, ou None se a chave não existir neste computador."""
    try:
        return Fernet(current_app.config["ARQUIVO_CHAVE"].read_bytes())
    except (OSError, ValueError, KeyError):
        return None


def salvar_configuracao(remetente, senha):
    """Grava o Gmail e a senha de aplicativo. Devolve True se a senha foi criptografada."""
    senha = senha.replace(" ", "")
    fernet = _chave()
    dados = {"remetente": remetente}
    if fernet:
        dados["senha_app_criptografada"] = fernet.encrypt(senha.encode()).decode()
    else:
        dados["senha_app"] = senha
    current_app.config["ARQUIVO_EMAIL"].write_text(json.dumps(dados), encoding="utf-8")
    return fernet is not None


def ler_configuracao():
    """Devolve (remetente, senha) ou levanta EmailNaoConfigurado."""
    try:
        dados = json.loads(current_app.config["ARQUIVO_EMAIL"].read_text(encoding="utf-8"))
        remetente = dados["remetente"]
        if dados.get("senha_app_criptografada"):
            fernet = _chave()
            if fernet is None:
                raise EmailNaoConfigurado()
            senha = fernet.decrypt(dados["senha_app_criptografada"].encode()).decode()
        else:
            senha = dados["senha_app"]
    except (OSError, ValueError, KeyError, TypeError, InvalidToken):
        raise EmailNaoConfigurado()
    if not remetente or not senha:
        raise EmailNaoConfigurado()
    return remetente, senha


def esta_configurado():
    try:
        ler_configuracao()
    except EmailNaoConfigurado:
        return False
    return True


def enviar(destino, assunto, texto):
    remetente, senha = ler_configuracao()
    mensagem = EmailMessage()
    mensagem["From"] = f"Biblioteca de Cristópolis <{remetente}>"
    mensagem["To"] = destino
    mensagem["Subject"] = assunto
    mensagem.set_content(texto)
    try:
        with smtplib.SMTP_SSL(SERVIDOR, PORTA, timeout=ESPERA_MAXIMA_SEGUNDOS, context=ssl.create_default_context()) as servidor:
            servidor.login(remetente, senha.replace(" ", ""))
            servidor.send_message(mensagem)
    except (OSError, smtplib.SMTPException) as erro:
        raise FalhaNoEnvio() from erro


def enviar_codigo(destino, codigo, validade_minutos):
    enviar(
        destino,
        "Código para redefinir a senha da biblioteca",
        f"Seu código para redefinir a senha do sistema da Biblioteca de Cristópolis é {codigo}.\n\n"
        f"Ele vale por {validade_minutos} minutos. Se você não pediu a troca de senha, ignore este e-mail.\n",
    )


def avisar_troca_de_senha(destino):
    """Avisa por e-mail que a senha foi trocada. Se o envio não for possível, segue sem avisar."""
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    try:
        enviar(
            destino,
            "A senha do sistema da biblioteca foi trocada",
            f"A senha do sistema da Biblioteca de Cristópolis foi trocada em {agora}.\n\n"
            "Se foi você, não precisa fazer nada. Se não foi, avise quem cuida do sistema.\n",
        )
    except (EmailNaoConfigurado, FalhaNoEnvio):
        return False
    return True
