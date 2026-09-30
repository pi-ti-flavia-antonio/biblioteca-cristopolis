from datetime import date

from app.database import get_db


def html(resposta):
    return resposta.get_data(as_text=True)


def test_lista_vazia_mostra_mensagem(client):
    resposta = client.get("/devolucoes")

    assert resposta.status_code == 200
    assert "Nenhum empréstimo ativo no momento." in html(resposta)


def test_lista_mostra_apenas_emprestimos_ativos(client, criar_usuario, criar_livro, registrar_emprestimo):
    id_livro_ativo = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro_ativo)

    id_livro_devolvido = criar_livro("1984", quantidade=1)
    registrar_emprestimo(id_livro_devolvido, status="devolvido")

    pagina = html(client.get("/devolucoes"))

    assert "Dom Casmurro" in pagina
    assert "1984" not in pagina


def test_registrar_devolucao_no_prazo(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro, id_usuario=id_usuario)
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]

    resposta = post(f"/devolucoes/{id_emprestimo}/registrar")

    assert resposta.status_code == 302
    pagina = html(client.get("/devolucoes"))
    assert "Nenhum empréstimo ativo no momento." in pagina

    linha = consulta("SELECT status, data_devolucao_real FROM emprestimo")[0]
    assert linha["status"] == "devolvido"
    assert linha["data_devolucao_real"] == date.today().isoformat()


def test_registrar_devolucao_mostra_mensagem_no_prazo(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro, id_usuario=id_usuario)
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]

    post(f"/devolucoes/{id_emprestimo}/registrar")

    assert "Devolvido no prazo." in html(client.get("/devolucoes"))


def test_registrar_devolucao_atrasada_informa_dias(app, client, post, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    with app.app_context():
        db = get_db()
        with db:
            id_emprestimo = db.execute(
                "INSERT INTO emprestimo (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro) "
                "VALUES ('2020-01-01', '2020-01-15', 'ativo', ?, ?)",
                (id_usuario, id_livro),
            ).lastrowid

    post(f"/devolucoes/{id_emprestimo}/registrar")

    assert "dias de atraso." in html(client.get("/devolucoes"))


def test_devolucao_libera_exemplar_do_livro(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro, id_usuario=id_usuario)

    assert "0 de 1" in html(client.get("/livros"))

    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]
    post(f"/devolucoes/{id_emprestimo}/registrar")

    assert "1 de 1" in html(client.get("/livros"))


def test_usuario_pode_emprestar_de_novo_apos_devolver(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro, id_usuario=id_usuario)
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]
    post(f"/devolucoes/{id_emprestimo}/registrar")

    outro_livro = criar_livro("1984", quantidade=1)
    resposta = post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": outro_livro})

    assert resposta.status_code == 302


def test_devolver_emprestimo_inexistente_da_404(post):
    resposta = post("/devolucoes/999/registrar")

    assert resposta.status_code == 404


def test_devolver_emprestimo_ja_devolvido_da_404(post, criar_livro, registrar_emprestimo, consulta):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro, status="devolvido")
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]

    resposta = post(f"/devolucoes/{id_emprestimo}/registrar")

    assert resposta.status_code == 404


def test_post_sem_token_csrf_e_recusado(post, criar_livro, registrar_emprestimo, consulta):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]

    resposta = post(f"/devolucoes/{id_emprestimo}/registrar", com_token=False)

    assert resposta.status_code == 400
    assert consulta("SELECT status FROM emprestimo")[0]["status"] == "ativo"


def test_busca_por_livro_ou_usuario(client, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario_a = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro_a = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro_a, id_usuario=id_usuario_a)

    id_usuario_b = criar_usuario("Carlos Souza", cpf="52998224725")
    id_livro_b = criar_livro("1984", quantidade=1)
    registrar_emprestimo(id_livro_b, id_usuario=id_usuario_b)

    pagina = html(client.get("/devolucoes", query_string={"q": "carlos"}))
    assert "Carlos Souza" in pagina
    assert "Dom Casmurro" not in pagina


def test_menu_destaca_a_secao_atual(client):
    pagina = html(client.get("/devolucoes"))

    assert 'class="sidebar__link is-active" aria-current="page">Devoluções' in pagina
    assert 'class="sidebar__link">Empréstimos' in pagina
