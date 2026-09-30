import math

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from . import repository, reservas_repository
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
        id_livro = request.args.get("id_livro", "")
        return _formulario(selecionado_livro=id_livro)

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


def _livros_esgotados():
    return [l for l in livros_repository.opcoes_para_emprestimo() if l["quantidade_disponivel"] <= 0]


def _reservas(erros=None, selecionado_usuario="", selecionado_livro=""):
    resposta = render_template(
        "emprestimos/reservas.html",
        aba="reservas",
        erros=erros or {},
        usuarios=usuarios_repository.opcoes_para_emprestimo(),
        livros=_livros_esgotados(),
        reservas=reservas_repository.listar_ativas(),
        total=reservas_repository.contar_ativas(),
        selecionado_usuario=selecionado_usuario,
        selecionado_livro=selecionado_livro,
    )
    return resposta, (400 if erros else 200)


@emprestimos_bp.route("/reservas", methods=["GET", "POST"])
def reservas():
    if request.method == "GET":
        return _reservas()

    id_usuario = request.form.get("id_usuario", type=int)
    id_livro = request.form.get("id_livro", type=int)

    erros = {}
    if not id_usuario:
        erros["id_usuario"] = "Selecione o usuário."
    if not id_livro:
        erros["id_livro"] = "Selecione o livro."
    if erros:
        return _reservas(erros, str(id_usuario or ""), str(id_livro or ""))

    try:
        reservas_repository.criar(id_usuario, id_livro)
    except reservas_repository.LivroComExemplarDisponivel:
        erros["id_livro"] = "Este livro já tem exemplar disponível. Registre um empréstimo em vez de uma reserva."
        return _reservas(erros, str(id_usuario), str(id_livro))
    except reservas_repository.ReservaDuplicada:
        erros["id_usuario"] = "Este usuário já tem uma reserva ativa para este livro."
        return _reservas(erros, str(id_usuario), str(id_livro))

    flash("Reserva registrada.", "success")
    return redirect(url_for("emprestimos.reservas"))


@emprestimos_bp.post("/reservas/<int:id_reserva>/cancelar")
def reservas_cancelar(id_reserva):
    try:
        reservas_repository.cancelar(id_reserva)
    except reservas_repository.ReservaInvalida:
        abort(404)

    flash("Reserva cancelada.", "success")
    return redirect(url_for("emprestimos.reservas"))


@emprestimos_bp.post("/reservas/<int:id_reserva>/retirar")
def reservas_retirar(id_reserva):
    try:
        prevista = reservas_repository.retirar(id_reserva)
    except reservas_repository.ReservaInvalida:
        abort(404)
    except repository.LivroIndisponivel:
        flash("Este livro não tem exemplar disponível agora.", "error")
        return redirect(url_for("emprestimos.reservas"))
    except repository.UsuarioComPendencia:
        flash("Este usuário já está com um livro emprestado e precisa devolvê-lo antes de pegar outro.", "error")
        return redirect(url_for("emprestimos.reservas"))

    flash(f"Empréstimo registrado a partir da reserva. Devolução prevista para {prevista.strftime('%d/%m/%Y')}.", "success")
    return redirect(url_for("emprestimos.reservas"))
