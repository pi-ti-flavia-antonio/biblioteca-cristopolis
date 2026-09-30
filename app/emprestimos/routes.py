import math

from flask import Blueprint, flash, redirect, render_template, request, url_for

from . import repository
from ..livros import repository as livros_repository
from ..usuarios import repository as usuarios_repository

emprestimos_bp = Blueprint("emprestimos", __name__, url_prefix="/emprestimos")


def _formulario(erros=None, selecionado_usuario="", selecionado_livro=""):
    resposta = render_template(
        "emprestimos/formulario.html",
        aba="cadastrar",
        erros=erros or {},
        usuarios=usuarios_repository.opcoes_para_emprestimo(),
        livros=livros_repository.opcoes_para_emprestimo(),
        prazo_dias=repository.PRAZO_PADRAO_DIAS,
        selecionado_usuario=selecionado_usuario,
        selecionado_livro=selecionado_livro,
    )
    return resposta, (400 if erros else 200)


@emprestimos_bp.get("")
def consultar():
    termo = request.args.get("q", "").strip()
    total = repository.contar(termo)
    total_paginas = max(math.ceil(total / repository.POR_PAGINA), 1)
    pagina = min(max(request.args.get("pagina", 1, type=int), 1), total_paginas)

    return render_template(
        "emprestimos/consultar.html",
        aba="consultar",
        termo=termo,
        emprestimos=repository.listar(termo, pagina),
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
        inicio=(pagina - 1) * repository.POR_PAGINA + 1 if total else 0,
        fim=min(pagina * repository.POR_PAGINA, total),
    )


@emprestimos_bp.route("/novo", methods=["GET", "POST"])
def cadastrar():
    if request.method == "GET":
        return _formulario()

    id_usuario = request.form.get("id_usuario", type=int)
    id_livro = request.form.get("id_livro", type=int)

    erros = {}
    if not id_usuario:
        erros["id_usuario"] = "Selecione o usuário."
    if not id_livro:
        erros["id_livro"] = "Selecione o livro."
    if erros:
        return _formulario(erros, str(id_usuario or ""), str(id_livro or ""))

    try:
        _, prevista = repository.criar(id_usuario, id_livro)
    except repository.LivroIndisponivel:
        erros["id_livro"] = "Este livro não tem exemplares disponíveis no momento."
        return _formulario(erros, str(id_usuario), str(id_livro))
    except repository.UsuarioComPendencia:
        erros["id_usuario"] = "Este usuário já está com um livro emprestado e precisa devolvê-lo antes de pegar outro."
        return _formulario(erros, str(id_usuario), str(id_livro))

    flash(f"Empréstimo registrado. Devolução prevista para {prevista.strftime('%d/%m/%Y')}.", "success")
    return redirect(url_for("emprestimos.cadastrar"))
