import requests

TIMEOUT_SEGUNDOS = 4
MAX_AUTORES_RESOLVIDOS = 3


def _nomes_dos_autores(autores):
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


def buscar_por_isbn(isbn):
    """Busca título, autor e ano na Open Library pelo ISBN.

    Retorna None em qualquer falha (sem internet, isbn não encontrado,
    resposta inesperada) — a busca é só uma conveniência opcional, o
    cadastro manual continua funcionando normalmente.
    """
    try:
        resposta = requests.get(f"https://openlibrary.org/isbn/{isbn}.json", timeout=TIMEOUT_SEGUNDOS)
        resposta.raise_for_status()
        registro = resposta.json()
    except (requests.RequestException, ValueError):
        return None

    titulo = registro.get("title")
    if not titulo:
        return None

    nomes = _nomes_dos_autores(registro.get("authors") or [])
    autor = ", ".join(nomes) if nomes else (registro.get("by_statement") or "")

    ano = None
    digitos = "".join(c for c in (registro.get("publish_date") or "") if c.isdigit())
    if len(digitos) >= 4:
        ano = int(digitos[-4:])

    return {"titulo": titulo, "autor": autor, "ano_publicacao": ano}
