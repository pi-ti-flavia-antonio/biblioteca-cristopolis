import math

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..emprestimos import repository as emprestimos

devolucoes_bp = Blueprint("devolucoes", __name__, url_prefix="/devolucoes")


@devolucoes_bp.get("")
def consultar():
    termo = request.args.get("q", "").strip()
    total = emprestimos.contar_ativos_busca(termo)
    total_paginas = max(math.ceil(total / emprestimos.POR_PAGINA), 1)
    pagina = min(max(request.args.get("pagina", 1, type=int), 1), total_paginas)

    return render_template(
        "devolucoes/consultar.html",
        termo=termo,
        emprestimos=emprestimos.listar_ativos(termo, pagina),
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
        inicio=(pagina - 1) * emprestimos.POR_PAGINA + 1 if total else 0,
        fim=min(pagina * emprestimos.POR_PAGINA, total),
    )


@devolucoes_bp.post("/<int:id_emprestimo>/registrar")
def registrar(id_emprestimo):
    try:
        resultado = emprestimos.registrar_devolucao(id_emprestimo)
    except emprestimos.EmprestimoInvalido:
        abort(404)

    if resultado["dias_atraso"] > 0:
        dias = resultado["dias_atraso"]
        mensagem = (
            f"Devolução registrada: {resultado['livro_titulo']} ({resultado['usuario_nome']}). "
            f"Devolvido com {dias} {'dia' if dias == 1 else 'dias'} de atraso."
        )
    else:
        mensagem = f"Devolução registrada: {resultado['livro_titulo']} ({resultado['usuario_nome']}). Devolvido no prazo."

    flash(mensagem, "success")
    return redirect(url_for("devolucoes.consultar"))
