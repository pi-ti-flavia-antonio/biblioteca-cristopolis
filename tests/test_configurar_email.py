import json

import configurar_email
from app import email_envio


def _preparar(monkeypatch, tmp_path, enviar):
    arquivo = tmp_path / "email.json"
    monkeypatch.setattr(configurar_email, "caminho_email", lambda: arquivo)
    monkeypatch.setattr(configurar_email, "create_app", lambda: _AppFalso())
    monkeypatch.setattr(email_envio, "enviar", enviar)
    return arquivo


class _AppFalso:
    def app_context(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_grava_o_arquivo_e_manda_o_teste_para_o_proprio_gmail(monkeypatch, tmp_path):
    enviados = []
    arquivo = _preparar(monkeypatch, tmp_path, lambda destino, assunto, texto: enviados.append(destino))

    deu_certo, mensagem = configurar_email.configurar(" biblioteca@gmail.com ", "abcd efgh ijkl mnop")

    assert deu_certo and "biblioteca@gmail.com" in mensagem
    assert json.loads(arquivo.read_text(encoding="utf-8")) == {"remetente": "biblioteca@gmail.com", "senha_app": "abcdefghijklmnop"}
    assert enviados == ["biblioteca@gmail.com"]


def test_sem_gmail_ou_sem_senha_nao_grava_nada(monkeypatch, tmp_path):
    arquivo = _preparar(monkeypatch, tmp_path, lambda *a: None)

    assert configurar_email.configurar("sem-arroba", "senha")[0] is False
    assert configurar_email.configurar("a@gmail.com", "")[0] is False
    assert not arquivo.exists()


def test_falha_no_envio_avisa_mas_deixa_os_dados_salvos(monkeypatch, tmp_path):
    def falhar(destino, assunto, texto):
        raise email_envio.FalhaNoEnvio()

    arquivo = _preparar(monkeypatch, tmp_path, falhar)

    deu_certo, mensagem = configurar_email.configurar("a@gmail.com", "senha")

    assert deu_certo is False and "não saiu" in mensagem
    assert arquivo.exists()
