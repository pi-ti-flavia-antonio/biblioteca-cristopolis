import io

from app.usuarios import validacao
from tests.conftest import TOKEN
from tests.test_usuarios import USUARIO_VALIDO

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200


def html(resposta):
    return resposta.get_data(as_text=True)


def _enviar(client, url, dados, foto=None, nome="foto.jpg", **extra):
    with client.session_transaction() as sessao:
        sessao["csrf_token"] = TOKEN
    corpo = {**dados, **extra, "csrf_token": TOKEN}
    if foto is not None:
        corpo["foto"] = (io.BytesIO(foto), nome)
    return client.post(url, data=corpo, content_type="multipart/form-data")


def _id_do_usuario(consulta):
    return consulta("SELECT id_usuario FROM usuario")[0]["id_usuario"]


# Cadastro


def test_cadastro_guarda_a_foto(client, consulta):
    resposta = _enviar(client, "/usuarios/novo", USUARIO_VALIDO, JPEG)

    assert resposta.status_code == 302
    foto = consulta("SELECT tipo_conteudo, dados FROM usuario_foto")[0]
    assert foto["tipo_conteudo"] == "image/jpeg"
    assert foto["dados"] == JPEG


def test_cadastro_aceita_png(client, consulta):
    _enviar(client, "/usuarios/novo", USUARIO_VALIDO, PNG, nome="foto.png")

    assert consulta("SELECT tipo_conteudo FROM usuario_foto")[0]["tipo_conteudo"] == "image/png"


def test_cadastro_sem_foto_continua_valido(client, consulta):
    resposta = _enviar(client, "/usuarios/novo", USUARIO_VALIDO)

    assert resposta.status_code == 302
    assert consulta("SELECT COUNT(*) AS n FROM usuario_foto")[0]["n"] == 0


def test_arquivo_que_nao_e_imagem_e_recusado(client, consulta):
    resposta = _enviar(client, "/usuarios/novo", USUARIO_VALIDO, b"<html>nao sou imagem</html>", nome="foto.jpg")

    assert resposta.status_code == 400
    assert "JPEG ou PNG" in html(resposta)
    assert consulta("SELECT COUNT(*) AS n FROM usuario")[0]["n"] == 0


def test_svg_e_recusado_mesmo_com_nome_de_imagem(client):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

    resposta = _enviar(client, "/usuarios/novo", USUARIO_VALIDO, svg, nome="foto.png")

    assert resposta.status_code == 400
    assert "JPEG ou PNG" in html(resposta)


def test_foto_grande_demais_e_recusada(client):
    grande = JPEG + b"\x00" * validacao.TAMANHO_MAX_FOTO

    resposta = _enviar(client, "/usuarios/novo", USUARIO_VALIDO, grande)

    assert resposta.status_code == 400
    assert "no máximo 1 MB" in html(resposta)


def test_arquivo_enorme_vira_pagina_de_erro(client):
    enorme = JPEG + b"\x00" * (4 * 1024 * 1024)

    resposta = _enviar(client, "/usuarios/novo", USUARIO_VALIDO, enorme)

    assert resposta.status_code == 413
    assert "grande demais" in html(resposta)


def test_erro_em_outro_campo_pede_a_foto_de_novo(client, consulta):
    resposta = _enviar(client, "/usuarios/novo", {**USUARIO_VALIDO, "nome": ""}, JPEG)

    assert resposta.status_code == 400
    assert "Escolha a foto de novo" in html(resposta)
    assert consulta("SELECT COUNT(*) AS n FROM usuario_foto")[0]["n"] == 0


# Ver a foto


def test_foto_e_servida_com_o_tipo_certo(client, consulta):
    _enviar(client, "/usuarios/novo", USUARIO_VALIDO, JPEG)
    id_usuario = _id_do_usuario(consulta)

    resposta = client.get(f"/usuarios/{id_usuario}/foto")

    assert resposta.status_code == 200
    assert resposta.mimetype == "image/jpeg"
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert resposta.get_data() == JPEG


def test_foto_exige_login(client_anonimo, id_funcionaria):
    resposta = client_anonimo.get("/usuarios/1/foto")

    assert resposta.status_code == 302
    assert "/entrar" in resposta.headers["Location"]


def test_usuario_sem_foto_da_404_na_imagem(client, criar_usuario):
    id_usuario = criar_usuario("Maria Oliveira")

    assert client.get(f"/usuarios/{id_usuario}/foto").status_code == 404


def test_pagina_do_usuario_mostra_a_foto_e_os_dados(client, consulta):
    _enviar(client, "/usuarios/novo", USUARIO_VALIDO, JPEG)
    id_usuario = _id_do_usuario(consulta)

    pagina = html(client.get(f"/usuarios/{id_usuario}"))

    assert f"/usuarios/{id_usuario}/foto" in pagina
    assert "Maria Oliveira" in pagina
    assert "Número da carteirinha" in pagina
    assert "123.456.789-09" not in pagina  # o CPF aparece escondido


def test_pagina_do_usuario_sem_foto(client, criar_usuario):
    id_usuario = criar_usuario("Maria Oliveira")

    pagina = html(client.get(f"/usuarios/{id_usuario}"))

    assert "Sem foto" in pagina
    assert f"/usuarios/{id_usuario}/foto" not in pagina


def test_pagina_de_usuario_que_nao_existe(client):
    assert client.get("/usuarios/999").status_code == 404


def test_lista_mostra_miniatura_so_de_quem_tem_foto(client, consulta):
    _enviar(client, "/usuarios/novo", USUARIO_VALIDO, JPEG)
    _enviar(client, "/usuarios/novo", {**USUARIO_VALIDO, "nome": "Bia Sem Foto", "cpf": ""})
    client.get("/usuarios")  # apaga a mensagem de "usuário cadastrado"

    pagina = html(client.get("/usuarios"))

    assert pagina.count("usuario-miniatura") == 1


# Edição


def test_edicao_troca_a_foto(client, consulta):
    _enviar(client, "/usuarios/novo", USUARIO_VALIDO, JPEG)
    id_usuario = _id_do_usuario(consulta)

    _enviar(client, f"/usuarios/{id_usuario}/editar", {**USUARIO_VALIDO, "numero_carteirinha": "11047"}, PNG, nome="nova.png")

    foto = consulta("SELECT tipo_conteudo, dados FROM usuario_foto")
    assert len(foto) == 1 and foto[0]["tipo_conteudo"] == "image/png"


def test_edicao_sem_escolher_foto_mantem_a_atual(client, consulta):
    _enviar(client, "/usuarios/novo", USUARIO_VALIDO, JPEG)
    id_usuario = _id_do_usuario(consulta)

    resposta = _enviar(client, f"/usuarios/{id_usuario}/editar", {**USUARIO_VALIDO, "nome": "Maria Souza", "numero_carteirinha": "11047"})

    assert resposta.status_code == 302
    assert consulta("SELECT dados FROM usuario_foto")[0]["dados"] == JPEG


def test_edicao_remove_a_foto(client, consulta):
    _enviar(client, "/usuarios/novo", USUARIO_VALIDO, JPEG)
    id_usuario = _id_do_usuario(consulta)

    _enviar(client, f"/usuarios/{id_usuario}/editar", {**USUARIO_VALIDO, "numero_carteirinha": "11047"}, remover_foto="1")

    assert consulta("SELECT COUNT(*) AS n FROM usuario_foto")[0]["n"] == 0


def test_formulario_de_edicao_mostra_a_foto_atual(client, consulta):
    _enviar(client, "/usuarios/novo", USUARIO_VALIDO, JPEG)
    id_usuario = _id_do_usuario(consulta)

    pagina = html(client.get(f"/usuarios/{id_usuario}/editar"))

    assert "foto-campo__atual" in pagina
    assert "Remover a foto atual" in pagina


def test_formulario_de_cadastro_aceita_envio_de_arquivo(client):
    pagina = html(client.get("/usuarios/novo"))

    assert 'enctype="multipart/form-data"' in pagina
    assert 'name="foto"' in pagina


# Exclusão


def test_excluir_o_usuario_apaga_a_foto(client, consulta):
    _enviar(client, "/usuarios/novo", USUARIO_VALIDO, JPEG)
    id_usuario = _id_do_usuario(consulta)

    _enviar(client, f"/usuarios/{id_usuario}/excluir", {})

    assert consulta("SELECT COUNT(*) AS n FROM usuario")[0]["n"] == 0
    assert consulta("SELECT COUNT(*) AS n FROM usuario_foto")[0]["n"] == 0
