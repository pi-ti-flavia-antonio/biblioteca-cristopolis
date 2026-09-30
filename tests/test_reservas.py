def html(resposta):
    return resposta.get_data(as_text=True)


def test_lista_vazia_mostra_mensagem(client):
    resposta = client.get("/emprestimos/reservas")

    assert resposta.status_code == 200
    assert "Nenhuma reserva ativa no momento." in html(resposta)


def test_so_livros_esgotados_aparecem_no_formulario(client, criar_livro):
    criar_livro("Dom Casmurro", quantidade=1)  # com exemplar disponível
    criar_livro("1984", quantidade=1)

    pagina = html(client.get("/emprestimos/reservas"))

    assert "Dom Casmurro" not in pagina
    assert "Nenhum livro esgotado no momento." in pagina


def test_registrar_reserva_valida(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)  # esgota o único exemplar
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")

    resposta = post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})

    assert resposta.status_code == 302
    pagina = html(client.get("/emprestimos/reservas"))
    assert "Dom Casmurro" in pagina
    assert "Maria Oliveira" in pagina
    assert "Aguardando" in pagina


def test_bloqueia_reserva_de_livro_com_exemplar_disponivel(client, post, criar_usuario, criar_livro):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")

    resposta = post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})

    assert resposta.status_code == 400
    assert "já tem exemplar disponível" in html(resposta)


def test_bloqueia_reserva_duplicada(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})

    resposta = post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})

    assert resposta.status_code == 400
    assert "já tem uma reserva ativa para este livro" in html(resposta)


def test_sem_selecao_mostra_erros(client, post):
    resposta = post("/emprestimos/reservas", {"id_usuario": "", "id_livro": ""})

    assert resposta.status_code == 400
    assert "Selecione o usuário." in html(resposta)
    assert "Selecione o livro." in html(resposta)


def test_fila_marca_so_a_reserva_mais_antiga_como_disponivel(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)

    id_usuario_a = criar_usuario("Maria Oliveira", cpf="12345678909")
    post("/emprestimos/reservas", {"id_usuario": id_usuario_a, "id_livro": id_livro})
    id_usuario_b = criar_usuario("Carlos Souza", cpf="52998224725")
    post("/emprestimos/reservas", {"id_usuario": id_usuario_b, "id_livro": id_livro})

    # devolve o exemplar: agora ha 1 vaga para 2 reservas ativas
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]
    post(f"/devolucoes/{id_emprestimo}/registrar")

    pagina = html(client.get("/emprestimos/reservas"))
    assert "Maria Oliveira" in pagina
    assert "Carlos Souza" in pagina
    # a mais antiga (Maria) tem o botao de retirada; a mais nova (Carlos), nao
    id_reserva_maria = consulta(
        "SELECT id_reserva FROM reserva WHERE id_usuario = ?", (id_usuario_a,)
    )[0]["id_reserva"]
    id_reserva_carlos = consulta(
        "SELECT id_reserva FROM reserva WHERE id_usuario = ?", (id_usuario_b,)
    )[0]["id_reserva"]
    assert f"/emprestimos/reservas/{id_reserva_maria}/retirar" in pagina
    assert f"/emprestimos/reservas/{id_reserva_carlos}/retirar" not in pagina


def test_registrar_retirada_converte_em_emprestimo(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})

    id_emprestimo_antigo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]
    post(f"/devolucoes/{id_emprestimo_antigo}/registrar")

    id_reserva = consulta("SELECT id_reserva FROM reserva")[0]["id_reserva"]
    resposta = post(f"/emprestimos/reservas/{id_reserva}/retirar")

    assert resposta.status_code == 302
    assert "Nenhuma reserva ativa no momento." in html(client.get("/emprestimos/reservas"))
    assert consulta("SELECT status FROM reserva")[0]["status"] == "concluida"

    emprestimos_ativos = consulta("SELECT COUNT(*) AS n FROM emprestimo WHERE status = 'ativo'")[0]["n"]
    assert emprestimos_ativos == 1


def test_registrar_retirada_bloqueia_se_usuario_tem_pendencia(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})

    id_emprestimo_antigo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]
    post(f"/devolucoes/{id_emprestimo_antigo}/registrar")

    outro_livro = criar_livro("1984", quantidade=1)
    registrar_emprestimo(outro_livro, id_usuario=id_usuario)  # usuario pega pendencia com outro livro

    id_reserva = consulta("SELECT id_reserva FROM reserva")[0]["id_reserva"]
    post(f"/emprestimos/reservas/{id_reserva}/retirar")

    assert "já está com um livro emprestado" in html(client.get("/emprestimos/reservas"))
    assert consulta("SELECT status FROM reserva")[0]["status"] == "ativa"


def test_cancelar_reserva(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})
    id_reserva = consulta("SELECT id_reserva FROM reserva")[0]["id_reserva"]

    resposta = post(f"/emprestimos/reservas/{id_reserva}/cancelar")

    assert resposta.status_code == 302
    assert "Nenhuma reserva ativa no momento." in html(client.get("/emprestimos/reservas"))
    assert consulta("SELECT status FROM reserva")[0]["status"] == "cancelada"


def test_cancelar_reserva_inexistente_da_404(post):
    resposta = post("/emprestimos/reservas/999/cancelar")

    assert resposta.status_code == 404


def test_retirar_reserva_inexistente_da_404(post):
    resposta = post("/emprestimos/reservas/999/retirar")

    assert resposta.status_code == 404


def test_post_sem_token_csrf_e_recusado(post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")

    resposta = post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro}, com_token=False)

    assert resposta.status_code == 400
    assert consulta("SELECT id_reserva FROM reserva") == []


def test_aba_reservas_fica_destacada(client):
    pagina = html(client.get("/emprestimos/reservas"))

    assert 'aria-current="page">Reservas' in pagina
