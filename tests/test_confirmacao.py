"""A caixa de confirmação é feita em JavaScript; aqui se confere que cada ação
que grava algo está marcada para pedir confirmação e que a caixa existe na página."""


def html(resposta):
    return resposta.get_data(as_text=True)


def test_toda_pagina_tem_a_caixa_de_confirmacao_com_sim_e_nao(client):
    pagina = html(client.get("/"))

    assert 'id="caixa-confirmacao"' in pagina
    assert ">Sim</button>" in pagina
    assert ">Não</button>" in pagina
    assert "js/confirmar.js" in pagina


def test_cadastrar_livro_pede_confirmacao(client):
    assert 'data-confirmar="Confirmar cadastro do livro?"' in html(client.get("/livros/novo"))


def test_editar_livro_pede_confirmacao(client, criar_livro):
    id_livro = criar_livro()

    pagina = html(client.get(f"/livros/{id_livro}/editar"))

    assert 'data-confirmar="Salvar as alterações do livro?"' in pagina


def test_buscar_dados_do_isbn_nao_pede_confirmacao(client):
    pagina = html(client.get("/livros/novo"))

    assert 'value="buscar_isbn"' in pagina
    assert "data-sem-confirmacao" in pagina


def test_cadastrar_usuario_pede_confirmacao(client):
    assert 'data-confirmar="Confirmar cadastro do usuário?"' in html(client.get("/usuarios/novo"))


def test_editar_usuario_pede_confirmacao(client, criar_usuario):
    id_usuario = criar_usuario()

    pagina = html(client.get(f"/usuarios/{id_usuario}/editar"))

    assert 'data-confirmar="Salvar as alterações do usuário?"' in pagina


def test_emprestimo_pede_confirmacao(client):
    assert 'data-confirmar="Confirmar empréstimo?"' in html(client.get("/emprestimos/novo"))


def test_reserva_pede_confirmacao(client):
    assert 'data-confirmar="Confirmar reserva?"' in html(client.get("/emprestimos/reservas"))


def test_devolucao_pede_confirmacao_e_mostra_livro_e_usuario(
    client, criar_usuario, criar_livro, registrar_emprestimo
):
    id_usuario = criar_usuario("Maria Oliveira")
    registrar_emprestimo(criar_livro("Dom Casmurro"), id_usuario=id_usuario)

    pagina = html(client.get("/devolucoes"))

    assert 'data-confirmar="Confirmar devolução?"' in pagina
    assert 'data-confirmar-detalhe="Dom Casmurro, devolvido por Maria Oliveira."' in pagina


def test_cancelar_reserva_pede_confirmacao_destacada(
    client, post, criar_usuario, criar_livro, registrar_emprestimo
):
    id_usuario = criar_usuario("Maria Oliveira")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})

    pagina = html(client.get("/emprestimos/reservas"))

    assert 'data-confirmar="Cancelar esta reserva?"' in pagina
    assert "data-confirmar-perigo" in pagina
