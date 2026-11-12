"""Testes de segurança: acesso sem login, token dos formulários, texto malicioso, senha e dados pessoais."""

import re
from pathlib import Path

import pytest

from app import auth, create_app
from app.database import get_db
from tests.conftest import LOGIN_DE_TESTE, SENHA_DE_TESTE, TOKEN

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = "<script>alert(1)</script>"
ENTRADAS_MALICIOSAS = ["'; DROP TABLE livro; --", "' OR '1'='1", '" OR 1=1 --', "%", "_", "\\", "%' UNION SELECT * FROM funcionario --"]


def html(resposta):
    return resposta.get_data(as_text=True)


def _rotas(metodo, com_argumentos=True):
    """Rotas do app que aceitam o método, com os números de exemplo no lugar dos argumentos."""
    app = create_app({"TESTING": True, "DATABASE": ":memory:", "SECRET_KEY": "teste"})
    rotas = []
    for regra in app.url_map.iter_rules():
        if regra.endpoint == "static" or metodo not in regra.methods:
            continue
        if regra.arguments and not com_argumentos:
            continue
        rotas.append((regra.endpoint, re.sub(r"<(?:int:)?\w+>", "1", regra.rule), regra.methods))
    return rotas


def _post_anonimo(cliente, url, dados=None):
    with cliente.session_transaction() as sessao:
        sessao["csrf_token"] = TOKEN
    return cliente.post(url, data={**(dados or {}), "csrf_token": TOKEN})


# Acesso sem login


LIVRES = {"auth.login", "auth.primeiro_acesso", "recuperacao.esqueci_senha", "recuperacao.digitar_codigo"}


@pytest.mark.parametrize("endpoint, url, _", [r for r in _rotas("GET") if r[0] not in LIVRES])
def test_toda_pagina_exige_login(client_anonimo, id_funcionaria, endpoint, url, _):
    resposta = client_anonimo.get(url)

    assert resposta.status_code in (302, 401), url
    if resposta.status_code == 302:
        assert "/entrar" in resposta.headers["Location"], url


@pytest.mark.parametrize("endpoint, url, _", [r for r in _rotas("POST") if r[0] not in LIVRES])
def test_nenhuma_acao_funciona_sem_login(client_anonimo, id_funcionaria, endpoint, url, _):
    resposta = _post_anonimo(client_anonimo, url)

    assert resposta.status_code == 302, url
    assert "/entrar" in resposta.headers["Location"], url


def test_so_o_login_e_a_recuperacao_abrem_sem_entrar(client_anonimo, id_funcionaria):
    for endpoint in sorted(LIVRES):
        regra = next(r for r in _rotas("GET") if r[0] == endpoint)
        assert client_anonimo.get(regra[1]).status_code in (200, 302), endpoint


# Token dos formulários (CSRF)


@pytest.mark.parametrize("endpoint, url, _", _rotas("POST"))
def test_toda_acao_recusa_o_formulario_sem_token(client, endpoint, url, _):
    assert client.post(url, data={}).status_code == 400, url


@pytest.mark.parametrize("endpoint, url, _", _rotas("POST"))
def test_toda_acao_recusa_token_errado(client, endpoint, url, _):
    with client.session_transaction() as sessao:
        sessao["csrf_token"] = TOKEN

    assert client.post(url, data={"csrf_token": "outro-token"}).status_code == 400, url


@pytest.mark.parametrize("endpoint, url, metodos", [r for r in _rotas("POST") if "GET" not in r[2]])
def test_acao_que_grava_nao_responde_a_get(client, endpoint, url, metodos):
    assert client.get(url).status_code == 405, url


# Texto malicioso nas telas (XSS)


def test_nome_de_usuario_com_script_aparece_como_texto(client, post, consulta):
    resposta = post(
        "/usuarios/novo",
        {"nome": SCRIPT, "telefone": "(67) 99999-0000", "endereco": "Rua A, 1", "carteirinha_modo": "automatico"},
    )
    id_usuario = consulta("SELECT id_usuario FROM usuario")[0]["id_usuario"]

    paginas = [
        html(client.get("/usuarios/novo")),  # a mensagem de "usuário cadastrado"
        html(client.get("/usuarios")),
        html(client.get(f"/usuarios/{id_usuario}")),
        html(client.get(f"/usuarios/{id_usuario}/editar")),
        html(client.get(f"/usuarios/{id_usuario}/excluir")),
    ]

    assert resposta.status_code == 302
    for pagina in paginas:
        assert SCRIPT not in pagina
        assert "&lt;script&gt;" in pagina


def test_titulo_de_livro_com_script_aparece_como_texto(client, criar_livro):
    criar_livro(titulo=SCRIPT, autor='"><img src=x onerror=alert(1)>')

    pagina = html(client.get("/livros"))

    assert SCRIPT not in pagina
    assert "<img src=x" not in pagina
    assert "&lt;script&gt;" in pagina


@pytest.mark.parametrize("url", ["/livros?q=", "/usuarios?q=", "/livros?categoria="])
def test_busca_com_script_nao_volta_como_codigo(client, url):
    pagina = html(client.get(url + SCRIPT))

    assert SCRIPT not in pagina


def test_login_digitado_volta_sem_virar_codigo(client_anonimo, id_funcionaria):
    resposta = _post_anonimo(client_anonimo, "/entrar", {"login": '"><script>alert(1)</script>', "senha": "x"})

    assert "<script>alert(1)</script>" not in html(resposta)


def test_sugestoes_saem_como_json_e_nao_como_pagina(client, criar_usuario):
    criar_usuario(SCRIPT)

    resposta = client.get("/usuarios/sugestoes?q=script")

    assert resposta.mimetype == "application/json"
    assert resposta.get_json()["itens"][0]["titulo"] == SCRIPT


# Texto com comandos SQL


@pytest.mark.parametrize("entrada", ENTRADAS_MALICIOSAS)
@pytest.mark.parametrize("url", ["/livros", "/usuarios", "/livros/sugestoes", "/usuarios/sugestoes"])
def test_busca_trata_comandos_sql_como_texto(client, criar_livro, criar_usuario, consulta, url, entrada):
    criar_livro(titulo="Dom Casmurro")
    criar_usuario("Maria Oliveira")

    resposta = client.get(url, query_string={"q": entrada})

    assert resposta.status_code == 200
    assert consulta("SELECT COUNT(*) AS n FROM livro")[0]["n"] == 1
    assert consulta("SELECT COUNT(*) AS n FROM usuario")[0]["n"] == 1
    assert consulta("SELECT COUNT(*) AS n FROM funcionario")[0]["n"] == 1


@pytest.mark.parametrize("entrada", ["%", "_"])
def test_curinga_da_busca_vale_como_letra_comum(client, criar_livro, entrada):
    criar_livro(titulo="Dom Casmurro")
    criar_livro(titulo="100% Algodão", isbn="9788535914849")
    criar_livro(titulo="Nome_com_sublinhado", isbn="9788535902778")

    itens = client.get("/livros/sugestoes", query_string={"q": entrada}).get_json()["itens"]

    titulos = [item["titulo"] for item in itens]
    assert "Dom Casmurro" not in titulos
    assert len(titulos) == 1


def test_categoria_com_comando_sql_nao_filtra_nada_nem_quebra(client, criar_livro):
    criar_livro(titulo="Dom Casmurro")

    resposta = client.get("/livros", query_string={"categoria": "x' OR '1'='1"})

    assert resposta.status_code == 200
    assert "Dom Casmurro" not in html(resposta)


def test_login_com_comando_sql_nao_entra(client_anonimo, id_funcionaria):
    for login in ["' OR '1'='1", "funcionaria' --", "funcionaria\" OR \"\"=\""]:
        resposta = _post_anonimo(client_anonimo, "/entrar", {"login": login, "senha": "' OR '1'='1"})
        assert resposta.status_code in (401, 429)
        assert client_anonimo.get("/livros").status_code == 302


def test_datas_do_relatorio_com_lixo_nao_quebram(client):
    for valor in ["'; DROP TABLE emprestimo; --", "9999-99-99", "<script>", ""]:
        for url in ["/relatorios", "/relatorios/periodo.pdf"]:
            resposta = client.get(url, query_string={"inicio": valor, "fim": valor})
            assert resposta.status_code in (200, 302), (url, valor)
            assert SCRIPT not in html(resposta)


# Senha e conta


def test_senha_fica_gravada_com_hash_e_sal(app):
    with app.app_context():
        auth.criar_conta("Ana", "ana", "mesma-senha-123")
        auth.criar_conta("Bia", "bia", "mesma-senha-123")
        hashes = [linha["senha_hash"] for linha in get_db().execute("SELECT senha_hash FROM funcionario")]

    assert all(h.startswith("scrypt:") for h in hashes)
    assert all("mesma-senha-123" not in h for h in hashes)
    assert hashes[0] != hashes[1]  # o sal faz o mesmo texto gerar hashes diferentes


def test_pagina_da_conta_nao_mostra_o_hash(client):
    pagina = html(client.get("/conta"))

    assert "scrypt:" not in pagina


def test_cookie_da_sessao_nao_e_lido_por_script_e_nao_vai_para_outro_site(client_anonimo, id_funcionaria):
    resposta = _post_anonimo(client_anonimo, "/entrar", {"login": LOGIN_DE_TESTE, "senha": SENHA_DE_TESTE})

    cookie = "; ".join(resposta.headers.getlist("Set-Cookie"))
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_trocar_o_usuario_nao_burla_a_espera_depois_de_erros(client_anonimo, id_funcionaria):
    for numero in range(auth.TENTATIVAS_ANTES_DE_ESPERAR):
        _post_anonimo(client_anonimo, "/entrar", {"login": f"usuario{numero}", "senha": "errada"})

    resposta = _post_anonimo(client_anonimo, "/entrar", {"login": LOGIN_DE_TESTE, "senha": SENHA_DE_TESTE})

    assert resposta.status_code == 429


def test_chave_secreta_nao_e_fixa(monkeypatch):
    monkeypatch.delenv("BIBLIOTECA_SECRET_KEY", raising=False)

    uma = create_app({"TESTING": True, "DATABASE": ":memory:"}).config["SECRET_KEY"]
    outra = create_app({"TESTING": True, "DATABASE": ":memory:"}).config["SECRET_KEY"]

    assert len(uma) >= 32 and uma != outra


def test_sessao_com_assinatura_falsa_nao_entra(client_anonimo, id_funcionaria):
    client_anonimo.set_cookie("session", "eyJpZF9mdW5jaW9uYXJpbyI6MX0.aaaaaa.bbbbbbbbbbbbbbbbbbbbbbbbbbb")

    resposta = client_anonimo.get("/livros")

    assert resposta.status_code == 302
    assert "/entrar" in resposta.headers["Location"]


# Dados pessoais


def test_cpf_aparece_escondido_nas_telas_de_consulta(client, criar_usuario):
    id_usuario = criar_usuario("Maria Oliveira", cpf="52998224725")

    paginas = [
        html(client.get("/usuarios")),
        html(client.get(f"/usuarios/{id_usuario}")),
        html(client.get(f"/usuarios/{id_usuario}/excluir")),
        client.get("/usuarios/sugestoes?q=Maria").get_data(as_text=True),
    ]

    for pagina in paginas:
        assert "52998224725" not in pagina
        assert "529.982.247-25" not in pagina


def test_servidor_so_atende_o_proprio_computador():
    codigo = (RAIZ / "main.py").read_text(encoding="utf-8")

    assert 'host="127.0.0.1"' in codigo
    assert "0.0.0.0" not in codigo


def test_arquivos_de_segredo_ficam_fora_do_git():
    ignorados = (RAIZ / ".gitignore").read_text(encoding="utf-8")

    for padrao in ["*.key", "client_secret*.json", "token*.json", "data/email.json", "data/*.db"]:
        assert padrao in ignorados, padrao


def test_pagina_de_erro_nao_mostra_detalhes_do_sistema(client):
    pagina = html(client.get("/pagina-que-nao-existe"))

    assert "Traceback" not in pagina
    assert "Werkzeug" not in pagina
    assert str(RAIZ) not in pagina
