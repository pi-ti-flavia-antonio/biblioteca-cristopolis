import math

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from . import repository, validacao
from ..texto import mascarar_cpf

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


def _checar_regras_do_banco(dados, erros, usuario_atual=None):
    """Regras que dependem do que já está gravado."""
    if dados["cpf"]:
        existente = repository.buscar_por_cpf(dados["cpf"])
        mesmo_usuario = (
            usuario_atual is not None
            and existente
            and existente["id_usuario"] == usuario_atual["id_usuario"]
        )
        if existente and not mesmo_usuario:
            erros["cpf"] = "Já existe um usuário cadastrado com este CPF."


def _formulario(valores, erros, aba=None, usuario_id=None, voltar=""):
    resposta = render_template(
        "usuarios/formulario.html",
        aba=aba,
        usuario_id=usuario_id,
        valores=valores,
        erros=erros,
        tipos_usuario=validacao.TIPOS_USUARIO,
        voltar=voltar,
    )
    return resposta, (400 if erros else 200)


def _obter_ou_404(id_usuario):
    usuario = repository.obter(id_usuario)
    if usuario is None:
        abort(404)
    return usuario


@usuarios_bp.get("")
def consultar():
    termo = request.args.get("q", "").strip()
    total = repository.contar(termo)
    total_paginas = max(math.ceil(total / repository.POR_PAGINA), 1)
    pagina = min(max(request.args.get("pagina", 1, type=int), 1), total_paginas)

    return render_template(
        "usuarios/consultar.html",
        aba="consultar",
        termo=termo,
        usuarios=repository.listar(termo, pagina),
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
        inicio=(pagina - 1) * repository.POR_PAGINA + 1 if total else 0,
        fim=min(pagina * repository.POR_PAGINA, total),
    )


@usuarios_bp.get("/sugestoes")
def sugestoes():
    termo = request.args.get("q", "").strip()
    return jsonify(itens=[
        {
            "id": usuario["id_usuario"],
            "titulo": usuario["nome"],
            "subtitulo": f"CPF {mascarar_cpf(usuario['cpf'])}" if usuario["cpf"] else "",
        }
        for usuario in repository.sugerir(termo)
    ])


@usuarios_bp.route("/novo", methods=["GET", "POST"])
def cadastrar():
    if request.method == "GET":
        voltar = request.args.get("voltar", "")
        return _formulario(validacao.valores_iniciais(), {}, aba="cadastrar", voltar=voltar)

    voltar = request.form.get("voltar", "")
    valores = validacao.valores_do_formulario(request.form)
    dados, erros = validacao.validar_usuario(valores)
    _checar_regras_do_banco(dados, erros)
    if erros:
        return _formulario(valores, erros, aba="cadastrar", voltar=voltar)

    id_usuario = repository.criar(dados)
    flash(f"Usuário cadastrado: {dados['nome']}.", "success")

    if voltar == "emprestimo":
        return redirect(url_for("emprestimos.cadastrar", id_usuario=id_usuario))
    return redirect(url_for("usuarios.cadastrar"))


@usuarios_bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
def editar(usuario_id):
    usuario = _obter_ou_404(usuario_id)
    if request.method == "GET":
        return _formulario(validacao.valores_do_usuario(usuario), {}, usuario_id=usuario_id)

    valores = validacao.valores_do_formulario(request.form)
    dados, erros = validacao.validar_usuario(valores)
    _checar_regras_do_banco(dados, erros, usuario_atual=usuario)
    if erros:
        return _formulario(valores, erros, usuario_id=usuario_id)

    repository.atualizar(usuario_id, dados)
    flash(f"Usuário atualizado: {dados['nome']}.", "success")
    return redirect(url_for("usuarios.consultar"))


@usuarios_bp.route("/<int:usuario_id>/excluir", methods=["GET", "POST"])
def excluir(usuario_id):
    usuario = _obter_ou_404(usuario_id)
    if request.method == "GET":
        return render_template(
            "usuarios/excluir.html",
            usuario=usuario,
            total_emprestimos=repository.contar_emprestimos(usuario_id),
        )

    try:
        repository.excluir(usuario_id)
    except repository.UsuarioComEmprestimos:
        flash("Este usuário tem empréstimos registrados e não pode ser excluído.", "error")
    else:
        flash(f"Usuário excluído: {usuario['nome']}.", "success")
    return redirect(url_for("usuarios.consultar"))
