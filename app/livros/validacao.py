import re
from datetime import date

from ..texto import limpar_isbn

CAMPOS = ("titulo", "autor", "quantidade", "categoria", "isbn", "ano_publicacao")

TAMANHO_MAX_TITULO = 200
TAMANHO_MAX_AUTOR = 150
TAMANHO_MAX_CATEGORIA = 60
QUANTIDADE_MAX = 9999
ANO_MIN = 1000


def valores_iniciais():
    return {**{campo: "" for campo in CAMPOS}, "quantidade": "1"}


def valores_do_formulario(form):
    return {campo: form.get(campo, "").strip() for campo in CAMPOS}


def valores_do_livro(livro):
    return {
        "titulo": livro["titulo"],
        "autor": livro["autor"],
        "quantidade": str(livro["quantidade_total"]),
        "categoria": livro["categoria"] or "",
        "isbn": livro["isbn"] or "",
        "ano_publicacao": "" if livro["ano_publicacao"] is None else str(livro["ano_publicacao"]),
    }


def validar_livro(valores):
    erros = {}

    titulo = valores["titulo"]
    if not titulo:
        erros["titulo"] = "Informe o título."
    elif len(titulo) > TAMANHO_MAX_TITULO:
        erros["titulo"] = f"O título pode ter no máximo {TAMANHO_MAX_TITULO} caracteres."

    autor = valores["autor"]
    if not autor:
        erros["autor"] = "Informe o autor."
    elif len(autor) > TAMANHO_MAX_AUTOR:
        erros["autor"] = f"O nome do autor pode ter no máximo {TAMANHO_MAX_AUTOR} caracteres."

    categoria = valores["categoria"]
    if len(categoria) > TAMANHO_MAX_CATEGORIA:
        erros["categoria"] = f"A categoria pode ter no máximo {TAMANHO_MAX_CATEGORIA} caracteres."

    quantidade = None
    if not valores["quantidade"]:
        erros["quantidade"] = "Informe a quantidade de exemplares."
    elif not valores["quantidade"].isdigit() or not 1 <= int(valores["quantidade"]) <= QUANTIDADE_MAX:
        erros["quantidade"] = f"A quantidade deve ser um número inteiro entre 1 e {QUANTIDADE_MAX}."
    else:
        quantidade = int(valores["quantidade"])

    isbn = None
    if valores["isbn"]:
        limpo = limpar_isbn(valores["isbn"])
        formato_valido = re.fullmatch(r"[0-9Xx\- ]+", valores["isbn"]) and re.fullmatch(
            r"\d{9}[\dX]|\d{13}", limpo
        )
        if formato_valido:
            isbn = limpo
        else:
            erros["isbn"] = "O ISBN deve ter 10 ou 13 dígitos. Hífens e espaços são aceitos."

    ano = None
    if valores["ano_publicacao"]:
        ano_atual = date.today().year
        if valores["ano_publicacao"].isdigit() and ANO_MIN <= int(valores["ano_publicacao"]) <= ano_atual:
            ano = int(valores["ano_publicacao"])
        else:
            erros["ano_publicacao"] = f"Informe um ano entre {ANO_MIN} e {ano_atual}."

    dados = {
        "titulo": titulo,
        "autor": autor,
        "categoria": categoria,
        "quantidade": quantidade,
        "isbn": isbn,
        "ano_publicacao": ano,
    }
    return dados, erros
