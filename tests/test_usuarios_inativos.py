import sqlite3

import pytest

from app import create_app
from app.database import get_db
from app.usuarios import validacao


def html(resposta):
    return resposta.get_data(as_text=True)


def _json(resposta):
    return resposta.get_json()["itens"]


@pytest.fixture
def reservar(app):
    def _reservar(id_usuario, id_livro, status="ativa"):
        with app.app_context():
            db = get_db()
            with db:
                db.execute(
                    "INSERT INTO reserva (data_reserva, status, id_usuario, id_livro) VALUES ('2026-10-01', ?, ?, ?)",
                    (status, id_usuario, id_livro),
                )

    return _reservar


# Telefone e e-mail


@pytest.mark.parametrize("telefone", ["77998123456", "(67) 99999-0000", "7733331234", "(11) 3333-4444"])
def test_telefones_validos(telefone):
    assert validacao.telefone_valido("".join(c for c in telefone if c.isdigit()))


@pytest.mark.parametrize(
    "telefone",
    [
        "0099999999",   # DDD que não existe
        "2099999999",
        "77888123456",  # celular sem o 9 depois do DDD
        "7799999999",   # celular antigo de 10 dígitos
        "11111111111",  # todos os dígitos iguais
        "7733333333",
        "779812345",    # curto demais
    ],
)
def test_telefones_invalidos(telefone):
    assert not validacao.telefone_valido(telefone)


def test_cadastro_recusa_telefone_com_ddd_inexistente(post):
    resposta = post(
        "/usuarios/novo",
        {"nome": "Maria", "cpf": "39184726393", "telefone": "(00) 99999-0000"},
    )

    assert resposta.status_code == 400
    assert "Informe um telefone válido com DDD" in html(resposta)


@pytest.mark.parametrize("email", ["a@b.c", "a@b", "a b@c.com", "a..b@c.com", ".a@c.com", "a@-c.com", "a@c..com", "@c.com"])
def test_emails_invalidos(post, email):
    resposta = post(
        "/usuarios/novo",
        {"nome": "Maria", "cpf": "39184726393", "telefone": "77998123456", "email": email},
    )

    assert resposta.status_code == 400, email
    assert "Informe um e-mail válido." in html(resposta)


@pytest.mark.parametrize("email", ["maria@example.com", "maria.silva+biblio@mail.example.com.br", "m_s@c.io"])
def test_emails_validos(post, email):
    resposta = post(
        "/usuarios/novo",
        {"nome": "Maria", "cpf": "39184726393", "telefone": "77998123456", "email": email},
    )

    assert resposta.status_code == 302, email


# Exclusão


def test_exclusao_sem_historico_apaga_o_usuario(client, post, criar_usuario, consulta):
    id_usuario = criar_usuario("Camila Rodrigues Prado", cpf="39184726393")

    resposta = post(f"/usuarios/{id_usuario}/excluir")

    assert resposta.status_code == 302
    assert consulta("SELECT id_usuario FROM usuario") == []


def test_nao_exclui_quem_esta_com_livro_emprestado(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_usuario = criar_usuario("Maria Oliveira")
    registrar_emprestimo(criar_livro(), id_usuario=id_usuario)

    pagina = html(client.get(f"/usuarios/{id_usuario}/excluir"))
    post(f"/usuarios/{id_usuario}/excluir")

    assert "não pode ser excluído nem inativado" in pagina
    assert "Sim, excluir" not in pagina and "Sim, inativar" not in pagina
    assert len(consulta("SELECT id_usuario FROM usuario")) == 1


def test_nao_exclui_quem_tem_reserva_ativa_e_nao_da_erro_500(client, post, criar_usuario, criar_livro, reservar, consulta):
    id_usuario = criar_usuario("Maria Oliveira")
    reservar(id_usuario, criar_livro())

    resposta = post(f"/usuarios/{id_usuario}/excluir")

    assert resposta.status_code == 302
    assert len(consulta("SELECT id_usuario FROM usuario")) == 1
    assert "reserva ativa" in html(client.get("/usuarios"))


def test_reserva_cancelada_conta_como_historico_e_oferece_inativar(client, post, criar_usuario, criar_livro, reservar, consulta):
    id_usuario = criar_usuario("Maria Oliveira")
    reservar(id_usuario, criar_livro(), status="cancelada")

    pagina = html(client.get(f"/usuarios/{id_usuario}/excluir"))
    resposta = post(f"/usuarios/{id_usuario}/excluir")

    assert "Sim, inativar" in pagina
    assert "Sim, excluir" not in pagina
    assert resposta.status_code == 302
    assert len(consulta("SELECT id_usuario FROM usuario")) == 1


# Inativar e reativar


def test_usuario_com_historico_pode_ser_inativado(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    registrar_emprestimo(criar_livro(), status="devolvido", id_usuario=id_usuario)

    pagina = html(client.get(f"/usuarios/{id_usuario}/excluir"))
    post(f"/usuarios/{id_usuario}/inativar")

    assert "Tem certeza que deseja inativar o usuário <strong>Maria Oliveira</strong>?" in pagina
    assert consulta("SELECT ativo FROM usuario")[0]["ativo"] == 0


def test_nao_inativa_quem_tem_pendencia(post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_usuario = criar_usuario("Maria Oliveira")
    registrar_emprestimo(criar_livro(), id_usuario=id_usuario)

    post(f"/usuarios/{id_usuario}/inativar")

    assert consulta("SELECT ativo FROM usuario")[0]["ativo"] == 1


def test_inativo_some_da_lista_mas_aparece_com_o_filtro(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    criar_usuario("Carlos Souza", cpf="52998224725")
    registrar_emprestimo(criar_livro(), status="devolvido", id_usuario=id_usuario)
    post(f"/usuarios/{id_usuario}/inativar")

    padrao = html(client.get("/usuarios"))
    com_inativos = html(client.get("/usuarios", query_string={"inativos": 1}))

    linha = '<span class="table__title">{}'
    assert linha.format("Maria Oliveira") not in padrao and linha.format("Carlos Souza") in padrao
    assert linha.format("Maria Oliveira") in com_inativos and linha.format("Carlos Souza") in com_inativos
    assert "Inativo" in com_inativos
    assert "Reativar" in com_inativos


def test_busca_que_so_acha_inativo_mostra_o_inativo(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    registrar_emprestimo(criar_livro(), status="devolvido", id_usuario=id_usuario)
    post(f"/usuarios/{id_usuario}/inativar")

    pagina = html(client.get("/usuarios", query_string={"q": "123.456.789-09"}))

    assert "Maria Oliveira" in pagina
    assert "Só há cadastros inativos para esta busca." in pagina


def test_sugestoes_dos_formularios_nao_trazem_inativos(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    registrar_emprestimo(criar_livro(), status="devolvido", id_usuario=id_usuario)
    post(f"/usuarios/{id_usuario}/inativar")

    formularios = _json(client.get("/usuarios/sugestoes", query_string={"q": "maria"}))
    consulta_de_usuarios = _json(client.get("/usuarios/sugestoes", query_string={"q": "maria", "inativos": 1}))

    assert formularios == []
    assert [item["titulo"] for item in consulta_de_usuarios] == ["Maria Oliveira"]
    assert "Inativo" in consulta_de_usuarios[0]["subtitulo"]


def test_inativo_nao_pega_livro_nem_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta, reservar):
    id_usuario = criar_usuario("Maria Oliveira")
    outro = criar_usuario("Outro Leitor", cpf="52998224725")
    registrar_emprestimo(criar_livro("Antigo"), status="devolvido", id_usuario=id_usuario)
    post(f"/usuarios/{id_usuario}/inativar")
    livro = criar_livro("Dom Casmurro", quantidade=1)

    resposta = post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": livro})

    assert resposta.status_code == 400
    assert "está inativo" in html(resposta)
    assert consulta("SELECT * FROM emprestimo WHERE id_livro = ?", (livro,)) == []

    registrar_emprestimo(livro, id_usuario=outro)
    resposta = post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": livro})
    assert resposta.status_code == 400
    assert "está inativo" in html(resposta)


def test_usuario_inexistente_no_emprestimo_nao_da_erro_500(post, criar_livro):
    resposta = post("/emprestimos/novo", {"id_usuario": 999, "id_livro": criar_livro()})

    assert resposta.status_code == 400


def test_painel_conta_so_usuarios_ativos(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    criar_usuario("Carlos Souza", cpf="52998224725")
    registrar_emprestimo(criar_livro(), status="devolvido", id_usuario=id_usuario)
    post(f"/usuarios/{id_usuario}/inativar")

    pagina = html(client.get("/"))

    assert '<span class="stat-card__value">1</span>' in pagina


def test_cadastrar_cpf_de_inativo_oferece_reativar(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_usuario = criar_usuario("Camila Prado", cpf="39184726393")
    registrar_emprestimo(criar_livro(), status="devolvido", id_usuario=id_usuario)
    post(f"/usuarios/{id_usuario}/inativar")

    resposta = post(
        "/usuarios/novo",
        {"nome": "Camila Prado", "cpf": "391.847.263-93", "telefone": "77998123456"},
    )
    pagina = html(resposta)

    assert resposta.status_code == 400
    assert "Este CPF pertence a um usuário inativo." in pagina
    assert f"/usuarios/{id_usuario}/reativar" in pagina
    assert "Reativar este usuário" in pagina
    assert len(consulta("SELECT id_usuario FROM usuario")) == 1

    reativar = post(f"/usuarios/{id_usuario}/reativar")

    assert reativar.status_code == 302
    assert reativar.headers["Location"].endswith(f"/usuarios/{id_usuario}/editar")
    assert consulta("SELECT ativo FROM usuario")[0]["ativo"] == 1


def test_cpf_de_usuario_ativo_continua_com_a_mensagem_antiga(post, criar_usuario):
    criar_usuario("Maria Oliveira", cpf="12345678909")

    resposta = post("/usuarios/novo", {"nome": "Outra", "cpf": "12345678909", "telefone": "77998123456"})

    assert "Já existe um usuário cadastrado com este CPF." in html(resposta)
    assert "Reativar este usuário" not in html(resposta)


# Livros e banco antigo


def test_livro_com_reserva_nao_da_erro_500_ao_excluir(client, post, criar_usuario, criar_livro, reservar, consulta):
    id_livro = criar_livro("Dom Casmurro")
    reservar(criar_usuario("Maria Oliveira"), id_livro, status="cancelada")

    pagina = html(client.get(f"/livros/{id_livro}/excluir"))
    resposta = post(f"/livros/{id_livro}/excluir")

    assert "1 reserva registrada" in pagina
    assert "Sim, excluir" not in pagina
    assert resposta.status_code == 302
    assert len(consulta("SELECT id_livro FROM livro")) == 1


def test_banco_antigo_ganha_a_coluna_ativo_sem_perder_usuarios(tmp_path):
    caminho = tmp_path / "antigo.db"
    antigo = sqlite3.connect(caminho)
    antigo.executescript(
        """
        CREATE TABLE usuario (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, cpf TEXT,
            telefone TEXT, email TEXT, endereco TEXT, tipo_usuario TEXT
        );
        INSERT INTO usuario (nome, cpf) VALUES ('Maria Antiga', '12345678909');
        """
    )
    antigo.commit()
    antigo.close()

    app = create_app({"TESTING": True, "DATABASE": caminho, "SECRET_KEY": "x"})

    with app.app_context():
        linha = get_db().execute("SELECT nome, ativo FROM usuario").fetchone()
        assert tuple(linha) == ("Maria Antiga", 1)


def test_banco_recusa_cpf_repetido_mesmo_sem_passar_pela_validacao(app):
    with app.app_context():
        db = get_db()
        with db:
            db.execute("INSERT INTO usuario (nome, cpf) VALUES ('Maria', '12345678909')")
        with pytest.raises(sqlite3.IntegrityError):
            with db:
                db.execute("INSERT INTO usuario (nome, cpf) VALUES ('Outra Maria', '12345678909')")


def test_banco_aceita_varios_usuarios_sem_cpf(app):
    with app.app_context():
        db = get_db()
        with db:
            db.execute("INSERT INTO usuario (nome) VALUES ('Sem CPF 1')")
            db.execute("INSERT INTO usuario (nome) VALUES ('Sem CPF 2')")
        assert db.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 2
