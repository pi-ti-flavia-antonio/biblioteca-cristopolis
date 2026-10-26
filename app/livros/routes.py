import math

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from . import isbn_lookup, repository, validacao
from ..texto import limpar_isbn

livros_bp = Blueprint("livros", __name__, url_prefix="/livros")


def _exemplares(quantidade):
    return f"{quantidade} exemplar emprestado" if quantidade == 1 else f"{quantidade} exemplares emprestados"


def _checar_regras_do_banco(dados, erros, livro_atual=None):
    """Regras que dependem do que já está gravado."""
    if dados["isbn"]:
        existente = repository.buscar_por_isbn(dados["isbn"])
        mesmo_livro = livro_atual is not None and existente and existente["id_livro"] == livro_atual["id_livro"]
        if existente and not mesmo_livro:
            erros["isbn"] = (
                f"Já existe um livro com este ISBN: {existente['titulo']}. "
                "Para registrar mais exemplares, aumente a quantidade dele."
            )

    if livro_atual is not None and dados["quantidade"] is not None:
        emprestados = livro_atual["emprestimos_ativos"]
        if dados["quantidade"] < emprestados:
            erros["quantidade"] = (
                f"Há {_exemplares(emprestados)} no momento, "
                f"então a quantidade não pode ser menor que {emprestados}."
            )


def _formulario(valores, erros, aba=None, livro_id=None, voltar=""):
    resposta = render_template(
        "livros/formulario.html",
        aba=aba,
        livro_id=livro_id,
        valores=valores,
        erros=erros,
        categorias=repository.nomes_categorias(),
        voltar=voltar,
    )
    return resposta, (400 if erros else 200)


def _buscar_dados_do_isbn(valores):
    """Tenta preencher título/autor/ano a partir do ISBN digitado.

    Retorna os valores (atualizados ou não) e uma mensagem para o usuário.
    """
    isbn = limpar_isbn(valores["isbn"])
    if not isbn:
        return valores, "Informe um ISBN para buscar.", "error"

    encontrado = isbn_lookup.buscar_por_isbn(isbn)
    if encontrado is None:
        return valores, (
            "Não foi possível encontrar dados para esse ISBN agora (sem internet ou livro não "
            "encontrado na base consultada). Preencha os campos manualmente."
        ), "error"

    novos_valores = {**valores, "isbn": isbn}
    if encontrado["titulo"]:
        novos_valores["titulo"] = encontrado["titulo"]
    if encontrado["autor"]:
        novos_valores["autor"] = encontrado["autor"]
    if encontrado["ano_publicacao"]:
        novos_valores["ano_publicacao"] = str(encontrado["ano_publicacao"])
    return novos_valores, "Dados encontrados. Confira as informações e clique em Salvar.", "success"


def _obter_ou_404(id_livro):
    livro = repository.obter(id_livro)
    if livro is None:
        abort(404)
    return livro


@livros_bp.get("")
def consultar():
    termo = request.args.get("q", "").strip()
    total = repository.contar(termo)
    total_paginas = max(math.ceil(total / repository.POR_PAGINA), 1)
    pagina = min(max(request.args.get("pagina", 1, type=int), 1), total_paginas)

    return render_template(
        "livros/consultar.html",
        aba="consultar",
        termo=termo,
        livros=repository.listar(termo, pagina),
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
        inicio=(pagina - 1) * repository.POR_PAGINA + 1 if total else 0,
        fim=min(pagina * repository.POR_PAGINA, total),
    )


@livros_bp.get("/sugestoes")
def sugestoes():
    termo = request.args.get("q", "").strip()
    return jsonify(itens=[
        {
            "id": livro["id_livro"],
            "titulo": livro["titulo"],
            "subtitulo": livro["autor"],
            "disponiveis": livro["quantidade_disponivel"],
        }
        for livro in repository.sugerir(termo, somente_esgotados=request.args.get("esgotados") == "1")
    ])


@livros_bp.route("/novo", methods=["GET", "POST"])
def cadastrar():
    if request.method == "GET":
        voltar = request.args.get("voltar", "")
        return _formulario(validacao.valores_iniciais(), {}, aba="cadastrar", voltar=voltar)

    voltar = request.form.get("voltar", "")
    valores = validacao.valores_do_formulario(request.form)

    if request.form.get("acao") == "buscar_isbn":
        valores, mensagem, categoria = _buscar_dados_do_isbn(valores)
        flash(mensagem, categoria)
        return _formulario(valores, {}, aba="cadastrar", voltar=voltar)

    dados, erros = validacao.validar_livro(valores)
    _checar_regras_do_banco(dados, erros)
    if erros:
        return _formulario(valores, erros, aba="cadastrar", voltar=voltar)

    id_livro = repository.criar(dados)
    flash(f"Livro cadastrado: {dados['titulo']}.", "success")

    if voltar == "emprestimo":
        return redirect(url_for("emprestimos.cadastrar", id_livro=id_livro))
    return redirect(url_for("livros.cadastrar"))


@livros_bp.route("/<int:id_livro>/editar", methods=["GET", "POST"])
def editar(id_livro):
    livro = _obter_ou_404(id_livro)
    if request.method == "GET":
        return _formulario(validacao.valores_do_livro(livro), {}, livro_id=id_livro)

    valores = validacao.valores_do_formulario(request.form)

    if request.form.get("acao") == "buscar_isbn":
        valores, mensagem, categoria = _buscar_dados_do_isbn(valores)
        flash(mensagem, categoria)
        return _formulario(valores, {}, livro_id=id_livro)

    dados, erros = validacao.validar_livro(valores)
    _checar_regras_do_banco(dados, erros, livro_atual=livro)
    if erros:
        return _formulario(valores, erros, livro_id=id_livro)

    repository.atualizar(id_livro, dados)
    flash(f"Livro atualizado: {dados['titulo']}.", "success")
    return redirect(url_for("livros.consultar"))


@livros_bp.route("/<int:id_livro>/excluir", methods=["GET", "POST"])
def excluir(id_livro):
    livro = _obter_ou_404(id_livro)
    if request.method == "GET":
        return render_template(
            "livros/excluir.html",
            livro=livro,
            total_emprestimos=repository.contar_emprestimos(id_livro),
            total_reservas=repository.contar_reservas(id_livro),
        )

    try:
        repository.excluir(id_livro)
    except repository.LivroComEmprestimos:
        flash("Este livro tem empréstimos ou reservas registrados e não pode ser excluído.", "error")
    else:
        flash(f"Livro excluído: {livro['titulo']}.", "success")
    return redirect(url_for("livros.consultar"))
