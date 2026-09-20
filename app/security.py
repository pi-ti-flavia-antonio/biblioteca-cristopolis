import hmac
import secrets

from flask import abort, request, session

METODOS_COM_ESCRITA = {"POST", "PUT", "PATCH", "DELETE"}


def gerar_token_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def _validar_csrf():
    if request.method not in METODOS_COM_ESCRITA:
        return
    esperado = session.get("csrf_token", "")
    enviado = request.form.get("csrf_token", "")
    if not esperado or not hmac.compare_digest(enviado, esperado):
        abort(400)


def init_app(app):
    app.before_request(_validar_csrf)
    app.jinja_env.globals["csrf_token"] = gerar_token_csrf
