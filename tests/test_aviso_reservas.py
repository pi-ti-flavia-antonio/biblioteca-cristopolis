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


def test_contador_aparece_na_aba_e_no_menu_enquanto_a_reserva_nao_foi_vista(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)

    for rota in ["/emprestimos/novo", "/emprestimos", "/livros"]:
        pagina = html(client.get(rota))
        assert 'aria-label="1 livro disponível para retirada"' in pagina, rota
    assert html(client.get("/emprestimos")).count('class="contagem"') == 2


def test_abrir_a_aba_reservas_tira_o_ponto_vermelho_mas_mantem_o_aviso(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)

    pagina = html(client.get("/emprestimos/reservas"))

    assert 'class="contagem"' not in pagina
    assert "1 livro disponível para retirada" in _aviso(pagina)
    assert "Maria Oliveira" in _aviso(pagina)


def test_ponto_vermelho_continua_apagado_nas_outras_telas_depois_de_visto(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)
    client.get("/emprestimos/reservas")

    for rota in ["/emprestimos/novo", "/emprestimos", "/livros", "/devolucoes"]:
        assert 'class="contagem"' not in html(client.get(rota)), rota
    assert "aviso-reservas-titulo" in html(client.get("/emprestimos/reservas"))


def test_aviso_amarelo_continua_em_visitas_seguintes(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)

    for _ in range(3):
        assert "Avisar por WhatsApp" in html(client.get("/emprestimos/reservas"))


def test_outro_livro_reservado_que_volta_acende_o_ponto_de_novo(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)
    client.get("/emprestimos/reservas")  # viu o primeiro aviso

    id_livro2 = criar_livro("Dom Quixote", quantidade=1)
    registrar_emprestimo(id_livro2)
    post("/emprestimos/reservas", {"id_usuario": criar_usuario("Carlos Souza", cpf="52998224725"), "id_livro": id_livro2})
    id_emprestimo2 = consulta("SELECT id_emprestimo FROM emprestimo WHERE id_livro = ?", (id_livro2,))[0]["id_emprestimo"]
    post(f"/devolucoes/{id_emprestimo2}/registrar")

    assert 'aria-label="1 livro disponível para retirada"' in html(client.get("/emprestimos"))
    pagina = html(client.get("/emprestimos/reservas"))
    assert "2 livros disponíveis para retirada" in _aviso(pagina)
    assert 'class="contagem"' not in pagina


def test_o_mesmo_livro_que_volta_de_novo_acende_o_ponto_outra_vez(client, post, criar_usuario, criar_livro, registrar_emprestimo, consulta):
    id_usuario, id_livro = _devolver_com_reserva(post, criar_usuario, criar_livro, registrar_emprestimo, consulta)
    client.get("/emprestimos/reservas")  # viu o aviso

    registrar_emprestimo(id_livro)  # alguem pegou o exemplar antes da retirada
    id_emprestimo = consulta("SELECT id_emprestimo FROM emprestimo WHERE status = 'ativo'")[0]["id_emprestimo"]
    post(f"/devolucoes/{id_emprestimo}/registrar")

    assert 'class="contagem"' in html(client.get("/emprestimos"))


def test_banco_antigo_sem_a_coluna_e_atualizado_sem_perder_reservas(tmp_path):
    import sqlite3

    from app import create_app

    caminho = tmp_path / "antigo.db"
    app = create_app({"TESTING": True, "DATABASE": caminho, "SECRET_KEY": "x"})
    with app.app_context():
        from app.database import get_db
        db = get_db()
        with db:
            db.execute("INSERT INTO usuario (nome) VALUES ('Maria')")
            db.execute("INSERT INTO livro (titulo, autor, quantidade_total) VALUES ('Dom Casmurro', 'Machado', 1)")
            db.execute("INSERT INTO reserva (data_reserva, status, id_usuario, id_livro) VALUES ('2026-10-01', 'ativa', 1, 1)")
            db.execute("ALTER TABLE reserva DROP COLUMN aviso_visto")

    app2 = create_app({"TESTING": True, "DATABASE": caminho, "SECRET_KEY": "x"})
    with app2.app_context():
        from app.database import get_db
        colunas = {c["name"] for c in get_db().execute("PRAGMA table_info(reserva)")}
        reservas = get_db().execute("SELECT id_reserva, aviso_visto FROM reserva").fetchall()

    assert "aviso_visto" in colunas
    assert [(r["id_reserva"], r["aviso_visto"]) for r in reservas] == [(1, 0)]


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
