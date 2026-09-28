import pytest

from app import create_app
from app.database import get_db
from app.livros import repository
from app.usuarios import repository as usuarios_repository

TOKEN = "token-de-teste"


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": tmp_path / "teste.db", "SECRET_KEY": "teste"})


@pytest.fixture
def client(app):
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
            **extra,
        }
        with app.app_context():
            return repository.criar(dados)

    return _criar


@pytest.fixture
def registrar_emprestimo(app):
    def _registrar(id_livro, status="ativo", id_usuario=None):
        with app.app_context():
            db = get_db()
            with db:
                if id_usuario is None:
                    id_usuario = db.execute("INSERT INTO usuario (nome) VALUES ('Leitor')").lastrowid
                db.execute(
                    """
                    INSERT INTO emprestimo (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro)
                    VALUES ('2026-09-01', '2026-09-15', ?, ?, ?)
                    """,
                    (status, id_usuario, id_livro),
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
