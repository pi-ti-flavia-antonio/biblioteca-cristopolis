import math
from datetime import date, timedelta

from flask import Blueprint, render_template, request

from ..emprestimos import repository as emprestimos_repo

relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")

LIMITE_DIAS_PERIODO = 366


def _periodo_padrao():
    hoje = date.today()
    return hoje - timedelta(days=29), hoje


def _validar_periodo(inicio_str, fim_str):
    erros = {}
    padrao_inicio, padrao_fim = _periodo_padrao()

    data_fim = padrao_fim
    if fim_str:
        try:
            data_fim = date.fromisoformat(fim_str)
        except ValueError:
            erros["data_fim"] = "Informe uma data final válida."

    data_inicio = padrao_inicio
    if inicio_str:
        try:
            data_inicio = date.fromisoformat(inicio_str)
        except ValueError:
            erros["data_inicio"] = "Informe uma data inicial válida."

    if not erros:
        if data_inicio > data_fim:
            erros["data_inicio"] = "A data inicial não pode ser depois da data final."
        elif (data_fim - data_inicio).days > LIMITE_DIAS_PERIODO:
            erros["data_inicio"] = "O período não pode ser maior que 1 ano."

    return data_inicio, data_fim, erros


def _com_dias_atraso(linha):
    prevista = date.fromisoformat(linha["data_devolucao_prevista"])
    return {**dict(linha), "dias_atraso": (date.today() - prevista).days}


@relatorios_bp.get("")
def periodo():
    data_inicio, data_fim, erros = _validar_periodo(
        request.args.get("inicio", ""), request.args.get("fim", "")
    )

    total = 0 if erros else emprestimos_repo.contar_por_periodo(data_inicio, data_fim)
    total_paginas = max(math.ceil(total / emprestimos_repo.POR_PAGINA), 1)
    pagina = min(max(request.args.get("pagina", 1, type=int), 1), total_paginas)
    lista = [] if erros else emprestimos_repo.listar_por_periodo(data_inicio, data_fim, pagina)

    return render_template(
        "relatorios/periodo.html",
        aba="periodo",
        data_inicio=data_inicio.isoformat(),
        data_fim=data_fim.isoformat(),
        hoje=date.today().isoformat(),
        erros=erros,
        emprestimos=lista,
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
        inicio=(pagina - 1) * emprestimos_repo.POR_PAGINA + 1 if total else 0,
        fim=min(pagina * emprestimos_repo.POR_PAGINA, total),
    )


@relatorios_bp.get("/atraso")
def atraso():
    total = emprestimos_repo.contar_atrasados()
    total_paginas = max(math.ceil(total / emprestimos_repo.POR_PAGINA), 1)
    pagina = min(max(request.args.get("pagina", 1, type=int), 1), total_paginas)
    lista = [_com_dias_atraso(l) for l in emprestimos_repo.listar_atrasados(pagina)]

    return render_template(
        "relatorios/atraso.html",
        aba="atraso",
        emprestimos=lista,
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
        inicio=(pagina - 1) * emprestimos_repo.POR_PAGINA + 1 if total else 0,
        fim=min(pagina * emprestimos_repo.POR_PAGINA, total),
    )
