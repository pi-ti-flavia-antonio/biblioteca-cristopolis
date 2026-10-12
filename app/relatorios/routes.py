import math
from datetime import date

from flask import Blueprint, redirect, render_template, request, send_file, url_for

from . import pdf
from ..emprestimos import repository as emprestimos_repo

relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")

LIMITE_DIAS_PERIODO = 366


def _ler_data(texto, rotulo, erros, chave):
    if not texto:
        erros[chave] = f"Informe a data {rotulo}."
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError:
        erros[chave] = f"Informe uma data {rotulo} válida."
        return None


def _validar_periodo(inicio_str, fim_str):
    erros = {}
    data_inicio = _ler_data(inicio_str, "inicial", erros, "data_inicio")
    data_fim = _ler_data(fim_str, "final", erros, "data_fim")

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
    inicio_str = request.args.get("inicio", "")
    fim_str = request.args.get("fim", "")
    enviado = "inicio" in request.args or "fim" in request.args

    data_inicio, data_fim, erros = _validar_periodo(inicio_str, fim_str) if enviado else (None, None, {})
    pronto = enviado and not erros

    total = emprestimos_repo.contar_por_periodo(data_inicio, data_fim) if pronto else 0
    total_paginas = max(math.ceil(total / emprestimos_repo.POR_PAGINA), 1)
    pagina = min(max(request.args.get("pagina", 1, type=int), 1), total_paginas)
    lista = emprestimos_repo.listar_por_periodo(data_inicio, data_fim, pagina) if pronto else []

    return render_template(
        "relatorios/periodo.html",
        aba="periodo",
        data_inicio=inicio_str,
        data_fim=fim_str,
        hoje=date.today().isoformat(),
        erros=erros,
        pronto=pronto,
        emprestimos=lista,
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
        inicio=(pagina - 1) * emprestimos_repo.POR_PAGINA + 1 if total else 0,
        fim=min(pagina * emprestimos_repo.POR_PAGINA, total),
    )


@relatorios_bp.get("/periodo.pdf")
def periodo_pdf():
    data_inicio, data_fim, erros = _validar_periodo(
        request.args.get("inicio", ""), request.args.get("fim", "")
    )
    if erros:
        return redirect(url_for(
            "relatorios.periodo", inicio=request.args.get("inicio", ""), fim=request.args.get("fim", "")
        ))

    total = emprestimos_repo.contar_por_periodo(data_inicio, data_fim)
    emprestimos = emprestimos_repo.listar_por_periodo_completo(data_inicio, data_fim)
    buffer = pdf.gerar_pdf_periodo(data_inicio, data_fim, total, emprestimos)

    nome_arquivo = f"relatorio-emprestimos-{data_inicio.isoformat()}-a-{data_fim.isoformat()}.pdf"
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=nome_arquivo)


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
