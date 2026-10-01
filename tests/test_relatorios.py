from datetime import date, timedelta

from app.database import get_db


def html(resposta):
    return resposta.get_data(as_text=True)


def _inserir_emprestimo(app, id_usuario, id_livro, data_emprestimo, data_devolucao_prevista, status="ativo"):
    with app.app_context():
        db = get_db()
        with db:
            db.execute(
                "INSERT INTO emprestimo (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro) "
                "VALUES (?, ?, ?, ?, ?)",
                (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro),
            )


def test_periodo_padrao_e_ultimos_30_dias(client):
    pagina = html(client.get("/relatorios"))

    esperado_fim = date.today().isoformat()
    esperado_inicio = (date.today() - timedelta(days=29)).isoformat()
    assert f'value="{esperado_inicio}"' in pagina
    assert f'value="{esperado_fim}"' in pagina


def test_periodo_padrao_mostra_apenas_emprestimos_recentes(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro_recente = criar_livro("Dom Casmurro", quantidade=1)
    id_livro_antigo = criar_livro("1984", quantidade=1)

    hoje = date.today()
    _inserir_emprestimo(app, id_usuario, id_livro_recente, hoje.isoformat(), (hoje + timedelta(days=14)).isoformat())
    _inserir_emprestimo(
        app, id_usuario, id_livro_antigo,
        (hoje - timedelta(days=60)).isoformat(), (hoje - timedelta(days=46)).isoformat(), status="devolvido",
    )

    pagina = html(client.get("/relatorios"))

    assert "Dom Casmurro" in pagina
    assert "1984" not in pagina
    assert "<strong>1</strong>" in pagina


def test_periodo_customizado_inclui_emprestimo_antigo(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("1984", quantidade=1)
    inicio = date.today() - timedelta(days=60)
    _inserir_emprestimo(app, id_usuario, id_livro, inicio.isoformat(), (inicio + timedelta(days=14)).isoformat(), status="devolvido")

    pagina = html(client.get("/relatorios", query_string={"inicio": inicio.isoformat(), "fim": date.today().isoformat()}))

    assert "1984" in pagina
    assert "<strong>1</strong>" in pagina


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

    pagina = html(client.get("/relatorios"))

    assert ">Ativo<" in pagina


def test_link_ultimos_30_dias_aponta_para_relatorio_sem_parametros(client):
    pagina = html(client.get("/relatorios", query_string={"inicio": "2020-01-01", "fim": "2020-01-02"}))

    assert 'href="/relatorios"' in pagina


def test_botao_ultimos_30_dias_fica_marcado_quando_e_o_periodo_atual(client):
    pagina = html(client.get("/relatorios"))

    assert 'aria-pressed="true"' in pagina


def test_botao_ultimos_30_dias_nao_fica_marcado_com_outro_periodo(client):
    pagina = html(client.get("/relatorios", query_string={"inicio": "2020-01-01", "fim": "2020-01-02"}))

    assert 'aria-pressed="false"' in pagina


def test_baixar_pdf_retorna_arquivo_pdf(app, client, criar_usuario, criar_livro):
    id_usuario = criar_usuario("Maria Oliveira", cpf="12345678909")
    id_livro = criar_livro("Dom Casmurro", quantidade=1)
    hoje = date.today()
    _inserir_emprestimo(app, id_usuario, id_livro, hoje.isoformat(), (hoje + timedelta(days=30)).isoformat())

    resposta = client.get("/relatorios/periodo.pdf")

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
