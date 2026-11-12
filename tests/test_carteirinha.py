import sqlite3

import pytest

from app import create_app
from app.database import get_db
from app.usuarios import repository
from tests.test_usuarios import USUARIO_VALIDO


def html(resposta):
    return resposta.get_data(as_text=True)


def _manual(numero, **extra):
    return {**USUARIO_VALIDO, "carteirinha_modo": "manual", "numero_carteirinha": numero, **extra}


def _numeros(consulta):
    return [linha["numero_carteirinha"] for linha in consulta("SELECT numero_carteirinha FROM usuario ORDER BY id_usuario")]


def _usuario_antigo(app, numero, nome="Antigo"):
    with app.app_context():
        return repository.criar(
            {"nome": nome, "cpf": None, "telefone": "67999990000", "tipo_usuario": None, "email": None,
             "endereco": "Rua A, 1", "numero_carteirinha": numero}
        )


# Cadastro


def test_cadastro_com_numero_digitado(post, consulta):
    resposta = post("/usuarios/novo", _manual("532"))

    assert resposta.status_code == 302
    assert _numeros(consulta) == [532]


def test_primeiro_numero_automatico_e_11047(post, consulta):
    post("/usuarios/novo", USUARIO_VALIDO)

    assert _numeros(consulta) == [11047]


def test_numeros_automaticos_seguem_em_sequencia(post, consulta):
    for cpf in ["123.456.789-09", "529.982.247-25", ""]:
        post("/usuarios/novo", {**USUARIO_VALIDO, "cpf": cpf})

    assert _numeros(consulta) == [11047, 11048, 11049]


def test_numero_digitado_nao_muda_a_sequencia_automatica(post, consulta):
    post("/usuarios/novo", _manual("11046", cpf=""))
    post("/usuarios/novo", USUARIO_VALIDO)

    assert _numeros(consulta) == [11046, 11047]


def test_automatico_ignora_numero_digitado(post, consulta):
    post("/usuarios/novo", {**USUARIO_VALIDO, "numero_carteirinha": "55"})

    assert _numeros(consulta) == [11047]


def test_mensagem_de_sucesso_mostra_o_numero_gerado(client, post):
    post("/usuarios/novo", USUARIO_VALIDO)

    assert "Número da carteirinha: 11047." in html(client.get("/usuarios/novo"))


def test_numero_manual_e_obrigatorio(post):
    resposta = post("/usuarios/novo", _manual(""))

    assert resposta.status_code == 400
    assert "Informe o número da carteirinha." in html(resposta)


@pytest.mark.parametrize("valor", ["abc", "12a", "-5", "1,5"])
def test_numero_manual_so_aceita_digitos(post, valor):
    resposta = post("/usuarios/novo", _manual(valor))

    assert resposta.status_code == 400
    assert "Digite só números" in html(resposta)


@pytest.mark.parametrize("valor", ["0", "11047", "20000"])
def test_numero_manual_fora_da_faixa_dos_antigos(post, valor):
    resposta = post("/usuarios/novo", _manual(valor))

    assert resposta.status_code == 400
    assert "de 1 a 11046" in html(resposta)


@pytest.mark.parametrize("valor", ["1", "11046"])
def test_numero_manual_nos_limites_da_faixa(post, valor):
    assert post("/usuarios/novo", _manual(valor)).status_code == 302


def test_numero_repetido_e_recusado(post, app):
    _usuario_antigo(app, 77, nome="Ana Antiga")

    resposta = post("/usuarios/novo", _manual("77"))

    assert resposta.status_code == 400
    assert "já é de Ana Antiga" in html(resposta)


def test_numero_de_usuario_inativo_tambem_nao_se_repete(post, app):
    id_usuario = _usuario_antigo(app, 78)
    with app.app_context():
        repository.inativar(id_usuario)

    resposta = post("/usuarios/novo", _manual("78"))

    assert resposta.status_code == 400
    assert "usuário inativo" in html(resposta)


def test_formulario_de_cadastro_oferece_as_duas_opcoes(client):
    pagina = html(client.get("/usuarios/novo"))

    assert "Escrever o número da carteirinha" in pagina
    assert "gerado automaticamente pelo sistema" in pagina


# Edição


def test_edicao_mantem_o_numero_gerado_acima_da_faixa(post, consulta):
    post("/usuarios/novo", USUARIO_VALIDO)
    id_usuario = consulta("SELECT id_usuario FROM usuario")[0]["id_usuario"]

    resposta = post(f"/usuarios/{id_usuario}/editar", {**USUARIO_VALIDO, "nome": "Maria Souza", "numero_carteirinha": "11047"})

    assert resposta.status_code == 302
    assert _numeros(consulta) == [11047]


def test_edicao_nao_deixa_trocar_por_numero_acima_da_faixa(post, consulta):
    post("/usuarios/novo", USUARIO_VALIDO)
    id_usuario = consulta("SELECT id_usuario FROM usuario")[0]["id_usuario"]

    resposta = post(f"/usuarios/{id_usuario}/editar", {**USUARIO_VALIDO, "numero_carteirinha": "15000"})

    assert resposta.status_code == 400
    assert "de 1 a 11046" in html(resposta)


def test_edicao_recusa_numero_de_outro_usuario(post, app):
    _usuario_antigo(app, 10, nome="Ana Antiga")
    id_outro = _usuario_antigo(app, 11, nome="Bia Antiga")

    resposta = post(f"/usuarios/{id_outro}/editar", {**USUARIO_VALIDO, "numero_carteirinha": "10"})

    assert resposta.status_code == 400
    assert "já é de Ana Antiga" in html(resposta)


def test_usuario_sem_numero_pode_continuar_sem_ou_ganhar_um(post, app, consulta):
    id_usuario = _usuario_antigo(app, None)

    sem_numero = post(f"/usuarios/{id_usuario}/editar", {**USUARIO_VALIDO, "numero_carteirinha": ""})
    com_numero = post(f"/usuarios/{id_usuario}/editar", {**USUARIO_VALIDO, "numero_carteirinha": "900"})

    assert sem_numero.status_code == 302
    assert com_numero.status_code == 302
    assert _numeros(consulta) == [900]


def test_usuario_com_numero_nao_pode_ficar_sem(post, app):
    id_usuario = _usuario_antigo(app, 10)

    resposta = post(f"/usuarios/{id_usuario}/editar", {**USUARIO_VALIDO, "numero_carteirinha": ""})

    assert resposta.status_code == 400
    assert "Informe o número da carteirinha." in html(resposta)


# Consulta


def test_busca_por_numero_da_carteirinha(client, post):
    post("/usuarios/novo", _manual("532", nome="Ana Antiga", cpf=""))
    post("/usuarios/novo", {**USUARIO_VALIDO, "nome": "Bia Nova", "cpf": ""})
    client.get("/usuarios")  # mostra e apaga a mensagem de "usuário cadastrado"

    antiga = html(client.get("/usuarios?q=532"))
    nova = html(client.get("/usuarios?q=11047"))

    assert "Ana Antiga" in antiga and "Bia Nova" not in antiga
    assert "Bia Nova" in nova and "Ana Antiga" not in nova


def test_lista_mostra_a_coluna_carteirinha(client, post):
    post("/usuarios/novo", USUARIO_VALIDO)

    pagina = html(client.get("/usuarios"))

    assert "Carteirinha" in pagina
    assert "11047" in pagina


def test_sugestoes_mostram_a_carteirinha(client, post):
    post("/usuarios/novo", _manual("532"))

    itens = client.get("/usuarios/sugestoes?q=Maria").get_json()["itens"]

    assert "Carteirinha 532" in itens[0]["subtitulo"]


# Banco antigo


def test_banco_antigo_ganha_a_coluna_e_o_indice_da_carteirinha(tmp_path):
    banco = tmp_path / "antigo.db"
    with sqlite3.connect(banco) as con:
        con.execute(
            "CREATE TABLE usuario (id_usuario INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, cpf TEXT, "
            "telefone TEXT, email TEXT, endereco TEXT, tipo_usuario TEXT, ativo INTEGER NOT NULL DEFAULT 1)"
        )
        con.execute("INSERT INTO usuario (nome) VALUES ('Antigo')")
    app = create_app({"TESTING": True, "DATABASE": banco, "SECRET_KEY": "teste"})

    with app.app_context():
        db = get_db()
        assert db.execute("SELECT numero_carteirinha FROM usuario").fetchone()[0] is None
        with db:
            db.execute("INSERT INTO usuario (nome, numero_carteirinha) VALUES ('A', 5)")
        with pytest.raises(sqlite3.IntegrityError), db:
            db.execute("INSERT INTO usuario (nome, numero_carteirinha) VALUES ('B', 5)")
