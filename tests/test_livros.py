from app.livros import isbn_lookup

LIVRO_VALIDO = {
    "titulo": "Dom Casmurro",
    "autor": "Machado de Assis",
    "quantidade": "3",
    "categoria": "Romance",
    "isbn": "",
    "ano_publicacao": "",
}


def html(resposta):
    return resposta.get_data(as_text=True)


def test_acervo_vazio_mostra_mensagem(client):
    resposta = client.get("/livros")

    assert resposta.status_code == 200
    assert "Nenhum livro cadastrado ainda." in html(resposta)


def test_cadastrar_livro_valido(client, post):
    resposta = post("/livros/novo", LIVRO_VALIDO)
    assert resposta.status_code == 302

    pagina = html(client.get("/livros"))
    assert "Dom Casmurro" in pagina
    assert "Machado de Assis" in pagina
    assert "3 de 3" in pagina


def test_cadastrar_mostra_mensagem_de_sucesso(client, post):
    post("/livros/novo", LIVRO_VALIDO)

    assert "Livro cadastrado: Dom Casmurro." in html(client.get("/livros/novo"))


def test_cadastrar_sem_campos_obrigatorios_nao_grava(client, post):
    resposta = post("/livros/novo", {"titulo": "", "autor": "", "quantidade": ""})
    pagina = html(resposta)

    assert resposta.status_code == 400
    assert "Informe o título." in pagina
    assert "Informe o autor." in pagina
    assert "Informe a quantidade de exemplares." in pagina
    assert "Nenhum livro cadastrado ainda." in html(client.get("/livros"))


def test_campos_opcionais_podem_ficar_vazios(post, consulta):
    resposta = post("/livros/novo", {**LIVRO_VALIDO, "categoria": ""})

    assert resposta.status_code == 302
    livro = consulta("SELECT isbn, ano_publicacao, id_categoria FROM livro")[0]
    assert livro["isbn"] is None
    assert livro["ano_publicacao"] is None
    assert livro["id_categoria"] is None


def test_quantidade_invalida(post):
    for valor in ["0", "-2", "abc", "1.5", "10000"]:
        resposta = post("/livros/novo", {**LIVRO_VALIDO, "quantidade": valor})
        assert resposta.status_code == 400, valor
        assert "A quantidade deve ser um número inteiro" in html(resposta)


def test_ano_fora_do_intervalo(post):
    resposta = post("/livros/novo", {**LIVRO_VALIDO, "ano_publicacao": "3000"})

    assert resposta.status_code == 400
    assert "Informe um ano entre 1000 e" in html(resposta)


def test_isbn_aceita_hifens_e_grava_so_digitos(post, consulta):
    post("/livros/novo", {**LIVRO_VALIDO, "isbn": "978-85-359-0277-5"})

    assert consulta("SELECT isbn FROM livro")[0]["isbn"] == "9788535902775"


def test_isbn_invalido(post):
    for valor in ["123", "abcdefghij", "978-85-359-0277"]:
        resposta = post("/livros/novo", {**LIVRO_VALIDO, "isbn": valor})
        assert resposta.status_code == 400, valor
        assert "O ISBN deve ter 10 ou 13 dígitos" in html(resposta)


def test_isbn_duplicado_e_recusado(post, consulta):
    post("/livros/novo", {**LIVRO_VALIDO, "isbn": "9788535902775"})
    resposta = post("/livros/novo", {**LIVRO_VALIDO, "titulo": "Outro", "isbn": "978-85-359-0277-5"})

    assert resposta.status_code == 400
    assert "Já existe um livro com este ISBN: Dom Casmurro" in html(resposta)
    assert len(consulta("SELECT id_livro FROM livro")) == 1


def test_formulario_sugere_categorias_padrao_mesmo_sem_livros_cadastrados(client):
    pagina = html(client.get("/livros/novo"))

    assert '<option value="Infantil">' in pagina
    assert '<option value="Romance">' in pagina


def test_categoria_personalizada_passa_a_ser_sugerida_tambem(client, post):
    post("/livros/novo", {**LIVRO_VALIDO, "categoria": "Mangá"})

    pagina = html(client.get("/livros/novo"))

    assert '<option value="Mangá">' in pagina


def test_categoria_e_reaproveitada_sem_diferenciar_acento_e_caixa(post, consulta):
    post("/livros/novo", {**LIVRO_VALIDO, "titulo": "A", "categoria": "Ficção"})
    post("/livros/novo", {**LIVRO_VALIDO, "titulo": "B", "categoria": "ficcao"})

    assert len(consulta("SELECT id_categoria FROM categoria")) == 1


def test_busca_por_titulo_sem_acento_e_sem_caixa(client, criar_livro):
    criar_livro("O Pequeno Príncipe", "Antoine de Saint-Exupéry")
    criar_livro("1984", "George Orwell")

    for termo in ["principe", "PRÍNCIPE", "pequeno prin"]:
        pagina = html(client.get("/livros", query_string={"q": termo}))
        assert "O Pequeno Príncipe" in pagina, termo
        assert "George Orwell" not in pagina, termo


def test_busca_por_autor(client, criar_livro):
    criar_livro("O Hobbit", "J.R.R. Tolkien")
    criar_livro("1984", "George Orwell")

    pagina = html(client.get("/livros", query_string={"q": "tolkien"}))

    assert "O Hobbit" in pagina
    assert "1984" not in pagina


def test_busca_por_isbn_com_ou_sem_hifen(client, criar_livro):
    criar_livro("Dom Casmurro", isbn="9788535902775")
    criar_livro("1984", isbn="9788535914849")

    for termo in ["978-85-359-0277", "9788535902775", "0277"]:
        pagina = html(client.get("/livros", query_string={"q": termo}))
        assert "Dom Casmurro" in pagina, termo
        assert "1984" not in pagina, termo


def test_busca_sem_resultado(client, criar_livro):
    criar_livro("Dom Casmurro")

    pagina = html(client.get("/livros", query_string={"q": "xyz"}))

    assert 'Nenhum livro encontrado para "xyz".' in pagina


def test_busca_trata_curingas_como_texto(client, criar_livro):
    criar_livro("Dom Casmurro")

    pagina = html(client.get("/livros", query_string={"q": "%"}))

    assert "Dom Casmurro" not in pagina


def test_paginacao(client, criar_livro):
    for numero in range(1, 31):
        criar_livro(f"Livro {numero:02d}")

    primeira = html(client.get("/livros"))
    segunda = html(client.get("/livros", query_string={"pagina": 2}))

    assert "Livro 25" in primeira and "Livro 26" not in primeira
    assert "Mostrando 1 a 25 de 30" in primeira
    assert "Livro 26" in segunda and "Livro 30" in segunda and "Livro 25" not in segunda
    assert "Mostrando 26 a 30 de 30" in segunda


def test_pagina_alem_do_fim_mostra_a_ultima(client, criar_livro):
    criar_livro("Dom Casmurro")

    resposta = client.get("/livros", query_string={"pagina": 99})

    assert resposta.status_code == 200
    assert "Dom Casmurro" in html(resposta)


def test_disponiveis_descontam_emprestimos_ativos(client, criar_livro, registrar_emprestimo):
    id_livro = criar_livro("Dom Casmurro", quantidade=3)
    registrar_emprestimo(id_livro)
    registrar_emprestimo(id_livro, status="devolvido")

    assert "2 de 3" in html(client.get("/livros"))


def test_editar_livro(client, post, criar_livro):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    dados = {**LIVRO_VALIDO, "titulo": "Dom Casmurro (edição nova)", "quantidade": "5"}

    resposta = post(f"/livros/{id_livro}/editar", dados)

    assert resposta.status_code == 302
    pagina = html(client.get("/livros"))
    assert "Dom Casmurro (edição nova)" in pagina
    assert "5 de 5" in pagina


def test_formulario_de_edicao_vem_preenchido(client, criar_livro):
    id_livro = criar_livro("Dom Casmurro", "Machado de Assis", quantidade=4)

    pagina = html(client.get(f"/livros/{id_livro}/editar"))

    assert 'value="Dom Casmurro"' in pagina
    assert 'value="4"' in pagina


def test_editar_mantem_o_proprio_isbn(post, criar_livro):
    id_livro = criar_livro("Dom Casmurro", isbn="9788535902775")

    resposta = post(f"/livros/{id_livro}/editar", {**LIVRO_VALIDO, "isbn": "9788535902775"})

    assert resposta.status_code == 302


def test_nao_reduz_quantidade_abaixo_dos_emprestados(post, criar_livro, registrar_emprestimo):
    id_livro = criar_livro("Dom Casmurro", quantidade=3)
    registrar_emprestimo(id_livro)
    registrar_emprestimo(id_livro)

    resposta = post(f"/livros/{id_livro}/editar", {**LIVRO_VALIDO, "quantidade": "1"})

    assert resposta.status_code == 400
    assert "Há 2 exemplares emprestados no momento" in html(resposta)


def test_editar_livro_inexistente(client):
    assert client.get("/livros/999/editar").status_code == 404


def test_excluir_livro_sem_emprestimos(client, post, criar_livro):
    id_livro = criar_livro("Dom Casmurro")

    assert "Sim, excluir" in html(client.get(f"/livros/{id_livro}/excluir"))
    resposta = post(f"/livros/{id_livro}/excluir")

    assert resposta.status_code == 302
    assert "Nenhum livro cadastrado ainda." in html(client.get("/livros"))


def test_nao_exclui_livro_com_historico_de_emprestimos(client, post, criar_livro, registrar_emprestimo):
    id_livro = criar_livro("Dom Casmurro")
    registrar_emprestimo(id_livro, status="devolvido")

    confirmacao = html(client.get(f"/livros/{id_livro}/excluir"))
    resposta = post(f"/livros/{id_livro}/excluir")

    assert "Sim, excluir" not in confirmacao
    assert resposta.status_code == 302
    pagina = html(client.get("/livros"))
    assert "não pode ser excluído" in pagina
    assert "Dom Casmurro" in pagina


def test_buscar_isbn_preenche_titulo_autor_e_ano(client, post, monkeypatch):
    monkeypatch.setattr(
        isbn_lookup,
        "buscar_por_isbn",
        lambda isbn: {"titulo": "Dom Casmurro", "autor": "Machado de Assis", "ano_publicacao": 1899},
    )

    resposta = post("/livros/novo", {**LIVRO_VALIDO, "titulo": "", "autor": "", "isbn": "9788535902775", "acao": "buscar_isbn"})
    pagina = html(resposta)

    assert resposta.status_code == 200
    assert "Dados encontrados" in pagina
    assert 'value="Dom Casmurro"' in pagina
    assert 'value="Machado de Assis"' in pagina
    assert 'value="1899"' in pagina


def test_buscar_isbn_nao_grava_nada_no_banco(client, post, consulta, monkeypatch):
    monkeypatch.setattr(
        isbn_lookup,
        "buscar_por_isbn",
        lambda isbn: {"titulo": "Dom Casmurro", "autor": "Machado de Assis", "ano_publicacao": 1899},
    )

    post("/livros/novo", {**LIVRO_VALIDO, "isbn": "9788535902775", "acao": "buscar_isbn"})

    assert consulta("SELECT id_livro FROM livro") == []


def test_buscar_isbn_sem_isbn_digitado_mostra_aviso(post):
    resposta = post("/livros/novo", {**LIVRO_VALIDO, "isbn": "", "acao": "buscar_isbn"})

    assert "Informe um ISBN para buscar." in html(resposta)


def test_buscar_isbn_nao_encontrado_mostra_aviso_e_mantem_valores(post, monkeypatch):
    monkeypatch.setattr(isbn_lookup, "buscar_por_isbn", lambda isbn: None)

    resposta = post("/livros/novo", {**LIVRO_VALIDO, "titulo": "Meu título digitado", "isbn": "9788535902775", "acao": "buscar_isbn"})
    pagina = html(resposta)

    assert "Não foi possível encontrar dados para esse ISBN" in pagina
    assert 'value="Meu título digitado"' in pagina


def test_buscar_isbn_tambem_funciona_ao_editar(post, criar_livro, monkeypatch):
    id_livro = criar_livro("Título provisório", "Autor provisório")
    monkeypatch.setattr(
        isbn_lookup,
        "buscar_por_isbn",
        lambda isbn: {"titulo": "Dom Casmurro", "autor": "Machado de Assis", "ano_publicacao": 1899},
    )

    resposta = post(f"/livros/{id_livro}/editar", {**LIVRO_VALIDO, "isbn": "9788535902775", "acao": "buscar_isbn"})
    pagina = html(resposta)

    assert resposta.status_code == 200
    assert 'value="Dom Casmurro"' in pagina


def test_post_sem_token_csrf_e_recusado(post, consulta):
    resposta = post("/livros/novo", LIVRO_VALIDO, com_token=False)

    assert resposta.status_code == 400
    assert consulta("SELECT id_livro FROM livro") == []


def test_painel_soma_os_exemplares(client, criar_livro):
    criar_livro("Dom Casmurro", quantidade=3)
    criar_livro("1984", quantidade=5)

    pagina = html(client.get("/"))

    assert '<span class="stat-card__value">8</span>' in pagina


def test_menu_destaca_a_secao_atual(client):
    pagina = html(client.get("/livros"))

    assert 'class="sidebar__link is-active" aria-current="page">Livros' in pagina
    assert 'class="sidebar__link">Início' in pagina


def test_cadastro_vindo_do_emprestimo_mostra_aviso_e_cancelar_volta(client):
    pagina = html(client.get("/livros/novo", query_string={"voltar": "emprestimo"}))

    assert "para poder emprestá-lo em seguida" in pagina
    assert 'name="voltar" value="emprestimo"' in pagina
    assert 'href="/emprestimos/novo"' in pagina


def test_cadastro_normal_nao_mostra_aviso_de_emprestimo(client):
    pagina = html(client.get("/livros/novo"))

    assert "para poder emprestá-lo em seguida" not in pagina
    assert 'href="/livros"' in pagina


def test_cadastro_vindo_do_emprestimo_redireciona_com_livro_selecionado(client, post, consulta):
    resposta = post("/livros/novo", {**LIVRO_VALIDO, "voltar": "emprestimo"})

    assert resposta.status_code == 302
    assert resposta.headers["Location"].startswith("/emprestimos/novo?id_livro=")

    id_livro = consulta("SELECT id_livro FROM livro")[0]["id_livro"]
    pagina = html(client.get(resposta.headers["Location"]))
    assert f'value="{id_livro}" checked' in pagina


def test_pagina_tem_link_para_pular_ao_conteudo(client):
    pagina = html(client.get("/livros"))

    assert 'class="skip-link" href="#conteudo"' in pagina
    assert 'id="conteudo"' in pagina
