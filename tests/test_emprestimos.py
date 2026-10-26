from datetime import date, timedelta

from app.database import get_db


def html(resposta):
    return resposta.get_data(as_text=True)


def test_historico_vazio_mostra_mensagem(client):
    resposta = client.get("/emprestimos")

    assert resposta.status_code == 200
    assert "Nenhum empréstimo registrado ainda." in html(resposta)


def test_realizar_emprestimo_valido(client, post, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)

    resposta = post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": id_livro})
    assert resposta.status_code == 302

    pagina = html(client.get("/emprestimos"))
    assert "Dom Casmurro" in pagina
    assert "Maria Oliveira" in pagina
    assert ">Ativo<" in pagina


def test_emprestimo_calcula_previsao_de_30_dias(client, post, criar_usuario, criar_livro, consulta):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)

    post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": id_livro})

    linha = consulta("SELECT data_emprestimo, data_devolucao_prevista FROM emprestimo")[0]
    esperado = date.fromisoformat(linha["data_emprestimo"]) + timedelta(days=30)
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


def test_menu_lateral_abre_direto_em_realizar_emprestimo(client):
    pagina = html(client.get("/"))

    assert 'href="/emprestimos/novo" class="sidebar__link">Empréstimos' in pagina


def test_abas_seguem_a_ordem_realizar_historico_reservas(client):
    pagina = html(client.get("/emprestimos/novo"))

    realizar = pagina.index(">Realizar empréstimo</a>")
    historico = pagina.index(">Histórico de empréstimos</a>")
    reservas = pagina.index(">Reservas</a>")
    assert realizar < historico < reservas



def _json(resposta):
    return resposta.get_json()["itens"]


def test_formulario_tem_dois_campos_de_busca_com_sugestoes(client):
    pagina = html(client.get("/emprestimos/novo"))

    assert pagina.count('role="combobox"') == 2
    assert 'data-url="/usuarios/sugestoes"' in pagina
    assert 'data-url="/livros/sugestoes"' in pagina
    assert 'src="/static/js/busca.js"' in pagina
    assert 'name="id_usuario" value=""' in pagina
    assert 'name="id_livro" value=""' in pagina


def test_formulario_nao_tem_mais_botao_buscar(client):
    pagina = html(client.get("/emprestimos/novo"))

    assert 'name="acao"' not in pagina
    assert ">Buscar<" not in pagina


def test_sugestoes_de_livros_ignoram_acento_e_caixa(client, criar_livro):
    criar_livro("O Pequeno Príncipe", "Antoine de Saint-Exupéry")
    criar_livro("1984", "George Orwell")

    for termo in ["principe", "PRÍNCIPE", "pequeno pri"]:
        itens = _json(client.get("/livros/sugestoes", query_string={"q": termo}))
        assert [i["titulo"] for i in itens] == ["O Pequeno Príncipe"], termo


def test_sugestoes_de_livros_acham_por_autor_e_por_isbn(client, criar_livro):
    criar_livro("Dom Casmurro", "Machado de Assis", isbn="9788535902775")
    criar_livro("1984", "George Orwell")

    por_autor = _json(client.get("/livros/sugestoes", query_string={"q": "machado"}))
    por_isbn = _json(client.get("/livros/sugestoes", query_string={"q": "978-85-359"}))

    assert [i["titulo"] for i in por_autor] == ["Dom Casmurro"]
    assert [i["titulo"] for i in por_isbn] == ["Dom Casmurro"]


def test_sugestoes_de_livros_informam_a_disponibilidade(client, criar_livro, registrar_emprestimo):
    id_esgotado = criar_livro("Quincas Borba", quantidade=1)
    registrar_emprestimo(id_esgotado)
    criar_livro("Quincas Borba Dois", quantidade=3)

    itens = {i["titulo"]: i for i in _json(client.get("/livros/sugestoes", query_string={"q": "quincas"}))}

    assert itens["Quincas Borba"]["disponiveis"] == 0
    assert itens["Quincas Borba Dois"]["disponiveis"] == 3
    assert set(itens["Quincas Borba"]) == {"id", "titulo", "subtitulo", "disponiveis"}


def test_sugestoes_sem_termo_voltam_vazias(client, criar_livro, criar_usuario):
    criar_livro("Dom Casmurro")
    criar_usuario("Maria Oliveira", cpf="12345678909")

    assert _json(client.get("/livros/sugestoes")) == []
    assert _json(client.get("/livros/sugestoes", query_string={"q": "   "})) == []
    assert _json(client.get("/usuarios/sugestoes")) == []


def test_sugestoes_mostram_no_maximo_seis(client, criar_livro):
    for numero in range(10):
        criar_livro(f"Livro {numero}")

    assert len(_json(client.get("/livros/sugestoes", query_string={"q": "livro"}))) == 6


def test_sugestoes_sem_resultado_voltam_vazias(client, criar_livro):
    criar_livro("Dom Casmurro")

    assert _json(client.get("/livros/sugestoes", query_string={"q": "xyz"})) == []


def test_sugestoes_de_usuarios_ignoram_acento_e_caixa(client, criar_usuario):
    criar_usuario("José Antônio", cpf="12345678909")
    criar_usuario("Carlos Souza", cpf="52998224725")

    for termo in ["jose antonio", "JOSÉ ANTÔNIO", "antonio"]:
        itens = _json(client.get("/usuarios/sugestoes", query_string={"q": termo}))
        assert [i["titulo"] for i in itens] == ["José Antônio"], termo


def test_sugestoes_de_usuarios_acham_cpf_com_ou_sem_pontuacao(client, criar_usuario):
    criar_usuario("José Antônio", cpf="12345678909")
    criar_usuario("Carlos Souza", cpf="52998224725")

    for termo in ["529.982.247-25", "52998224725", "529 982 247 25", "52998"]:
        itens = _json(client.get("/usuarios/sugestoes", query_string={"q": termo}))
        assert [i["titulo"] for i in itens] == ["Carlos Souza"], termo


def test_sugestoes_de_usuarios_mostram_so_o_cpf_mascarado(client, criar_usuario):
    criar_usuario("Carlos Souza", cpf="52998224725")

    resposta = client.get("/usuarios/sugestoes", query_string={"q": "carlos"})

    assert _json(resposta)[0]["subtitulo"] == "CPF ***.***.***-25"
    assert "52998224725" not in resposta.get_data(as_text=True)
    assert "529.982" not in resposta.get_data(as_text=True)


def test_formulario_com_usuario_e_livro_escolhidos_mostra_a_faixa(client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", "Machado de Assis")

    pagina = html(client.get("/emprestimos/novo", query_string={"id_usuario": id_usuario, "id_livro": id_livro}))

    assert f'name="id_usuario" value="{id_usuario}"' in pagina
    assert f'name="id_livro" value="{id_livro}"' in pagina
    assert "Maria Oliveira (***.***.***-09)" in pagina
    assert "12345678909" not in pagina and "123.456.789-09" not in pagina
    assert "Dom Casmurro, de Machado de Assis" in pagina


def test_erro_de_validacao_mantem_o_que_ja_foi_escolhido(post, criar_usuario):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")

    resposta = post("/emprestimos/novo", {"id_usuario": id_usuario, "id_livro": ""})
    pagina = html(resposta)

    assert resposta.status_code == 400
    assert "Selecione o livro." in pagina
    assert f'name="id_usuario" value="{id_usuario}"' in pagina
    assert "Maria Oliveira" in pagina


def test_formulario_tem_link_para_cadastrar_usuario_faltante(client):
    pagina = html(client.get("/emprestimos/novo"))

    assert "O usuário que você procura não está cadastrado?" in pagina
    assert 'href="/usuarios/novo?voltar=emprestimo"' in pagina


def test_arquivo_de_busca_e_servido(client):
    resposta = client.get("/static/js/busca.js")

    assert resposta.status_code == 200
    assert b"role=option" in resposta.data


def test_sugestoes_do_historico_trazem_livros_e_usuarios_com_emprestimo(client, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro")
    criar_livro("Dom Quixote")  # nunca emprestado, nao deve aparecer
    registrar_emprestimo(id_livro, id_usuario=id_usuario)

    por_livro = _json(client.get("/emprestimos/sugestoes", query_string={"q": "dom"}))
    por_usuario = _json(client.get("/emprestimos/sugestoes", query_string={"q": "MARIA"}))

    assert [(i["rotulo"], i["titulo"]) for i in por_livro] == [("Livro", "Dom Casmurro")]
    assert [(i["rotulo"], i["titulo"]) for i in por_usuario] == [("Usuário", "Maria Oliveira")]


def test_sugestoes_do_historico_ignoram_acento(client, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario = criar_usuario("José Antônio", cpf="12345678909")
    registrar_emprestimo(criar_livro("Vidas Secas"), id_usuario=id_usuario)

    itens = _json(client.get("/emprestimos/sugestoes", query_string={"q": "jose antonio"}))

    assert [i["titulo"] for i in itens] == ["José Antônio"]


def test_sugestoes_das_devolucoes_so_olham_emprestimos_ativos(client, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    registrar_emprestimo(criar_livro("Dom Casmurro"), id_usuario=id_usuario, status="devolvido")
    registrar_emprestimo(criar_livro("Dom Quixote"), id_usuario=id_usuario)

    historico = _json(client.get("/emprestimos/sugestoes", query_string={"q": "dom"}))
    ativos = _json(client.get("/emprestimos/sugestoes", query_string={"q": "dom", "ativos": "1"}))

    assert {i["titulo"] for i in historico} == {"Dom Casmurro", "Dom Quixote"}
    assert [i["titulo"] for i in ativos] == ["Dom Quixote"]


def test_sugestoes_do_historico_sem_termo_voltam_vazias(client):
    assert _json(client.get("/emprestimos/sugestoes")) == []


def test_as_quatro_barras_de_consulta_tem_sugestoes(client):
    esperado = {
        "/livros": 'data-url="/livros/sugestoes"',
        "/usuarios": 'data-url="/usuarios/sugestoes?inativos=1"',
        "/emprestimos": 'data-url="/emprestimos/sugestoes"',
        "/devolucoes": 'data-url="/emprestimos/sugestoes?ativos=1"',
    }
    for rota, trecho in esperado.items():
        pagina = html(client.get(rota))
        assert "data-busca-filtro" in pagina, rota
        assert trecho in pagina, rota
        assert 'role="combobox"' in pagina, rota
        assert 'name="q"' in pagina, rota


def test_barra_de_consulta_mantem_o_termo_e_o_botao_buscar(client, criar_livro):
    criar_livro("Dom Casmurro")

    pagina = html(client.get("/livros", query_string={"q": "casmurro"}))

    assert 'value="casmurro"' in pagina
    assert ">Buscar<" in pagina
    assert ">Limpar<" in pagina


def test_script_de_busca_e_carregado_em_todas_as_paginas(client):
    for rota in ["/", "/livros", "/usuarios", "/emprestimos", "/devolucoes", "/emprestimos/novo", "/emprestimos/reservas"]:
        assert 'src="/static/js/busca.js"' in html(client.get(rota)), rota

