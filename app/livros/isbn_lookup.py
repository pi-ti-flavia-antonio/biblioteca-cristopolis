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
        chave = autor.get("key")
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
    autor = ", ".join(nomes) if nomes else (registro.get("by_statement") or "")

    return {"titulo": titulo, "autor": autor, "ano_publicacao": _ano_de(registro.get("publish_date"))}


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

    return {"titulo": titulo, "autor": autor, "ano_publicacao": _ano_de(info.get("publishedDate"))}


def buscar_por_isbn(isbn):
    """Busca título, autor e ano pelo ISBN, tentando a Open Library e,
    se não encontrar, o Google Books.

    Retorna None se nenhuma das duas achar o livro, ou em qualquer falha
    de rede — a busca é só uma conveniência opcional, o cadastro manual
    continua funcionando normalmente.
    """
    return _buscar_open_library(isbn) or _buscar_google_books(isbn)
