import re

import requests

TIMEOUT_SEGUNDOS = 4
MAX_AUTORES_RESOLVIDOS = 3


def _ano_de(texto):
    encontrado = re.search(r"\d{4}", texto or "")
    return int(encontrado.group()) if encontrado else None


def _nomes_dos_autores_open_library(autores):
    nomes = []
    for autor in autores[:MAX_AUTORES_RESOLVIDOS]:
        # No registro da edição a chave vem em "key"; no da obra, dentro de "author".
        chave = autor.get("key") or (autor.get("author") or {}).get("key")
        if not chave:
            continue
        try:
            resposta = requests.get(f"https://openlibrary.org{chave}.json", timeout=TIMEOUT_SEGUNDOS)
            resposta.raise_for_status()
            nome = resposta.json().get("name")
        except (requests.RequestException, ValueError):
            continue
        if nome:
            nomes.append(nome)
    return nomes


def _autores_da_obra(registro):
    """Muitas edições não trazem o autor, que fica no registro da obra."""
    for obra in (registro.get("works") or [])[:1]:
        chave = obra.get("key")
        if not chave:
            continue
        try:
            resposta = requests.get(f"https://openlibrary.org{chave}.json", timeout=TIMEOUT_SEGUNDOS)
            resposta.raise_for_status()
            return resposta.json().get("authors") or []
        except (requests.RequestException, ValueError):
            return []
    return []


def _buscar_open_library(isbn):
    try:
        resposta = requests.get(f"https://openlibrary.org/isbn/{isbn}.json", timeout=TIMEOUT_SEGUNDOS)
        resposta.raise_for_status()
        registro = resposta.json()
    except (requests.RequestException, ValueError):
        return None

    titulo = registro.get("title")
    if not titulo:
        return None

    nomes = _nomes_dos_autores_open_library(registro.get("authors") or [])
    if not nomes and not registro.get("by_statement"):
        nomes = _nomes_dos_autores_open_library(_autores_da_obra(registro))
    autor = ", ".join(nomes) if nomes else (registro.get("by_statement") or "")

    return {
        "titulo": titulo,
        "autor": autor,
        "ano_publicacao": _ano_de(registro.get("publish_date")),
        "edicao": registro.get("edition_name") or None,
    }


def _buscar_google_books(isbn):
    try:
        resposta = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": f"isbn:{isbn}"},
            timeout=TIMEOUT_SEGUNDOS,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError):
        return None

    itens = dados.get("items") or []
    if not itens:
        return None

    info = itens[0].get("volumeInfo") or {}
    titulo = info.get("title")
    if not titulo:
        return None

    autor = ", ".join(info.get("authors") or [])

    return {"titulo": titulo, "autor": autor, "ano_publicacao": _ano_de(info.get("publishedDate")), "edicao": None}


def buscar_por_isbn(isbn):
    """Busca título, autor, ano e edição pelo ISBN, tentando a Open Library e,
    se não encontrar ou se faltar o autor ou o ano, o Google Books.

    Retorna None se nenhuma das duas achar o livro, ou em qualquer falha
    de rede — a busca é só uma conveniência opcional, o cadastro manual
    continua funcionando normalmente.
    """
    encontrado = _buscar_open_library(isbn)
    if encontrado is None:
        return _buscar_google_books(isbn)

    if not encontrado["autor"] or encontrado["ano_publicacao"] is None:
        complemento = _buscar_google_books(isbn)
        if complemento:
            encontrado["autor"] = encontrado["autor"] or complemento["autor"]
            if encontrado["ano_publicacao"] is None:
                encontrado["ano_publicacao"] = complemento["ano_publicacao"]
    return encontrado
