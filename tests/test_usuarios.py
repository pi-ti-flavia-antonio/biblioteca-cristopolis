USUARIO_VALIDO = {
    "nome": "Maria Oliveira",
    "cpf": "123.456.789-09",
    "telefone": "(67) 99999-0000",
    "tipo_usuario": "aluno",
    "email": "maria@example.com",
    "endereco": "Rua das Flores, 10",
}


def html(resposta):
    return resposta.get_data(as_text=True)


def test_lista_vazia_mostra_mensagem(client):
    resposta = client.get("/usuarios")

    assert resposta.status_code == 200
    assert "Nenhum usuário cadastrado ainda." in html(resposta)


def test_cadastrar_usuario_valido(client, post):
    resposta = post("/usuarios/novo", USUARIO_VALIDO)
    assert resposta.status_code == 302

    pagina = html(client.get("/usuarios"))
    assert "Maria Oliveira" in pagina
    assert "***.***.***-09" in pagina
    assert "123.456.789-09" not in pagina
    assert "(67) 99999-0000" in pagina
    assert "aluno" in pagina


def test_cadastrar_mostra_mensagem_de_sucesso(client, post):
    post("/usuarios/novo", USUARIO_VALIDO)

    assert "Usuário cadastrado: Maria Oliveira." in html(client.get("/usuarios/novo"))


def test_cadastrar_sem_campos_obrigatorios_nao_grava(client, post):
    resposta = post("/usuarios/novo", {"nome": "", "cpf": "", "telefone": ""})
    pagina = html(resposta)

    assert resposta.status_code == 400
    assert "Informe o nome." in pagina
    assert "Informe o CPF." in pagina
    assert "Informe o telefone." in pagina
    assert "Nenhum usuário cadastrado ainda." in html(client.get("/usuarios"))


def test_campos_opcionais_podem_ficar_vazios(post, consulta):
    resposta = post("/usuarios/novo", {**USUARIO_VALIDO, "tipo_usuario": "", "email": "", "endereco": ""})

    assert resposta.status_code == 302
    usuario = consulta("SELECT tipo_usuario, email, endereco FROM usuario")[0]
    assert usuario["tipo_usuario"] is None
    assert usuario["email"] is None
    assert usuario["endereco"] is None


def test_cpf_invalido(post):
    for valor in ["123", "abcdefghijk", "111.111.111-11", "123.456.789-00"]:
        resposta = post("/usuarios/novo", {**USUARIO_VALIDO, "cpf": valor})
        assert resposta.status_code == 400, valor
        assert "Informe um CPF válido" in html(resposta)


def test_cpf_aceita_pontuacao_e_grava_so_digitos(post, consulta):
    post("/usuarios/novo", {**USUARIO_VALIDO, "cpf": "123.456.789-09"})

    assert consulta("SELECT cpf FROM usuario")[0]["cpf"] == "12345678909"


def test_cpf_duplicado_e_recusado(post, consulta):
    post("/usuarios/novo", USUARIO_VALIDO)
    resposta = post("/usuarios/novo", {**USUARIO_VALIDO, "nome": "Outra Pessoa"})

    assert resposta.status_code == 400
    assert "Já existe um usuário cadastrado com este CPF." in html(resposta)
    assert "com este CPF:" not in html(resposta)
    assert len(consulta("SELECT id_usuario FROM usuario")) == 1


def test_telefone_invalido(post):
    for valor in ["123", "abcdefghij", "9999999999999"]:
        resposta = post("/usuarios/novo", {**USUARIO_VALIDO, "telefone": valor})
        assert resposta.status_code == 400, valor
        assert "Informe um telefone válido" in html(resposta)


def test_tipo_usuario_invalido(post):
    resposta = post("/usuarios/novo", {**USUARIO_VALIDO, "tipo_usuario": "gerente"})

    assert resposta.status_code == 400
    assert "Selecione um tipo de usuário válido." in html(resposta)


def test_email_invalido(post):
    resposta = post("/usuarios/novo", {**USUARIO_VALIDO, "email": "sem-arroba"})

    assert resposta.status_code == 400
    assert "Informe um e-mail válido." in html(resposta)


def test_busca_por_nome_sem_acento_e_sem_caixa(client, criar_usuario):
    criar_usuario("José António", cpf="12345678909")
    criar_usuario("Carlos Souza", cpf="52998224725")

    for termo in ["jose", "ANTÓNIO", "jose anton"]:
        pagina = html(client.get("/usuarios", query_string={"q": termo}))
        assert "José António" in pagina, termo
        assert "Carlos Souza" not in pagina, termo


def test_busca_por_cpf_com_ou_sem_pontuacao(client, criar_usuario):
    criar_usuario("Maria Oliveira", cpf="12345678909")
    criar_usuario("Carlos Souza", cpf="52998224725")

    for termo in ["123.456.789-09", "12345678909", "789"]:
        pagina = html(client.get("/usuarios", query_string={"q": termo}))
        assert "Maria Oliveira" in pagina, termo
        assert "Carlos Souza" not in pagina, termo


def test_busca_sem_resultado(client, criar_usuario):
    criar_usuario("Maria Oliveira")

    pagina = html(client.get("/usuarios", query_string={"q": "xyz"}))

    assert 'Nenhum usuário encontrado para "xyz".' in pagina


def test_paginacao(client, criar_usuario):
    for numero in range(1, 31):
        criar_usuario(f"Usuário {numero:02d}", cpf=str(10000000000 + numero))

    primeira = html(client.get("/usuarios"))
    segunda = html(client.get("/usuarios", query_string={"pagina": 2}))

    assert "Usuário 25" in primeira and "Usuário 26" not in primeira
    assert "Mostrando 1 a 25 de 30" in primeira
    assert "Usuário 26" in segunda and "Usuário 30" in segunda and "Usuário 25" not in segunda


def test_editar_usuario(client, post, criar_usuario):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    dados = {**USUARIO_VALIDO, "nome": "Maria Oliveira Santos", "cpf": "123.456.789-09"}

    resposta = post(f"/usuarios/{id_usuario}/editar", dados)

    assert resposta.status_code == 302
    assert "Maria Oliveira Santos" in html(client.get("/usuarios"))


def test_formulario_de_edicao_vem_preenchido(client, criar_usuario):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909", tipo_usuario="professor")

    pagina = html(client.get(f"/usuarios/{id_usuario}/editar"))

    assert 'value="Maria Oliveira"' in pagina
    assert 'value="12345678909"' in pagina
    assert "selected>Professor" in pagina


def test_editar_mantem_o_proprio_cpf(post, criar_usuario):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")

    resposta = post(f"/usuarios/{id_usuario}/editar", {**USUARIO_VALIDO, "cpf": "123.456.789-09"})

    assert resposta.status_code == 302


def test_editar_usuario_inexistente(client):
    assert client.get("/usuarios/999/editar").status_code == 404


def test_excluir_usuario_sem_emprestimos(client, post, criar_usuario):
    id_usuario = criar_usuario("Maria Oliveira")

    assert "Sim, excluir" in html(client.get(f"/usuarios/{id_usuario}/excluir"))
    resposta = post(f"/usuarios/{id_usuario}/excluir")

    assert resposta.status_code == 302
    assert "Nenhum usuário cadastrado ainda." in html(client.get("/usuarios"))


def test_nao_exclui_usuario_com_historico_de_emprestimos(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_usuario = criar_usuario("Maria Oliveira")
    id_livro = criar_livro()
    registrar_emprestimo(id_livro, status="devolvido", id_usuario=id_usuario)

    confirmacao = html(client.get(f"/usuarios/{id_usuario}/excluir"))
    resposta = post(f"/usuarios/{id_usuario}/excluir")

    assert "Sim, excluir" not in confirmacao
    assert resposta.status_code == 302
    pagina = html(client.get("/usuarios"))
    assert "não pode ser excluído" in pagina
    assert "Maria Oliveira" in pagina


def test_post_sem_token_csrf_e_recusado(post, consulta):
    resposta = post("/usuarios/novo", USUARIO_VALIDO, com_token=False)

    assert resposta.status_code == 400
    assert consulta("SELECT id_usuario FROM usuario") == []


def test_painel_soma_usuarios_cadastrados(client, criar_usuario):
    criar_usuario("Maria Oliveira", cpf="12345678909")
    criar_usuario("Carlos Souza", cpf="52998224725")

    pagina = html(client.get("/"))

    assert '<span class="stat-card__value">2</span>' in pagina


def test_menu_destaca_a_secao_atual(client):
    pagina = html(client.get("/usuarios"))

    assert 'class="sidebar__link is-active" aria-current="page">Usuários' in pagina
    assert 'class="sidebar__link">Livros' in pagina


def test_cadastro_vindo_do_emprestimo_mostra_aviso_e_cancelar_volta(client):
    pagina = html(client.get("/usuarios/novo", query_string={"voltar": "emprestimo"}))

    assert "para poder registrar o empréstimo em seguida" in pagina
    assert 'name="voltar" value="emprestimo"' in pagina
    assert 'href="/emprestimos/novo"' in pagina


def test_cadastro_normal_nao_mostra_aviso_de_emprestimo(client):
    pagina = html(client.get("/usuarios/novo"))

    assert "para poder registrar o empréstimo em seguida" not in pagina
    assert 'href="/usuarios"' in pagina


def test_cadastro_vindo_do_emprestimo_redireciona_com_usuario_selecionado(client, post, consulta):
    resposta = post("/usuarios/novo", {**USUARIO_VALIDO, "voltar": "emprestimo"})

    assert resposta.status_code == 302
    assert resposta.headers["Location"].startswith("/emprestimos/novo?id_usuario=")

    id_usuario = consulta("SELECT id_usuario FROM usuario")[0]["id_usuario"]
    pagina = html(client.get(resposta.headers["Location"]))
    assert f'name="id_usuario" value="{id_usuario}"' in pagina
    assert "Maria Oliveira" in pagina
