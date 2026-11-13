"""Recuperação de senha por e-mail.

A funcionária pede um código, que chega no e-mail de recuperação cadastrado
em "Minha conta". O código tem 6 dígitos, vale por 10 minutos e aceita 5
tentativas. Ele fica só na memória do programa: se o sistema for fechado, é
preciso pedir outro.
"""

import secrets
import time

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from . import auth, email_envio

recuperacao_bp = Blueprint("recuperacao", __name__)

VALIDADE_SEGUNDOS = 10 * 60
TENTATIVAS_DO_CODIGO = 5
ESPERA_ENTRE_ENVIOS_SEGUNDOS = 60


def _estado():
    return current_app.extensions.setdefault("recuperacao", {"codigo": None, "expira": 0.0, "tentativas": 0, "ultimo_envio": None})


def _apagar_codigo():
    estado = _estado()
    estado["codigo"], estado["expira"], estado["tentativas"] = None, 0.0, 0


def _codigo_ativo():
    estado = _estado()
    if estado["codigo"] and time.monotonic() < estado["expira"]:
        return True
    _apagar_codigo()
    return False


def _segundos_ate_novo_envio():
    ultimo = _estado()["ultimo_envio"]
    if ultimo is None:
        return 0
    return max(0, int(ultimo + ESPERA_ENTRE_ENVIOS_SEGUNDOS - time.monotonic() + 0.999))


def mascarar_email(email):
    usuario, _, dominio = email.partition("@")
    return f"{usuario[:1]}***@{dominio}"


@recuperacao_bp.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    conta = auth.conta()
    email = conta["email_recuperacao"]
    configurado = email_envio.esta_configurado()
    pode_enviar = bool(email) and configurado
    tela = {"pode_enviar": pode_enviar, "email_cadastrado": bool(email), "email": mascarar_email(email) if email else ""}

    if request.method == "GET":
        return render_template("auth/esqueci_senha.html", **tela, tem_codigo=_codigo_ativo())

    if not pode_enviar:
        return render_template("auth/esqueci_senha.html", **tela, tem_codigo=False), 400
    espera = _segundos_ate_novo_envio()
    if espera:
        return render_template("auth/esqueci_senha.html", **tela, tem_codigo=_codigo_ativo(),
                               erro=f"Aguarde {espera} segundos para pedir outro código."), 429

    codigo = f"{secrets.randbelow(10**6):06d}"
    try:
        email_envio.enviar_codigo(email, codigo, VALIDADE_SEGUNDOS // 60)
    except email_envio.FalhaNoEnvio:
        return render_template("auth/esqueci_senha.html", **tela, tem_codigo=_codigo_ativo(),
                               erro="Não foi possível enviar o e-mail. Confira a internet e tente de novo."), 502

    estado = _estado()
    estado.update(codigo=codigo, expira=time.monotonic() + VALIDADE_SEGUNDOS, tentativas=0, ultimo_envio=time.monotonic())
    flash(f"Enviamos um código para {mascarar_email(email)}. Ele vale por {VALIDADE_SEGUNDOS // 60} minutos.", "success")
    return redirect(url_for("recuperacao.digitar_codigo"))


@recuperacao_bp.route("/esqueci-senha/codigo", methods=["GET", "POST"])
def digitar_codigo():
    if not _codigo_ativo():
        flash("Peça um código novo para redefinir a senha.", "error")
        return redirect(url_for("recuperacao.esqueci_senha"))

    if request.method == "GET":
        return render_template("auth/codigo_senha.html", erros={})

    estado = _estado()
    digitado = "".join(request.form.get("codigo", "").split())
    senha = request.form.get("senha", "")
    confirmacao = request.form.get("confirmacao", "")

    if not secrets.compare_digest(digitado.encode(), estado["codigo"].encode()):
        estado["tentativas"] += 1
        if estado["tentativas"] >= TENTATIVAS_DO_CODIGO:
            _apagar_codigo()
            flash("Muitas tentativas erradas. Peça um código novo.", "error")
            return redirect(url_for("recuperacao.esqueci_senha"))
        restantes = TENTATIVAS_DO_CODIGO - estado["tentativas"]
        return render_template("auth/codigo_senha.html", erros={"codigo": f"Código incorreto. Você ainda tem {restantes} tentativa(s)."}), 400

    conta = auth.conta()
    erro_senha = auth.validar_nova_senha(senha, confirmacao, conta["login"])
    if erro_senha:
        return render_template("auth/codigo_senha.html", erros={"senha": erro_senha}), 400

    auth.redefinir_senha(senha)
    if conta["email_recuperacao"]:
        email_envio.avisar_troca_de_senha(conta["email_recuperacao"])
    auth.zerar_falhas()
    _apagar_codigo()
    flash("Senha alterada. Entre com a nova senha.", "success")
    return redirect(url_for("auth.login"))
