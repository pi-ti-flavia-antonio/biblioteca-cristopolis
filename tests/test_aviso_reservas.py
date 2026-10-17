def html(resposta):
    return resposta.get_data(as_text=True)


def _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta, telefone="67999990000"):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909", telefone=telefone)
    post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]
    post(f"/devolucoes/{id_emprestimo}/registrar")
    return id_usuario, id_livro


def _aviso(pagina):
    inicio = pagina.index('aria-labelledby="aviso-reservas-titulo"')
    return pagina[inicio:pagina.index("</section>", inicio)]


def test_aviso_aparece_no_topo_quando_o_livro_reservado_volta(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)

    aviso = _aviso(html(client.get("/emprestimos/reservas")))

    assert "1 livro disponível para retirada" in aviso
    assert "Maria Oliveira" in aviso and "Dom Casmurro" in aviso
    assert "(67) 99999-0000" in aviso
    assert "Avisar por WhatsApp" in aviso


def test_link_do_whatsapp_leva_o_numero_e_a_mensagem(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)

    aviso = _aviso(html(client.get("/emprestimos/reservas")))

    assert 'href="https://wa.me/5567999990000?text=' in aviso
    assert "Ol%C3%A1%2C%20Maria%21" in aviso
    assert "Dom%20Casmurro" in aviso
    assert 'target="_blank"' in aviso and "noopener" in aviso


def test_sem_reserva_pronta_nao_ha_aviso_nem_contador(client, post, criar_usuario, criar_livro, registrar_emprestimo):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})

    pagina = html(client.get("/emprestimos/reservas"))

    assert "aviso-reservas-titulo" not in pagina
    assert "Avisar por WhatsApp" not in pagina
    assert 'class="contagem"' not in pagina


def test_aviso_lista_so_a_pessoa_mais_antiga_da_fila(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    post("/emprestimos/reservas", {"id_usuario": criar_usuario("Maria Oliveira", cpf="12345678909"), "id_livro": id_livro})
    post("/emprestimos/reservas", {"id_usuario": criar_usuario("Carlos Souza", cpf="52998224725"), "id_livro": id_livro})
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]
    post(f"/devolucoes/{id_emprestimo}/registrar")

    aviso = _aviso(html(client.get("/emprestimos/reservas")))

    assert "Maria Oliveira" in aviso
    assert "Carlos Souza" not in aviso


def test_contador_aparece_na_aba_e_no_menu_em_todas_as_paginas_de_emprestimos(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)

    for rota in ["/emprestimos/novo", "/emprestimos", "/emprestimos/reservas"]:
        pagina = html(client.get(rota))
        assert pagina.count('class="contagem"') == 2, rota
        assert 'aria-label="1 livro disponível para retirada"' in pagina, rota

    assert 'class="contagem"' in html(client.get("/livros"))


def test_aviso_some_depois_que_a_retirada_e_registrada(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)
    id_reserva = consulta("SELECT id_reserva FROM reserva")[0]["id_reserva"]

    post(f"/emprestimos/reservas/{id_reserva}/retirar")
    pagina = html(client.get("/emprestimos/reservas"))

    assert "aviso-reservas-titulo" not in pagina
    assert 'class="contagem"' not in pagina


def test_aviso_some_se_a_reserva_for_cancelada(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)
    id_reserva = consulta("SELECT id_reserva FROM reserva")[0]["id_reserva"]

    post(f"/emprestimos/reservas/{id_reserva}/cancelar")

    assert "aviso-reservas-titulo" not in html(client.get("/emprestimos/reservas"))


def test_telefone_sem_ddd_mostra_o_aviso_mas_sem_botao_do_whatsapp(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta, telefone="9999")

    aviso = _aviso(html(client.get("/emprestimos/reservas")))

    assert "Maria Oliveira" in aviso
    assert "wa.me" not in aviso


def test_devolver_livro_reservado_avisa_quem_esta_esperando(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909", telefone="67999990000")
    post("/emprestimos/reservas", {"id_usuario": id_usuario, "id_livro": id_livro})
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]

    post(f"/devolucoes/{id_emprestimo}/registrar")
    pagina = html(client.get("/devolucoes"))

    assert "O livro Dom Casmurro tinha reserva e já está disponível." in pagina
    assert "Avise Maria Oliveira pelo WhatsApp: (67) 99999-0000" in pagina
    assert "aba Reservas" in pagina
    assert "alert--info" in pagina


def test_devolver_livro_sem_reserva_nao_mostra_aviso_de_reserva(client, post, criar_livro, registrar_emprestimo, consulta):
    registrar_emprestimo(criar_livro("Dom Casmurro", quantidade=1))
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]

    post(f"/devolucoes/{id_emprestimo}/registrar")
    pagina = html(client.get("/devolucoes"))

    assert "Devolução registrada" in pagina
    assert "tinha reserva" not in pagina


def test_devolver_com_fila_avisa_so_a_pessoa_mais_antiga(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    registrar_emprestimo(id_livro)
    post("/emprestimos/reservas", {"id_usuario": criar_usuario("Maria Oliveira", cpf="12345678909"), "id_livro": id_livro})
    post("/emprestimos/reservas", {"id_usuario": criar_usuario("Carlos Souza", cpf="52998224725"), "id_livro": id_livro})
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo")[0]["id_emprestimo"]

    post(f"/devolucoes/{id_emprestimo}/registrar")
    pagina = html(client.get("/devolucoes"))

    assert "Avise Maria Oliveira" in pagina
    assert "Avise Carlos Souza" not in pagina
