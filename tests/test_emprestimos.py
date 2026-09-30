from datetime import date, timedelta

from app.database import get_db


def html(resposta):
    return resposta.get_data(as_text=True)


def test_historico_vazio_mostra_mensagem(client):
    resposta = client.get("/emprestimos")

    assert resposta.status_code == 200
    assert "Nenhum empréstimo registrado ainda." in html(resposta)


def test_formulario_lista_usuarios_e_livros(client, criar_usuario, criar_livro):
    criar_usuario("Maria Oliveira", cpf="12345678909")
    criar_livro("Dom Casmurro", quantidade=2)

    pagina = html(client.get("/emprestimos/novo"))

    assert "Maria Oliveira" in pagina
    assert "Dom Casmurro" in pagina
    assert "2 disponíveis" in pagina


def test_realizar_emprestimo_valido(client, post, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)

    resposta = post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": id_livro})
    assert resposta.status_code == 302

    pagina = html(client.get("/emprestimos"))
    assert "Dom Casmurro" in pagina
    assert "Maria Oliveira" in pagina
    assert ">Ativo<" in pagina


def test_emprestimo_calcula_previsao_de_14_dias(client, post, criar_usuario, criar_livro, consulta):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)

    post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": id_livro})

    linha = consulta("SELECT data_emprestimo, data_devolucao_prevista FROM emprestimo")[0]
    esperado = date.fromisoformat(linha["data_emprestimo"]) + timedelta(days=14)
    assert linha["data_devolucao_prevista"] == esperado.isoformat()


def test_sem_selecao_mostra_erros(client, post):
    resposta = post("/emprestimos/novo", {"id_usuario": "", "id_livro": ""})

    assert resposta.status_code == 400
    assert "Selecione o usuário." in html(resposta)
    assert "Selecione o livro." in html(resposta)


def test_bloqueia_livro_sem_exemplar_disponivel(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)  # ocupa o único exemplar
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")

    resposta = post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": id_livro})

    assert resposta.status_code == 400
    assert "não tem exemplares disponíveis" in html(resposta)


def test_bloqueia_usuario_com_pendencia(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    outro_livro = criar_livro("1984", quantidade=1)
    registrar_emprestimo(outro_livro, id_usuario=id_usuario)

    novo_livro = criar_livro("Dom Casmurro", quantidade=1)
    resposta = post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": novo_livro})

    assert resposta.status_code == 400
    assert "já está com um livro emprestado" in html(resposta)


def test_usuario_pode_pegar_outro_livro_apos_devolucao(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    livro_devolvido = criar_livro("1984", quantidade=1)
    registrar_emprestimo(livro_devolvido, status="devolvido", id_usuario=id_usuario)

    novo_livro = criar_livro("Dom Casmurro", quantidade=1)
    resposta = post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": novo_livro})

    assert resposta.status_code == 302


def test_livro_esgotado_aparece_desabilitado_no_formulario(client, criar_livro, registrar_emprestimo):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)

    pagina = html(client.get("/emprestimos/novo"))

    assert f'value="{id_livro}" disabled' in pagina


def test_historico_marca_atraso_de_emprestimo_vencido(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    with app.app_context():
        db = get_db()
        with db:
            db.execute(
                "INSERT INTO emprestimo (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro) "
                "VALUES ('2020-01-01', '2020-01-15', 'ativo', ?, ?)",
                (id_usuario, id_livro),
            )

    pagina = html(client.get("/emprestimos"))

    assert ">Atrasado<" in pagina


def test_busca_por_livro_ou_usuario(client, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario_a = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro_a = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro_a, id_usuario=id_usuario_a)

    id_usuario_b = criar_usuario("Carlos Souza", cpf="52998224725")
    id_livro_b = criar_livro("1984", quantidade=1)
    registrar_emprestimo(id_livro_b, id_usuario=id_usuario_b)

    pagina = html(client.get("/emprestimos", query_string={"q": "Casmurro"}))
    assert "Maria Oliveira" in pagina
    assert "Carlos Souza" not in pagina

    pagina = html(client.get("/emprestimos", query_string={"q": "carlos"}))
    assert "Carlos Souza" in pagina
    assert "Dom Casmurro" not in pagina


def test_post_sem_token_csrf_e_recusado(post, consulta, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)

    resposta = post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": id_livro}, com_token=False)

    assert resposta.status_code == 400
    assert consulta("SELECT id_emprestimo FROM emprestimo") == []


def test_painel_mostra_emprestimos_ativos_e_atrasados(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    with app.app_context():
        db = get_db()
        with db:
            db.execute(
                "INSERT INTO emprestimo (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro) "
                "VALUES ('2020-01-01', '2020-01-15', 'ativo', ?, ?)",
                (id_usuario, id_livro),
            )

    pagina = html(client.get("/"))

    assert '<span class="stat-card__value">1</span>' in pagina
    assert "1 em atraso" in pagina
    assert "Dom Casmurro" in pagina


def test_painel_mostra_total_mesmo_com_mais_emprestimos_que_a_lista_recente(app, client, criar_usuario, criar_livro):
    with app.app_context():
        db = get_db()
        with db:
            for numero in range(7):
                id_usuario = db.execute(
                    "INSERT INTO usuario (nome, cpf, telefone) VALUES (?, ?, ?)",
                    (f"Usuário {numero}", str(10000000000 + numero), "67999990000"),
                ).lastrowid
                id_livro = db.execute(
                    "INSERT INTO livro (titulo, autor, quantidade_total) VALUES (?, 'Autor', 1)",
                    (f"Livro {numero}",),
                ).lastrowid
                db.execute(
                    "INSERT INTO emprestimo (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro) "
                    "VALUES ('2026-09-01', '2026-09-15', 'ativo', ?, ?)",
                    (id_usuario, id_livro),
                )

    pagina = html(client.get("/"))

    assert '<span class="stat-card__value">7</span>' in pagina


def test_menu_destaca_a_secao_atual(client):
    pagina = html(client.get("/emprestimos"))

    assert 'class="sidebar__link is-active" aria-current="page">Empréstimos' in pagina
    assert 'class="sidebar__link">Usuários' in pagina


def test_formulario_tem_link_para_cadastrar_livro_faltante(client, criar_livro):
    criar_livro("Dom Casmurro", quantidade=1)  # mesmo com livros cadastrados, o aviso deve aparecer

    pagina = html(client.get("/emprestimos/novo"))

    assert "não está cadastrado no acervo" in pagina
    assert 'href="/livros/novo?voltar=emprestimo"' in pagina


def test_id_livro_na_query_pre_seleciona_o_livro(client, criar_livro):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)

    pagina = html(client.get("/emprestimos/novo", query_string={"id_livro": id_livro}))

    assert f'value="{id_livro}" selected' in pagina
