"""Envio do código de recuperação de senha pelo Gmail.

O Gmail e a senha de aplicativo ficam em `email.json`, na pasta de dados do
sistema (fora do Git). O arquivo é criado por `configurar_email.py`.
"""

import json
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app

SERVIDOR = "smtp.gmail.com"
PORTA = 465
ESPERA_MAXIMA_SEGUNDOS = 15


class EmailNaoConfigurado(Exception):
    pass


class FalhaNoEnvio(Exception):
    pass


def ler_configuracao():
    """Devolve (remetente, senha) ou levanta EmailNaoConfigurado."""
    try:
        dados = json.loads(current_app.config["ARQUIVO_EMAIL"].read_text(encoding="utf-8"))
        remetente, senha = dados["remetente"], dados["senha_app"]
    except (OSError, ValueError, KeyError, TypeError):
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
