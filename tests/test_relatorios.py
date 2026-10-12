from datetime import date, timedelta

from app.database import get_db


def html(resposta):
    return resposta.get_data(as_text=True)


def _ultimos_30_dias():
    hoje = date.today()
    return {"inicio": (hoje - timedelta(days=29)).isoformat(), "fim": hoje.isoformat()}


def _inserir_emprestimo(app, id_usuario, id_livro, data_emprestimo, data_devolucao_prevista, status="ativo"):
    with app.app_context():
        db = get_db()
        with db:
            db.execute(
                "INSERT INTO emprestimo (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro) "
                "VALUES (?, ?, ?, ?, ?)",
                (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro),
            )


def test_tela_abre_sem_relatorio_gerado_e_sem_datas_preenchidas(client):
    pagina = html(client.get("/relatorios"))

    assert "Escolha o período" in pagina
    assert "Relatório pronto" not in pagina
    assert "<table" not in pagina
    assert 'name="inicio" value=""' in pagina
    assert 'name="fim" value=""' in pagina


def test_periodo_mostra_apenas_emprestimos_do_intervalo(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro_recente = criar_livro("Dom Casmurro", quantidade=1)
    id_livro_antigo = criar_livro("1984", quantidade=1)

    hoje = date.today()
    _inserir_emprestimo(app, id_usuario, id_livro_recente, hoje.isoformat(), (hoje + timedelta(days=14)).isoformat())
    _inserir_emprestimo(
        app, id_usuario, id_livro_antigo,
        (hoje - timedelta(days=60)).isoformat(), (hoje - timedelta(days=46)).isoformat(), status="devolvido",
    )

    pagina = html(client.get("/relatorios", query_string=_ultimos_30_dias()))

    assert "Dom Casmurro" in pagina
    assert "1984" not in pagina
    assert "1 empréstimo registrado" in pagina


def test_periodo_customizado_inclui_emprestimo_antigo(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("1984", quantidade=1)
    inicio = date.today() - timedelta(days=60)
    _inserir_emprestimo(app, id_usuario, id_livro, inicio.isoformat(), (inicio + timedelta(days=14)).isoformat(), status="devolvido")

    pagina = html(client.get("/relatorios", query_string={"inicio": inicio.isoformat(), "fim": date.today().isoformat()}))

    assert "1984" in pagina
    assert "1 empréstimo registrado" in pagina


def test_periodo_com_data_inicial_depois_da_final_mostra_erro(client):
    hoje = date.today().isoformat()
    ontem = (date.today() - timedelta(days=1)).isoformat()

    pagina = html(client.get("/relatorios", query_string={"inicio": hoje, "fim": ontem}))

    assert "A data inicial não pode ser depois da data final." in pagina
    assert "Corrija o período acima" in pagina


def test_periodo_maior_que_um_ano_mostra_erro(client):
    fim = date.today().isoformat()
    inicio = (date.today() - timedelta(days=400)).isoformat()

    pagina = html(client.get("/relatorios", query_string={"inicio": inicio, "fim": fim}))

    assert "O período não pode ser maior que 1 ano." in pagina


def test_periodo_mostra_status_de_cada_emprestimo(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    hoje = date.today()

    id_livro_ativo = criar_livro("Dom Casmurro", quantidade=1)
    _inserir_emprestimo(app, id_usuario, id_livro_ativo, hoje.isoformat(), (hoje + timedelta(days=14)).isoformat())

    pagina = html(client.get("/relatorios", query_string=_ultimos_30_dias()))

    assert ">Ativo<" in pagina


def test_nao_ha_mais_botao_nem_relatorio_automatico_dos_ultimos_30_dias(client):
    pagina = html(client.get("/relatorios"))

    assert "Últimos 30 dias" not in pagina


def test_gerar_relatorio_mostra_aviso_de_pronto_com_botao_para_baixar(client):
    parametros = _ultimos_30_dias()

    pagina = html(client.get("/relatorios", query_string=parametros))

    assert "Relatório pronto." in pagina
    assert f'href="/relatorios/periodo.pdf?inicio={parametros["inicio"]}&amp;fim={parametros["fim"]}"' in pagina
    assert ">Baixar PDF<" in pagina


def test_sem_gerar_nao_aparece_botao_de_baixar(client):
    pagina = html(client.get("/relatorios"))

    assert "Baixar PDF" not in pagina


def test_pagina_traz_aviso_de_gerando_escondido_ate_clicar(client):
    pagina = html(client.get("/relatorios"))

    assert 'id="aviso-gerando"' in pagina
    assert "Gerando relatório, aguarde..." in pagina
    assert "hidden>" in pagina


def test_gerar_com_datas_vazias_pede_as_datas(client):
    pagina = html(client.get("/relatorios", query_string={"inicio": "", "fim": ""}))

    assert "Informe a data inicial." in pagina
    assert "Informe a data final." in pagina
    assert "Relatório pronto" not in pagina


def test_gerar_com_so_uma_data_pede_a_outra(client):
    pagina = html(client.get("/relatorios", query_string={"inicio": date.today().isoformat(), "fim": ""}))

    assert "Informe a data final." in pagina
    assert "Informe a data inicial." not in pagina


def test_baixar_pdf_retorna_arquivo_pdf(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    hoje = date.today()
    _inserir_emprestimo(app, id_usuario, id_livro, hoje.isoformat(), (hoje + timedelta(days=30)).isoformat())

    resposta = client.get("/relatorios/periodo.pdf", query_string=_ultimos_30_dias())

    assert resposta.status_code == 200
    assert resposta.mimetype == "application/pdf"
    assert resposta.data[:4] == b"%PDF"


def test_baixar_pdf_com_periodo_invalido_volta_para_o_relatorio(client):
    resposta = client.get("/relatorios/periodo.pdf", query_string={"inicio": "2026-01-01", "fim": "2020-01-01"})

    assert resposta.status_code == 302
    assert resposta.headers["Location"].startswith("/relatorios")


def test_atraso_lista_vazia_mostra_mensagem(client):
    pagina = html(client.get("/relatorios/atraso"))

    assert "Nenhum empréstimo em atraso no momento." in pagina
    assert "<strong>0</strong>" in pagina


def test_atraso_lista_apenas_emprestimos_atrasados(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909", telefone="67999990000")
    hoje = date.today()

    id_livro_atrasado = criar_livro("1984", quantidade=1)
    _inserir_emprestimo(app, id_usuario, id_livro_atrasado, (hoje - timedelta(days=20)).isoformat(), (hoje - timedelta(days=6)).isoformat())

    id_livro_ativo = criar_livro("Dom Casmurro", quantidade=1)
    _inserir_emprestimo(app, id_usuario, id_livro_ativo, hoje.isoformat(), (hoje + timedelta(days=14)).isoformat())

    id_livro_devolvido = criar_livro("O Hobbit", quantidade=1)
    _inserir_emprestimo(
        app, id_usuario, id_livro_devolvido,
        (hoje - timedelta(days=30)).isoformat(), (hoje - timedelta(days=16)).isoformat(), status="devolvido",
    )

    pagina = html(client.get("/relatorios/atraso"))

    assert "1984" in pagina
    assert "Dom Casmurro" not in pagina
    assert "O Hobbit" not in pagina
    assert "(67) 99999-0000" in pagina
    assert "6 dias" in pagina


def test_atraso_singular_para_um_dia(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    hoje = date.today()
    id_livro = criar_livro("1984", quantidade=1)
    _inserir_emprestimo(app, id_usuario, id_livro, (hoje - timedelta(days=15)).isoformat(), (hoje - timedelta(days=1)).isoformat())

    pagina = html(client.get("/relatorios/atraso"))

    assert "1 dia<" in pagina


def test_menu_destaca_a_secao_atual(client):
    pagina = html(client.get("/relatorios"))

    assert 'class="sidebar__link is-active" aria-current="page">Relatórios' in pagina
    assert 'class="sidebar__link">Devoluções' in pagina


def test_abas_alternam_entre_periodo_e_atraso(client):
    periodo = html(client.get("/relatorios"))
    atraso = html(client.get("/relatorios/atraso"))

    assert 'aria-current="page">Empréstimos por período' in periodo
    assert 'aria-current="page">Empréstimos em atraso' in atraso


def test_baixar_pdf_sem_periodo_volta_para_o_relatorio(client):
    resposta = client.get("/relatorios/periodo.pdf")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].startswith("/relatorios")
