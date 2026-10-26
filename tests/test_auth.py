import time

import pytest

from app import auth
from app.database import get_db
from tests.conftest import LOGIN_DE_TESTE, SENHA_DE_TESTE, TOKEN


def html(resposta):
    return resposta.get_data(as_text=True)


def _post_anonimo(cliente, url, dados=None):
    with cliente.session_transaction() as sessao:
        sessao["csrf_token"] = TOKEN
    return cliente.post(url, data={**(dados or {}), "csrf_token": TOKEN})


def _entrar(cliente, login=LOGIN_DE_TESTE, senha=SENHA_DE_TESTE, **extra):
    return _post_anonimo(cliente, "/entrar", {"login": login, "senha": senha, **extra})


# Primeiro acesso


def test_sem_conta_tudo_leva_ao_primeiro_acesso(client_anonimo):
    for url in ["/", "/livros", "/entrar"]:
        resposta = client_anonimo.get(url)
        assert resposta.status_code == 302, url
        assert resposta.headers["Location"].endswith("/primeiro-acesso"), url


def test_primeiro_acesso_cria_a_conta_e_ja_entra(client_anonimo, app):
    resposta = _post_anonimo(
        client_anonimo,
        "/primeiro-acesso",
        {"nome": "Ana Souza", "login": "ana", "senha": "senha-forte-1", "confirmacao": "senha-forte-1"},
    )

    assert resposta.status_code == 302
    assert client_anonimo.get("/").status_code == 200
    with app.app_context():
        linha = get_db().execute("SELECT nome, login, senha_hash FROM funcionario").fetchone()
        assert (linha["nome"], linha["login"]) == ("Ana Souza", "ana")
        assert "senha-forte-1" not in linha["senha_hash"]


@pytest.mark.parametrize(
    "dados, trecho",
    [
        ({"nome": "", "login": "ana", "senha": "senha-forte-1", "confirmacao": "senha-forte-1"}, "Informe o nome."),
        ({"nome": "Ana", "login": "", "senha": "senha-forte-1", "confirmacao": "senha-forte-1"}, "Escolha um nome de usuário."),
        ({"nome": "Ana", "login": "a na", "senha": "senha-forte-1", "confirmacao": "senha-forte-1"}, "sem espaços"),
        ({"nome": "Ana", "login": "ana", "senha": "curta", "confirmacao": "curta"}, "pelo menos 8 caracteres"),
        ({"nome": "Ana", "login": "ana", "senha": "senha-forte-1", "confirmacao": "outra-coisa-1"}, "diferentes"),
        ({"nome": "Ana", "login": "usuario123", "senha": "usuario123", "confirmacao": "usuario123"}, "igual ao nome de usuário"),
    ],
)
def test_primeiro_acesso_valida_os_campos(client_anonimo, app, dados, trecho):
    resposta = _post_anonimo(client_anonimo, "/primeiro-acesso", dados)

    assert resposta.status_code == 400
    assert trecho in html(resposta)
    with app.app_context():
        assert auth.conta() is None


def test_primeiro_acesso_nao_serve_para_criar_uma_segunda_conta(client_anonimo, id_funcionaria, app):
    resposta = _post_anonimo(
        client_anonimo,
        "/primeiro-acesso",
        {"nome": "Intrusa", "login": "intrusa", "senha": "senha-forte-1", "confirmacao": "senha-forte-1"},
    )

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/entrar")
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM funcionario").fetchone()[0] == 1


# Entrada


def test_paginas_exigem_login(client_anonimo, id_funcionaria):
    for url in ["/", "/livros", "/usuarios", "/emprestimos/novo", "/devolucoes", "/relatorios"]:
        resposta = client_anonimo.get(url)
        assert resposta.status_code == 302, url
        assert "/entrar" in resposta.headers["Location"], url


def test_pagina_inexistente_tambem_exige_login(client_anonimo, id_funcionaria):
    assert client_anonimo.get("/nao-existe").status_code == 302


def test_sugestoes_sem_login_respondem_401_em_json(client_anonimo, id_funcionaria):
    resposta = client_anonimo.get("/livros/sugestoes", query_string={"q": "dom"})

    assert resposta.status_code == 401
    assert resposta.get_json()["erro"]


def test_login_certo_entra_e_volta_para_a_pagina_pedida(client_anonimo, id_funcionaria):
    pedido = client_anonimo.get("/livros")
    destino = pedido.headers["Location"]

    resposta = _entrar(client_anonimo, proximo="/livros")

    assert destino.endswith("/entrar?proximo=/livros")
    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/livros")
    assert client_anonimo.get("/livros").status_code == 200


def test_login_ignora_o_usuario_em_maiusculas(client_anonimo, id_funcionaria):
    assert _entrar(client_anonimo, login=LOGIN_DE_TESTE.upper()).status_code == 302


@pytest.mark.parametrize("destino", ["https://outro-site.com", "//outro-site.com", "\\\\outro"])
def test_login_nao_redireciona_para_fora(client_anonimo, id_funcionaria, destino):
    resposta = _entrar(client_anonimo, proximo=destino)

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/")
    assert "outro" not in resposta.headers["Location"]


def test_login_errado_nao_entra_e_nao_diz_qual_campo_errou(client_anonimo, id_funcionaria):
    senha_errada = _entrar(client_anonimo, senha="errada-errada")
    usuario_errado = _entrar(client_anonimo, login="outra")

    for resposta in (senha_errada, usuario_errado):
        assert resposta.status_code == 401
        assert "Usuário ou senha incorretos." in html(resposta)
    assert client_anonimo.get("/").status_code == 302


def test_depois_de_cinco_erros_o_login_espera(client_anonimo, id_funcionaria):
    for _ in range(auth.TENTATIVAS_ANTES_DE_ESPERAR):
        _entrar(client_anonimo, senha="errada-errada")

    bloqueada = _entrar(client_anonimo)

    assert bloqueada.status_code == 429
    assert "Aguarde" in html(bloqueada)
    assert client_anonimo.get("/").status_code == 302


def test_a_espera_termina(client_anonimo, id_funcionaria, app):
    for _ in range(auth.TENTATIVAS_ANTES_DE_ESPERAR):
        _entrar(client_anonimo, senha="errada-errada")
    app.extensions["auth"]["bloqueado_ate"] = time.monotonic() - 1

    assert _entrar(client_anonimo).status_code == 302


def test_acerto_zera_a_contagem_de_erros(client_anonimo, id_funcionaria):
    for _ in range(auth.TENTATIVAS_ANTES_DE_ESPERAR - 1):
        _entrar(client_anonimo, senha="errada-errada")
    _entrar(client_anonimo)
    client_anonimo.post("/sair", data={"csrf_token": TOKEN})

    for _ in range(auth.TENTATIVAS_ANTES_DE_ESPERAR - 1):
        resposta = _entrar(client_anonimo, senha="errada-errada")

    assert resposta.status_code == 401


def test_tela_de_login_ja_logada_vai_para_o_painel(client):
    resposta = client.get("/entrar")

    assert resposta.status_code == 302


# Sessão e saída


def test_sessao_expirada_em_formulario_leva_ao_login_e_nao_a_erro_400(client_anonimo, id_funcionaria):
    resposta = client_anonimo.post("/livros/novo", data={"titulo": "Dom Casmurro"})

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/entrar")
    assert "sessão expirou" in html(client_anonimo.get("/entrar"))


def test_sessao_vence_depois_de_ficar_parada(app, id_funcionaria):
    app.config["PERMANENT_SESSION_LIFETIME"] = 1
    cliente = app.test_client()
    _entrar(cliente)
    assert cliente.get("/").status_code == 200

    time.sleep(2.2)

    assert cliente.get("/").status_code == 302


def test_sair_encerra_a_sessao(client):
    with client.session_transaction() as sessao:
        sessao["csrf_token"] = TOKEN

    resposta = client.post("/sair", data={"csrf_token": TOKEN})

    assert resposta.status_code == 302
    assert client.get("/").status_code == 302


def test_sair_exige_token(client):
    assert client.post("/sair").status_code == 400


def test_menu_mostra_nome_trocar_senha_e_sair(client):
    pagina = html(client.get("/"))

    assert "Funcionária de Teste" in pagina
    assert "Minha conta" in pagina
    assert ">Sair</button>" in pagina


# Trocar senha


def _trocar(post, atual=SENHA_DE_TESTE, nova="nova-senha-123", confirmacao=None):
    return post(
        "/conta/senha",
        {"senha_atual": atual, "senha": nova, "confirmacao": nova if confirmacao is None else confirmacao},
    )


def test_trocar_senha_funciona(client, post, app):
    resposta = _trocar(post)

    assert resposta.status_code == 302
    novo = app.test_client()
    assert _entrar(novo, senha=SENHA_DE_TESTE).status_code == 401
    assert _entrar(novo, senha="nova-senha-123").status_code == 302


@pytest.mark.parametrize(
    "argumentos, trecho",
    [
        ({"atual": "errada-errada"}, "senha atual está incorreta"),
        ({"nova": "curta"}, "pelo menos 8 caracteres"),
        ({"confirmacao": "diferente-123"}, "diferentes"),
        ({"nova": SENHA_DE_TESTE}, "diferente da atual"),
    ],
)
def test_trocar_senha_valida(client, post, argumentos, trecho):
    resposta = _trocar(post, **argumentos)

    assert resposta.status_code == 400
    assert trecho in html(resposta)


def test_pagina_da_conta_pede_confirmacao_nas_duas_acoes(client):
    pagina = html(client.get("/conta"))

    assert 'data-confirmar="Trocar a senha?"' in pagina
    assert 'data-confirmar="Salvar as alterações da conta?"' in pagina
    assert pagina.count('id="senha_atual"') == 0  # os campos têm prefixo, sem ids repetidos


def test_pagina_da_conta_exige_login(client_anonimo, id_funcionaria):
    for url in ["/conta", "/conta/senha"]:
        assert client_anonimo.get(url).status_code == 302, url


# Mudar nome e usuário


def _alterar(post, nome="Nova Pessoa", login="novo.usuario", senha_atual=SENHA_DE_TESTE):
    return post("/conta/dados", {"nome": nome, "login": login, "senha_atual": senha_atual})


def test_alterar_usuario_e_nome(client, post, app):
    resposta = _alterar(post)

    assert resposta.status_code == 302
    assert "Nova Pessoa" in html(client.get("/"))
    novo = app.test_client()
    assert _entrar(novo, login=LOGIN_DE_TESTE).status_code == 401
    assert _entrar(novo, login="novo.usuario").status_code == 302


def test_alterar_dados_mantem_a_senha(post, app):
    _alterar(post)

    assert _entrar(app.test_client(), login="novo.usuario", senha=SENHA_DE_TESTE).status_code == 302


@pytest.mark.parametrize(
    "argumentos, trecho",
    [
        ({"senha_atual": "errada-errada"}, "senha atual está incorreta"),
        ({"nome": ""}, "Informe o nome."),
        ({"login": ""}, "Escolha um nome de usuário."),
        ({"login": "dois nomes"}, "sem espaços"),
    ],
)
def test_alterar_dados_valida(client, post, app, argumentos, trecho):
    resposta = _alterar(post, **argumentos)

    assert resposta.status_code == 400
    assert trecho in html(resposta)
    assert _entrar(app.test_client()).status_code == 302  # nada mudou


# Redefinir senha (script)


def test_redefinir_senha_pelo_script_troca_a_senha(app, id_funcionaria):
    with app.app_context():
        auth.redefinir_senha("senha-redefinida-1")

    cliente = app.test_client()
    assert _entrar(cliente, senha=SENHA_DE_TESTE).status_code == 401
    assert _entrar(cliente, senha="senha-redefinida-1").status_code == 302
