import json

import pytest
from cryptography.fernet import Fernet

import configurar_email
from app import create_app, email_envio


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """App com o e-mail e a chave em pasta temporária. Devolve (app, arquivo do e-mail, arquivo da chave, e-mails enviados)."""
    arquivo = tmp_path / "email.json"
    chave = tmp_path / "chave_backup.key"
    app = create_app({"TESTING": True, "DATABASE": tmp_path / "teste.db", "SECRET_KEY": "teste", "ARQUIVO_EMAIL": arquivo, "ARQUIVO_CHAVE": chave})
    enviados = []
    monkeypatch.setattr(configurar_email, "create_app", lambda: app)
    monkeypatch.setattr(email_envio, "enviar", lambda destino, assunto, texto: enviados.append(destino))
    return app, arquivo, chave, enviados


def test_grava_o_arquivo_e_manda_o_teste_para_o_proprio_gmail(ambiente):
    _, arquivo, _, enviados = ambiente

    deu_certo, mensagem = configurar_email.configurar(" biblioteca@gmail.com ", "abcd efgh ijkl mnop")

    assert deu_certo and "biblioteca@gmail.com" in mensagem
    assert json.loads(arquivo.read_text(encoding="utf-8"))["remetente"] == "biblioteca@gmail.com"
    assert enviados == ["biblioteca@gmail.com"]


def test_sem_gmail_ou_sem_senha_nao_grava_nada(ambiente):
    _, arquivo, _, _ = ambiente

    assert configurar_email.configurar("sem-arroba", "senha")[0] is False
    assert configurar_email.configurar("a@gmail.com", "")[0] is False
    assert not arquivo.exists()


def test_falha_no_envio_avisa_mas_deixa_os_dados_salvos(ambiente, monkeypatch):
    _, arquivo, _, _ = ambiente

    def falhar(destino, assunto, texto):
        raise email_envio.FalhaNoEnvio()

    monkeypatch.setattr(email_envio, "enviar", falhar)

    deu_certo, mensagem = configurar_email.configurar("a@gmail.com", "senha")

    assert deu_certo is False and "não saiu" in mensagem
    assert arquivo.exists()


# Senha criptografada com a chave do backup


def test_com_a_chave_do_backup_a_senha_nao_fica_em_texto(ambiente):
    app, arquivo, chave, _ = ambiente
    chave.write_bytes(Fernet.generate_key())

    deu_certo, mensagem = configurar_email.configurar("biblioteca@gmail.com", "abcd efgh ijkl mnop")

    texto = arquivo.read_text(encoding="utf-8")
    assert deu_certo and "sem criptografia" not in mensagem
    assert "abcdefghijklmnop" not in texto and "senha_app_criptografada" in texto
    with app.app_context():
        assert email_envio.ler_configuracao() == ("biblioteca@gmail.com", "abcdefghijklmnop")


def test_sem_a_chave_a_senha_fica_em_texto_e_o_aviso_diz_isso(ambiente):
    app, arquivo, _, _ = ambiente

    deu_certo, mensagem = configurar_email.configurar("biblioteca@gmail.com", "abcdefghijklmnop")

    assert deu_certo and "sem criptografia" in mensagem
    with app.app_context():
        assert email_envio.ler_configuracao() == ("biblioteca@gmail.com", "abcdefghijklmnop")


def test_chave_errada_deixa_o_envio_como_nao_configurado(ambiente):
    app, arquivo, chave, _ = ambiente
    chave.write_bytes(Fernet.generate_key())
    configurar_email.configurar("biblioteca@gmail.com", "abcdefghijklmnop")
    chave.write_bytes(Fernet.generate_key())

    with app.app_context():
        assert not email_envio.esta_configurado()


def test_chave_que_sumiu_deixa_o_envio_como_nao_configurado(ambiente):
    app, arquivo, chave, _ = ambiente
    chave.write_bytes(Fernet.generate_key())
    configurar_email.configurar("biblioteca@gmail.com", "abcdefghijklmnop")
    chave.unlink()

    with app.app_context():
        assert not email_envio.esta_configurado()


def test_arquivo_antigo_com_senha_em_texto_continua_funcionando(ambiente):
    app, arquivo, chave, _ = ambiente
    chave.write_bytes(Fernet.generate_key())
    arquivo.write_text(json.dumps({"remetente": "a@gmail.com", "senha_app": "antiga"}), encoding="utf-8")

    with app.app_context():
        assert email_envio.ler_configuracao() == ("a@gmail.com", "antiga")
