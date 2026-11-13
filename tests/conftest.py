import smtplib
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.database import get_db
from app.livros import repository
from app.usuarios import repository as usuarios_repository

TOKEN = "token-de-teste"
LOGIN_DE_TESTE = "funcionaria"
SENHA_DE_TESTE = "senha-de-teste"
# O hash é feito uma vez só: gerar um por teste deixaria a suíte lenta.
_HASH_DE_TESTE = generate_password_hash(SENHA_DE_TESTE)


@pytest.fixture(autouse=True)
def sem_envio_de_email_de_verdade(monkeypatch):
    """Nenhum teste pode mandar e-mail de verdade, mesmo que exista um email.json neste computador."""
    def proibido(*args, **kwargs):
        raise RuntimeError("Um teste tentou enviar e-mail de verdade. Troque o envio por um simulado.")

    monkeypatch.setattr(smtplib, "SMTP_SSL", proibido)


@pytest.fixture
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATABASE": tmp_path / "teste.db",
            "SECRET_KEY": "teste",
            # Arquivos de e-mail e de chave dentro da pasta temporária: nunca os do computador.
            "ARQUIVO_EMAIL": tmp_path / "email.json",
            "ARQUIVO_CHAVE": tmp_path / "chave_backup.key",
        }
    )


@pytest.fixture
def id_funcionaria(app):
    """Cria a conta de acesso direto no banco, sem passar pela tela de primeiro acesso."""
    with app.app_context():
        db = get_db()
        with db:
            return db.execute(
                "INSERT INTO funcionario (nome, cargo, login, senha_hash) VALUES (?, ?, ?, ?)",
                ("Funcionária de Teste", "Bibliotecária", LOGIN_DE_TESTE, _HASH_DE_TESTE),
            ).lastrowid


@pytest.fixture
def client(app, id_funcionaria):
    """Cliente já logado, para os testes que não tratam de login."""
    cliente = app.test_client()
    with cliente.session_transaction() as sessao:
        sessao["id_funcionario"] = id_funcionaria
        sessao.permanent = True
    return cliente


@pytest.fixture
def client_anonimo(app):
    return app.test_client()


@pytest.fixture
def post(client):
    def _post(url, dados=None, com_token=True):
        with client.session_transaction() as sessao:
            sessao["csrf_token"] = TOKEN
        corpo = dict(dados or {})
        if com_token:
            corpo["csrf_token"] = TOKEN
        return client.post(url, data=corpo)

    return _post


@pytest.fixture
def criar_livro(app):
    def _criar(titulo="Dom Casmurro", autor="Machado de Assis", quantidade=1, **extra):
        dados = {
            "titulo": titulo,
            "autor": autor,
            "quantidade": quantidade,
            "categoria": "",
            "isbn": None,
            "ano_publicacao": None,
            "edicao": None,
            **extra,
        }
        with app.app_context():
            return repository.criar(dados)

    return _criar


@pytest.fixture
def registrar_emprestimo(app):
    def _registrar(id_livro, status="ativo", id_usuario=None):
        # Datas relativas a hoje, não fixas: um empréstimo "ativo" recém-criado
        # não deve virar "atrasado" sozinho só porque o tempo passou.
        hoje = date.today()
        prevista = hoje + timedelta(days=14)
        with app.app_context():
            db = get_db()
            with db:
                if id_usuario is None:
                    id_usuario = db.execute("INSERT INTO usuario (nome) VALUES ('Leitor')").lastrowid
                db.execute(
                    """
                    INSERT INTO emprestimo (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (hoje.isoformat(), prevista.isoformat(), status, id_usuario, id_livro),
                )
            return id_usuario

    return _registrar


@pytest.fixture
def criar_usuario(app):
    def _criar(nome="Maria Oliveira", cpf="12345678909", telefone="67999990000", **extra):
        dados = {
            "nome": nome,
            "cpf": cpf,
            "telefone": telefone,
            "tipo_usuario": None,
            "email": None,
            "endereco": None,
            "numero_carteirinha": None,
            **extra,
        }
        with app.app_context():
            return usuarios_repository.criar(dados)

    return _criar


@pytest.fixture
def consulta(app):
    def _consulta(sql, parametros=()):
        with app.app_context():
            return get_db().execute(sql, parametros).fetchall()

    return _consulta
