import json
import sqlite3
import time

import pytest

from app import auth, create_app, email_envio, recuperacao
from app.database import get_db
from tests.conftest import LOGIN_DE_TESTE, SENHA_DE_TESTE, TOKEN


def html(resposta):
    return resposta.get_data(as_text=True)


def _post(cliente, url, dados=None):
    with cliente.session_transaction() as sessao:
        sessao["csrf_token"] = TOKEN
    return cliente.post(url, data={**(dados or {}), "csrf_token": TOKEN})


@pytest.fixture
def emails(monkeypatch):
    """Troca o envio de verdade por uma lista, para ver o que seria enviado."""
    enviados = []
    monkeypatch.setattr(email_envio, "esta_configurado", lambda: True)
    monkeypatch.setattr(email_envio, "enviar_codigo", lambda destino, codigo, minutos: enviados.append((destino, codigo)))
    return enviados


@pytest.fixture
def com_email(app, id_funcionaria):
    with app.app_context():
        db = get_db()
        with db:
            db.execute("UPDATE funcionario SET email_recuperacao = 'maria@example.com'")


def _pedir_codigo(cliente, emails):
    resposta = _post(cliente, "/esqueci-senha")
    assert resposta.status_code == 302
    return emails[-1][1]


def _redefinir(cliente, codigo, senha="senha-nova-123", confirmacao=None):
    return _post(cliente, "/esqueci-senha/codigo", {"codigo": codigo, "senha": senha, "confirmacao": confirmacao or senha})


def _codigo_errado(codigo):
    return "000000" if codigo != "000000" else "111111"


# Pedir o código


def test_login_tem_link_para_recuperar_a_senha(client_anonimo, id_funcionaria):
    assert "/esqueci-senha" in html(client_anonimo.get("/entrar"))


def test_pagina_de_recuperacao_abre_sem_login(client_anonimo, com_email, emails):
    resposta = client_anonimo.get("/esqueci-senha")

    assert resposta.status_code == 200
    assert "m***@example.com" in html(resposta)
    assert "maria@example.com" not in html(resposta)


def test_pedir_codigo_envia_seis_digitos_para_o_email_cadastrado(client_anonimo, com_email, emails):
    resposta = _post(client_anonimo, "/esqueci-senha")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/esqueci-senha/codigo")
    assert len(emails) == 1
    destino, codigo = emails[0]
    assert destino == "maria@example.com"
    assert len(codigo) == 6 and codigo.isdigit()


def test_sem_email_cadastrado_nao_envia_nada(client_anonimo, id_funcionaria, emails):
    resposta = _post(client_anonimo, "/esqueci-senha")

    assert resposta.status_code == 400
    assert "Não há e-mail de recuperação cadastrado" in html(resposta)
    assert emails == []


def test_sem_configuracao_de_envio_explica_o_que_fazer(client_anonimo, com_email, monkeypatch):
    monkeypatch.setattr(email_envio, "esta_configurado", lambda: False)

    resposta = client_anonimo.get("/esqueci-senha")

    assert "ainda não foi configurado" in html(resposta)
    assert "Enviar código" not in html(resposta)


def test_falha_no_envio_avisa_e_nao_guarda_codigo(client_anonimo, com_email, emails, monkeypatch):
    def falhar(destino, codigo, minutos):
        raise email_envio.FalhaNoEnvio()

    monkeypatch.setattr(email_envio, "enviar_codigo", falhar)

    resposta = _post(client_anonimo, "/esqueci-senha")

    assert resposta.status_code == 502
    assert "Não foi possível enviar o e-mail" in html(resposta)
    assert client_anonimo.get("/esqueci-senha/codigo").status_code == 302


def test_segundo_pedido_seguido_precisa_esperar(client_anonimo, com_email, emails):
    _pedir_codigo(client_anonimo, emails)

    resposta = _post(client_anonimo, "/esqueci-senha")

    assert resposta.status_code == 429
    assert "Aguarde" in html(resposta)
    assert len(emails) == 1


# Digitar o código


def test_codigo_certo_troca_a_senha(client_anonimo, app, com_email, emails):
    codigo = _pedir_codigo(client_anonimo, emails)

    resposta = _redefinir(client_anonimo, codigo)

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/entrar")
    assert _post(client_anonimo, "/entrar", {"login": LOGIN_DE_TESTE, "senha": "senha-nova-123"}).status_code == 302
    antiga = _post(app.test_client(), "/entrar", {"login": LOGIN_DE_TESTE, "senha": SENHA_DE_TESTE})
    assert antiga.status_code == 401


def test_codigo_aceita_espacos(client_anonimo, com_email, emails):
    codigo = _pedir_codigo(client_anonimo, emails)

    resposta = _redefinir(client_anonimo, f"{codigo[:3]} {codigo[3:]}")

    assert resposta.status_code == 302


def test_codigo_so_funciona_uma_vez(client_anonimo, com_email, emails):
    codigo = _pedir_codigo(client_anonimo, emails)
    _redefinir(client_anonimo, codigo)

    resposta = _redefinir(client_anonimo, codigo, senha="outra-senha-456")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/esqueci-senha")


def test_codigo_errado_conta_tentativa(client_anonimo, com_email, emails):
    codigo = _pedir_codigo(client_anonimo, emails)

    resposta = _redefinir(client_anonimo, _codigo_errado(codigo))

    assert resposta.status_code == 400
    assert "Código incorreto" in html(resposta)
    assert "4 tentativa" in html(resposta)


def test_cinco_erros_cancelam_o_codigo(client_anonimo, com_email, emails):
    codigo = _pedir_codigo(client_anonimo, emails)

    for _ in range(recuperacao.TENTATIVAS_DO_CODIGO):
        resposta = _redefinir(client_anonimo, _codigo_errado(codigo))

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/esqueci-senha")
    # Nem o código certo vale mais.
    assert _redefinir(client_anonimo, codigo).headers["Location"].endswith("/esqueci-senha")


def test_codigo_vencido_nao_vale(client_anonimo, app, com_email, emails):
    codigo = _pedir_codigo(client_anonimo, emails)
    app.extensions["recuperacao"]["expira"] = time.monotonic() - 1

    resposta = _redefinir(client_anonimo, codigo)

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/esqueci-senha")


def test_senha_nova_invalida_mantem_o_codigo(client_anonimo, com_email, emails):
    codigo = _pedir_codigo(client_anonimo, emails)

    curta = _redefinir(client_anonimo, codigo, senha="curta")
    diferente = _redefinir(client_anonimo, codigo, senha="senha-nova-123", confirmacao="outra-coisa-1")

    assert curta.status_code == 400 and "pelo menos 8 caracteres" in html(curta)
    assert diferente.status_code == 400 and "diferentes" in html(diferente)
    assert _redefinir(client_anonimo, codigo).status_code == 302


def test_tela_do_codigo_sem_pedido_volta_para_o_inicio(client_anonimo, com_email):
    resposta = client_anonimo.get("/esqueci-senha/codigo")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/esqueci-senha")


def test_recuperar_a_senha_libera_o_bloqueio_por_tentativas(client_anonimo, com_email, emails):
    for _ in range(auth.TENTATIVAS_ANTES_DE_ESPERAR):
        _post(client_anonimo, "/entrar", {"login": LOGIN_DE_TESTE, "senha": "errada"})
    assert _post(client_anonimo, "/entrar", {"login": LOGIN_DE_TESTE, "senha": "errada"}).status_code == 429

    _redefinir(client_anonimo, _pedir_codigo(client_anonimo, emails))

    assert _post(client_anonimo, "/entrar", {"login": LOGIN_DE_TESTE, "senha": "senha-nova-123"}).status_code == 302


def test_mascarar_email():
    assert recuperacao.mascarar_email("maria@example.com") == "m***@example.com"


# E-mail de recuperação na conta


def test_primeiro_acesso_guarda_o_email(client_anonimo, app):
    _post(client_anonimo, "/primeiro-acesso", {
        "nome": "Ana", "login": "ana", "senha": "senha-forte-1", "confirmacao": "senha-forte-1", "email": "ana@example.com",
    })

    with app.app_context():
        assert get_db().execute("SELECT email_recuperacao FROM funcionario").fetchone()[0] == "ana@example.com"


def test_primeiro_acesso_sem_email_continua_valido(client_anonimo, app):
    resposta = _post(client_anonimo, "/primeiro-acesso", {
        "nome": "Ana", "login": "ana", "senha": "senha-forte-1", "confirmacao": "senha-forte-1", "email": "",
    })

    assert resposta.status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT email_recuperacao FROM funcionario").fetchone()[0] is None


def test_primeiro_acesso_recusa_email_invalido(client_anonimo):
    resposta = _post(client_anonimo, "/primeiro-acesso", {
        "nome": "Ana", "login": "ana", "senha": "senha-forte-1", "confirmacao": "senha-forte-1", "email": "sem-arroba",
    })

    assert resposta.status_code == 400
    assert "Informe um e-mail válido." in html(resposta)


def test_conta_salva_o_email_com_a_senha_atual(client, app):
    resposta = _post(client, "/conta/email", {"email": "novo@example.com", "senha_atual": SENHA_DE_TESTE})

    assert resposta.status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT email_recuperacao FROM funcionario").fetchone()[0] == "novo@example.com"
    assert "novo@example.com" in html(client.get("/conta"))


def test_conta_exige_a_senha_atual_para_mudar_o_email(client, app, com_email):
    resposta = _post(client, "/conta/email", {"email": "outro@example.com", "senha_atual": "errada"})

    assert resposta.status_code == 400
    assert "A senha atual está incorreta." in html(resposta)
    with app.app_context():
        assert get_db().execute("SELECT email_recuperacao FROM funcionario").fetchone()[0] == "maria@example.com"


def test_conta_recusa_email_invalido(client):
    resposta = _post(client, "/conta/email", {"email": "sem-arroba", "senha_atual": SENHA_DE_TESTE})

    assert resposta.status_code == 400
    assert "Informe um e-mail válido." in html(resposta)


def test_conta_deixa_remover_o_email(client, app, com_email):
    resposta = _post(client, "/conta/email", {"email": "", "senha_atual": SENHA_DE_TESTE})

    assert resposta.status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT email_recuperacao FROM funcionario").fetchone()[0] is None


def test_banco_antigo_ganha_a_coluna_do_email(tmp_path):
    banco = tmp_path / "antigo.db"
    with sqlite3.connect(banco) as con:
        con.execute(
            "CREATE TABLE funcionario (id_funcionario INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, "
            "cargo TEXT, login TEXT NOT NULL UNIQUE, senha_hash TEXT NOT NULL)"
        )
        con.execute("INSERT INTO funcionario (nome, login, senha_hash) VALUES ('A', 'a', 'x')")
    app = create_app({"TESTING": True, "DATABASE": banco, "SECRET_KEY": "teste"})
    with app.app_context():
        assert get_db().execute("SELECT email_recuperacao FROM funcionario").fetchone()[0] is None


# Envio de verdade (sem internet)


def test_configuracao_ausente_ou_incompleta(app, tmp_path):
    arquivo = tmp_path / "email.json"
    app.config["ARQUIVO_EMAIL"] = arquivo
    with app.app_context():
        assert not email_envio.esta_configurado()
        arquivo.write_text(json.dumps({"remetente": "a@gmail.com", "senha_app": ""}))
        assert not email_envio.esta_configurado()
        arquivo.write_text(json.dumps({"remetente": "a@gmail.com", "senha_app": "abcd efgh"}))
        assert email_envio.esta_configurado()


def test_envio_usa_o_gmail_e_a_senha_do_arquivo(app, tmp_path, monkeypatch):
    chamadas = {}

    class FalsoSMTP:
        def __init__(self, servidor, porta, timeout, context):
            chamadas["servidor"] = (servidor, porta)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, usuario, senha):
            chamadas["login"] = (usuario, senha)

        def send_message(self, mensagem):
            chamadas["mensagem"] = mensagem

    monkeypatch.setattr(email_envio.smtplib, "SMTP_SSL", FalsoSMTP)
    arquivo = tmp_path / "email.json"
    arquivo.write_text(json.dumps({"remetente": "biblioteca@gmail.com", "senha_app": "abcd efgh ijkl mnop"}))
    app.config["ARQUIVO_EMAIL"] = arquivo

    with app.app_context():
        email_envio.enviar_codigo("maria@example.com", "123456", 10)

    assert chamadas["servidor"] == ("smtp.gmail.com", 465)
    assert chamadas["login"] == ("biblioteca@gmail.com", "abcdefghijklmnop")
    assert chamadas["mensagem"]["To"] == "maria@example.com"
    assert "123456" in chamadas["mensagem"].get_content()


def test_erro_de_rede_vira_falha_no_envio(app, tmp_path, monkeypatch):
    def sem_rede(*args, **kwargs):
        raise OSError("sem internet")

    monkeypatch.setattr(email_envio.smtplib, "SMTP_SSL", sem_rede)
    arquivo = tmp_path / "email.json"
    arquivo.write_text(json.dumps({"remetente": "biblioteca@gmail.com", "senha_app": "abc"}))
    app.config["ARQUIVO_EMAIL"] = arquivo

    with app.app_context(), pytest.raises(email_envio.FalhaNoEnvio):
        email_envio.enviar("maria@example.com", "Assunto", "Texto")
