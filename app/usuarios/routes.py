import math

from flask import Blueprint, Response, abort, flash, jsonify, redirect, render_template, request, url_for

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
            if existente["ativo"]:
                erros["cpf"] = "Já existe um usuário cadastrado com este CPF."
            else:
                erros["cpf"] = "Este CPF pertence a um usuário inativo."
            return existente
    if dados["numero_carteirinha"]:
        existente = repository.buscar_por_carteirinha(dados["numero_carteirinha"])
        mesmo_usuario = (
            usuario_atual is not None
            and existente
            and existente["id_usuario"] == usuario_atual["id_usuario"]
        )
        if existente and not mesmo_usuario:
            erros["numero_carteirinha"] = (
                f"Este número de carteirinha já é de {existente['nome']}."
                if existente["ativo"]
                else f"Este número de carteirinha é de um usuário inativo ({existente['nome']})."
            )
    return None


def _foto_enviada():
    """Valida a foto do formulário. Devolve (tipo, bytes) e preenche o erro, se houver."""
    return validacao.validar_foto(request.files.get("foto"))


def _formulario(valores, erros, aba=None, usuario_id=None, voltar="", cpf_inativo=None, tem_foto=False):
    resposta = render_template(
        "usuarios/formulario.html",
        aba=aba,
        usuario_id=usuario_id,
        valores=valores,
        erros=erros,
        tipos_usuario=validacao.TIPOS_USUARIO,
        voltar=voltar,
        cpf_inativo=cpf_inativo,
        tem_foto=tem_foto,
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
    incluir_inativos = request.args.get("inativos") == "1"
    # Se a busca só acha cadastros inativos, mostra eles em vez de uma lista vazia.
    so_inativos = bool(termo) and not incluir_inativos and repository.contar(termo) == 0 and repository.contar(termo, True) > 0
    incluir_inativos = incluir_inativos or so_inativos
    total = repository.contar(termo, incluir_inativos)
    total_paginas = max(math.ceil(total / repository.POR_PAGINA), 1)
    pagina = min(max(request.args.get("pagina", 1, type=int), 1), total_paginas)

    return render_template(
        "usuarios/consultar.html",
        aba="consultar",
        termo=termo,
        usuarios=repository.listar(termo, pagina, incluir_inativos),
        incluir_inativos=incluir_inativos,
        so_inativos=so_inativos,
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
            "subtitulo": " · ".join(filter(None, [
                f"Carteirinha {usuario['numero_carteirinha']}" if usuario["numero_carteirinha"] else "",
                f"CPF {mascarar_cpf(usuario['cpf'])}" if usuario["cpf"] else "",
                "" if usuario["ativo"] else "Inativo",
            ])),
        }
        for usuario in repository.sugerir(termo, incluir_inativos=request.args.get("inativos") == "1")
    ])


@usuarios_bp.route("/novo", methods=["GET", "POST"])
def cadastrar():
    if request.method == "GET":
        voltar = request.args.get("voltar", "")
        return _formulario(validacao.valores_iniciais(), {}, aba="cadastrar", voltar=voltar)

    voltar = request.form.get("voltar", "")
    valores = validacao.valores_do_formulario(request.form)
    dados, erros = validacao.validar_usuario(valores)
    existente = _checar_regras_do_banco(dados, erros)
    tipo_foto, foto, erro_foto = _foto_enviada()
    if erro_foto:
        erros["foto"] = erro_foto
    elif erros and foto:
        erros["foto"] = "Escolha a foto de novo: ela não foi guardada porque o formulário tinha erros."
    if erros:
        cpf_inativo = existente if existente is not None and not existente["ativo"] else None
        return _formulario(valores, erros, aba="cadastrar", voltar=voltar, cpf_inativo=cpf_inativo)

    if valores["carteirinha_modo"] == "automatico":
        dados["numero_carteirinha"] = repository.proximo_numero_carteirinha()
    id_usuario = repository.criar(dados)
    if foto:
        repository.salvar_foto(id_usuario, tipo_foto, foto)
    flash(
        f"Usuário cadastrado: {dados['nome']}. Número da carteirinha: {dados['numero_carteirinha']}."
        if dados["numero_carteirinha"] else f"Usuário cadastrado: {dados['nome']}.",
        "success",
    )

    if voltar == "emprestimo":
        return redirect(url_for("emprestimos.cadastrar", id_usuario=id_usuario))
    return redirect(url_for("usuarios.cadastrar"))


@usuarios_bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
def editar(usuario_id):
    usuario = _obter_ou_404(usuario_id)
    if request.method == "GET":
        return _formulario(validacao.valores_do_usuario(usuario), {}, usuario_id=usuario_id, tem_foto=usuario["tem_foto"])

    valores = validacao.valores_do_formulario(request.form)
    dados, erros = validacao.validar_usuario(valores, numero_atual=usuario["numero_carteirinha"], edicao=True)
    _checar_regras_do_banco(dados, erros, usuario_atual=usuario)
    tipo_foto, foto, erro_foto = _foto_enviada()
    if erro_foto:
        erros["foto"] = erro_foto
    elif erros and foto:
        erros["foto"] = "Escolha a foto de novo: ela não foi guardada porque o formulário tinha erros."
    if erros:
        return _formulario(valores, erros, usuario_id=usuario_id, tem_foto=usuario["tem_foto"])

    repository.atualizar(usuario_id, dados)
    if foto:
        repository.salvar_foto(usuario_id, tipo_foto, foto)
    elif request.form.get("remover_foto") == "1":
        repository.remover_foto(usuario_id)
    flash(f"Usuário atualizado: {dados['nome']}.", "success")
    return redirect(url_for("usuarios.consultar"))


@usuarios_bp.get("/<int:usuario_id>")
def ver(usuario_id):
    return render_template("usuarios/ver.html", usuario=_obter_ou_404(usuario_id))


@usuarios_bp.get("/<int:usuario_id>/foto")
def foto(usuario_id):
    registro = repository.obter_foto(usuario_id)
    if registro is None:
        abort(404)
    resposta = Response(registro["dados"], mimetype=registro["tipo_conteudo"])
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["Cache-Control"] = "private, no-cache"
    return resposta


@usuarios_bp.route("/<int:usuario_id>/excluir", methods=["GET", "POST"])
def excluir(usuario_id):
    usuario = _obter_ou_404(usuario_id)
    if request.method == "GET":
        return render_template(
            "usuarios/excluir.html",
            usuario=usuario,
            situacao=repository.situacao_para_remover(usuario_id),
            emprestimos_ativos=repository.contar_pendencias(usuario_id),
        )

    try:
        repository.excluir(usuario_id)
    except repository.UsuarioComPendencia:
        flash("Este usuário está com livro emprestado ou reserva ativa e não pode ser excluído.", "error")
    except repository.UsuarioComHistorico:
        flash("Este usuário tem histórico de empréstimos ou reservas e não pode ser excluído. Use Inativar.", "error")
    else:
        flash(f"Usuário excluído: {usuario['nome']}.", "success")
    return redirect(url_for("usuarios.consultar"))


@usuarios_bp.post("/<int:usuario_id>/inativar")
def inativar(usuario_id):
    usuario = _obter_ou_404(usuario_id)
    try:
        repository.inativar(usuario_id)
    except repository.UsuarioComPendencia:
        flash("Este usuário está com livro emprestado ou reserva ativa e não pode ser inativado.", "error")
    else:
        flash(f"Usuário inativado: {usuario['nome']}. Ele não aparece mais nas buscas de empréstimo e reserva.", "success")
    return redirect(url_for("usuarios.consultar"))


@usuarios_bp.post("/<int:usuario_id>/reativar")
def reativar(usuario_id):
    usuario = _obter_ou_404(usuario_id)
    repository.reativar(usuario_id)
    flash(f"Usuário reativado: {usuario['nome']}. Confira se os dados abaixo continuam certos.", "success")
    return redirect(url_for("usuarios.editar", usuario_id=usuario_id))
