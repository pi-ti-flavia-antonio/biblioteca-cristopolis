"""Login da funcionária da biblioteca.

O sistema tem uma conta só, guardada na tabela `funcionario`. Ela é criada no
primeiro uso, a senha fica gravada apenas como hash e a sessão expira depois
de um tempo parada.
"""

import time

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .database import get_db
from .usuarios.validacao import erro_de_email

auth_bp = Blueprint("auth", __name__)

SENHA_MINIMA = 8
TENTATIVAS_ANTES_DE_ESPERAR = 5
ESPERA_SEGUNDOS = 60
TAMANHO_MAX_NOME = 100
TAMANHO_MAX_LOGIN = 40

ENDPOINTS_LIVRES = {"static", "auth.login", "auth.primeiro_acesso", "recuperacao.esqueci_senha", "recuperacao.digitar_codigo"}


# Conta


def conta():
    """A conta da funcionária, ou None se ainda não foi criada."""
    return get_db().execute(
        "SELECT id_funcionario, nome, login, senha_hash, email_recuperacao FROM funcionario ORDER BY id_funcionario LIMIT 1"
    ).fetchone()


def validar_nova_senha(senha, confirmacao, login=""):
    if len(senha) < SENHA_MINIMA:
        return f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres."
    if login and senha.casefold() == login.casefold():
        return "A senha não pode ser igual ao nome de usuário."
    if senha != confirmacao:
        return "As duas senhas digitadas são diferentes."
    return None


def validar_nome(nome):
    if not nome:
        return "Informe o nome."
    if len(nome) > TAMANHO_MAX_NOME:
        return f"O nome pode ter no máximo {TAMANHO_MAX_NOME} caracteres."
    return None


def validar_login(login):
    if not login:
        return "Escolha um nome de usuário."
    if len(login) > TAMANHO_MAX_LOGIN or any(c.isspace() for c in login):
        return f"Use até {TAMANHO_MAX_LOGIN} caracteres, sem espaços."
    return None


def alterar_dados(nome, login):
    db = get_db()
    with db:
        db.execute(
            "UPDATE funcionario SET nome = ?, login = ? WHERE id_funcionario = ?",
            (nome, login, conta()["id_funcionario"]),
        )


def alterar_email_de_recuperacao(email):
    db = get_db()
    with db:
        db.execute(
            "UPDATE funcionario SET email_recuperacao = ? WHERE id_funcionario = ?",
            (email or None, conta()["id_funcionario"]),
        )


def criar_conta(nome, login, senha, email=None):
    db = get_db()
    with db:
        cursor = db.execute(
            "INSERT INTO funcionario (nome, cargo, login, senha_hash, email_recuperacao) VALUES (?, 'Bibliotecária', ?, ?, ?)",
            (nome, login, generate_password_hash(senha), email or None),
        )
    return cursor.lastrowid


def redefinir_senha(nova_senha):
    atual = conta()
    db = get_db()
    with db:
        db.execute(
            "UPDATE funcionario SET senha_hash = ? WHERE id_funcionario = ?",
            (generate_password_hash(nova_senha), atual["id_funcionario"]),
        )


# Tentativas erradas


def _controle():
    return current_app.extensions.setdefault("auth", {"falhas": 0, "bloqueado_ate": 0.0})


def _segundos_de_espera():
    return max(0, int(_controle()["bloqueado_ate"] - time.monotonic() + 0.999))


def _registrar_falha():
    controle = _controle()
    controle["falhas"] += 1
    if controle["falhas"] >= TENTATIVAS_ANTES_DE_ESPERAR:
        controle["falhas"] = 0
        controle["bloqueado_ate"] = time.monotonic() + ESPERA_SEGUNDOS


def zerar_falhas():
    controle = _controle()
    controle["falhas"] = 0
    controle["bloqueado_ate"] = 0.0


# Proteção das páginas


def _destino_seguro(destino):
    return destino if destino and destino.startswith("/") and not destino.startswith("//") and "\\" not in destino else ""


def _quer_json():
    return request.path.endswith("/sugestoes") or request.accept_mimetypes.best == "application/json"


def exigir_login():
    if request.endpoint in ENDPOINTS_LIVRES:
        return None

    funcionaria = conta()
    if funcionaria is None:
        return redirect(url_for("auth.primeiro_acesso"))

    if session.get("id_funcionario") != funcionaria["id_funcionario"]:
        if _quer_json():
            return jsonify(erro="É preciso entrar no sistema."), 401
        if request.method == "GET":
            return redirect(url_for("auth.login", proximo=request.full_path.rstrip("?")))
        flash("Sua sessão expirou. Entre de novo para continuar.", "error")
        return redirect(url_for("auth.login"))

    g.funcionaria = funcionaria
    return None


def _entrar(id_funcionario):
    session.clear()
    session["id_funcionario"] = id_funcionario
    session.permanent = True


# Telas


def _tela_login(erro="", status=200, login="", proximo=""):
    return render_template("auth/login.html", erro=erro, login=login, proximo=proximo), status


@auth_bp.route("/entrar", methods=["GET", "POST"])
def login():
    if conta() is None:
        return redirect(url_for("auth.primeiro_acesso"))
    proximo = _destino_seguro(request.values.get("proximo", ""))

    if request.method == "GET":
        if session.get("id_funcionario") == conta()["id_funcionario"]:
            return redirect(proximo or url_for("main.index"))
        return _tela_login(proximo=proximo)

    espera = _segundos_de_espera()
    if espera:
        return _tela_login(f"Muitas tentativas erradas. Aguarde {espera} segundos para tentar de novo.", 429, proximo=proximo)

    login_digitado = request.form.get("login", "").strip()
    senha = request.form.get("senha", "")
    funcionaria = conta()
    # A senha é conferida mesmo quando o usuário está errado, para o tempo de resposta não revelar qual dos dois falhou.
    senha_certa = check_password_hash(funcionaria["senha_hash"], senha)
    if senha_certa and login_digitado.casefold() == funcionaria["login"].casefold():
        zerar_falhas()
        _entrar(funcionaria["id_funcionario"])
        return redirect(proximo or url_for("main.index"))

    _registrar_falha()
    return _tela_login("Usuário ou senha incorretos.", 401, login=login_digitado, proximo=proximo)


@auth_bp.route("/primeiro-acesso", methods=["GET", "POST"])
def primeiro_acesso():
    if conta() is not None:
        return redirect(url_for("auth.login"))

    valores = {"nome": "", "login": "", "email": ""}
    erros = {}
    if request.method == "POST":
        valores = {
            "nome": request.form.get("nome", "").strip(),
            "login": request.form.get("login", "").strip(),
            "email": request.form.get("email", "").strip(),
        }
        senha = request.form.get("senha", "")
        confirmacao = request.form.get("confirmacao", "")

        for campo, validar in (("nome", validar_nome), ("login", validar_login)):
            erro = validar(valores[campo])
            if erro:
                erros[campo] = erro
        erro_senha = validar_nova_senha(senha, confirmacao, valores["login"])
        if erro_senha:
            erros["senha"] = erro_senha
        if valores["email"]:
            erro = erro_de_email(valores["email"])
            if erro:
                erros["email"] = erro

        if not erros:
            id_funcionario = criar_conta(valores["nome"], valores["login"], senha, valores["email"])
            _entrar(id_funcionario)
            flash("Conta criada. Você já está dentro do sistema.", "success")
            return redirect(url_for("main.index"))

    return render_template("auth/primeiro_acesso.html", valores=valores, erros=erros), (400 if erros else 200)


@auth_bp.post("/sair")
def sair():
    session.clear()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for("auth.login"))


def _tela_conta(erros_dados=None, erros_senha=None, valores=None, erros_email=None, email=None):
    erros_dados, erros_senha, erros_email = erros_dados or {}, erros_senha or {}, erros_email or {}
    valores = valores or {"nome": g.funcionaria["nome"], "login": g.funcionaria["login"]}
    if email is None:
        email = g.funcionaria["email_recuperacao"] or ""
    status = 400 if (erros_dados or erros_senha or erros_email) else 200
    return render_template(
        "auth/conta.html", erros_dados=erros_dados, erros_senha=erros_senha, erros_email=erros_email, valores=valores, email=email
    ), status


@auth_bp.get("/conta")
def minha_conta():
    return _tela_conta()


@auth_bp.post("/conta/dados")
def alterar_dados_da_conta():
    valores = {"nome": request.form.get("nome", "").strip(), "login": request.form.get("login", "").strip()}
    erros = {}
    for campo, validar in (("nome", validar_nome), ("login", validar_login)):
        erro = validar(valores[campo])
        if erro:
            erros[campo] = erro
    if not check_password_hash(g.funcionaria["senha_hash"], request.form.get("senha_atual", "")):
        erros["senha_atual"] = "A senha atual está incorreta."

    if erros:
        return _tela_conta(erros_dados=erros, valores=valores)

    alterar_dados(valores["nome"], valores["login"])
    flash("Dados da conta atualizados.", "success")
    return redirect(url_for("auth.minha_conta"))


@auth_bp.post("/conta/email")
def alterar_email_da_conta():
    email = request.form.get("email", "").strip()
    erros = {}
    if email:
        erro = erro_de_email(email)
        if erro:
            erros["email"] = erro
    if not check_password_hash(g.funcionaria["senha_hash"], request.form.get("senha_atual", "")):
        erros["senha_atual"] = "A senha atual está incorreta."

    if erros:
        return _tela_conta(erros_email=erros, email=email)

    alterar_email_de_recuperacao(email)
    flash("E-mail de recuperação salvo." if email else "E-mail de recuperação removido.", "success")
    return redirect(url_for("auth.minha_conta"))


@auth_bp.route("/conta/senha", methods=["GET", "POST"])
def trocar_senha():
    if request.method == "GET":
        return redirect(url_for("auth.minha_conta"))

    erros = {}
    atual = request.form.get("senha_atual", "")
    nova = request.form.get("senha", "")
    confirmacao = request.form.get("confirmacao", "")

    if not check_password_hash(g.funcionaria["senha_hash"], atual):
        erros["senha_atual"] = "A senha atual está incorreta."
    erro_nova = validar_nova_senha(nova, confirmacao, g.funcionaria["login"])
    if erro_nova:
        erros["senha"] = erro_nova
    elif nova == atual:
        erros["senha"] = "A nova senha precisa ser diferente da atual."

    if erros:
        return _tela_conta(erros_senha=erros)

    redefinir_senha(nova)
    flash("Senha alterada.", "success")
    return redirect(url_for("auth.minha_conta"))


def init_app(app):
    from .recuperacao import recuperacao_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(recuperacao_bp)
    app.before_request(exigir_login)
    app.context_processor(lambda: {"funcionaria": g.get("funcionaria")})
