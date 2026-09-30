import requests

from app.livros import isbn_lookup


class _RespostaFalsa:
    def __init__(self, corpo, status_ok=True):
        self._corpo = corpo
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise requests.HTTPError("erro")

    def json(self):
        return self._corpo


def _get_falso(respostas_por_url):
    def _get(url, timeout=None):
        for pedaco, resposta in respostas_por_url.items():
            if pedaco in url:
                return resposta
        return _RespostaFalsa({}, status_ok=False)

    return _get


def test_encontrado_resolve_titulo_autor_e_ano(monkeypatch):
    respostas = {
        "/isbn/0201558025.json": _RespostaFalsa({
            "title": "Concrete mathematics",
            "authors": [{"key": "/authors/OL720958A"}],
            "publish_date": "1994",
        }),
        "/authors/OL720958A.json": _RespostaFalsa({"name": "Ronald L. Graham"}),
    }
    monkeypatch.setattr(requests, "get", _get_falso(respostas))

    resultado = isbn_lookup.buscar_por_isbn("0201558025")

    assert resultado == {"titulo": "Concrete mathematics", "autor": "Ronald L. Graham", "ano_publicacao": 1994}


def test_varios_autores_sao_resolvidos_e_juntados(monkeypatch):
    respostas = {
        "/isbn/123.json": _RespostaFalsa({
            "title": "Livro X",
            "authors": [{"key": "/authors/A1"}, {"key": "/authors/A2"}],
        }),
        "/authors/A1.json": _RespostaFalsa({"name": "Autor A"}),
        "/authors/A2.json": _RespostaFalsa({"name": "Autor B"}),
    }
    monkeypatch.setattr(requests, "get", _get_falso(respostas))

    resultado = isbn_lookup.buscar_por_isbn("123")

    assert resultado["autor"] == "Autor A, Autor B"
    assert resultado["ano_publicacao"] is None


def test_sem_authors_usa_by_statement_como_autor(monkeypatch):
    respostas = {
        "/isbn/999.json": _RespostaFalsa({
            "title": "Livro Y",
            "by_statement": "Fulano de Tal",
        }),
    }
    monkeypatch.setattr(requests, "get", _get_falso(respostas))

    resultado = isbn_lookup.buscar_por_isbn("999")

    assert resultado["autor"] == "Fulano de Tal"


def test_isbn_nao_encontrado_retorna_none(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: _RespostaFalsa({}, status_ok=False))

    assert isbn_lookup.buscar_por_isbn("0000000000") is None


def test_resposta_sem_titulo_retorna_none(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: _RespostaFalsa({"publish_date": "2020"}))

    assert isbn_lookup.buscar_por_isbn("0000000000") is None


def test_sem_conexao_retorna_none(monkeypatch):
    def _levantar(*args, **kwargs):
        raise requests.ConnectionError("sem rede")

    monkeypatch.setattr(requests, "get", _levantar)

    assert isbn_lookup.buscar_por_isbn("9788535902775") is None


def test_timeout_retorna_none(monkeypatch):
    def _levantar(*args, **kwargs):
        raise requests.Timeout("demorou")

    monkeypatch.setattr(requests, "get", _levantar)

    assert isbn_lookup.buscar_por_isbn("9788535902775") is None


def test_falha_ao_resolver_autor_nao_quebra_a_busca(monkeypatch):
    def _get(url, timeout=None):
        if "/isbn/" in url:
            return _RespostaFalsa({"title": "Livro Z", "authors": [{"key": "/authors/A1"}]})
        raise requests.ConnectionError("falhou ao buscar autor")

    monkeypatch.setattr(requests, "get", _get)

    resultado = isbn_lookup.buscar_por_isbn("777")

    assert resultado["titulo"] == "Livro Z"
    assert resultado["autor"] == ""
