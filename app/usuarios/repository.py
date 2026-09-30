from ..database import get_db
from ..texto import limpar_digitos, normalizar

POR_PAGINA = 25

_SELECT_USUARIOS = """
    SELECT id_usuario, nome, cpf, telefone, email, endereco, tipo_usuario
      FROM usuario
"""


class UsuarioComEmprestimos(Exception):
    """Usuário com histórico de empréstimos não pode ser excluído."""


def _escapar_like(texto):
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filtro_busca(termo):
    termo = termo.strip()
    if not termo:
        return "", {}

    condicoes = ["normalizar(nome) LIKE :texto ESCAPE '\\'"]
    parametros = {"texto": f"%{_escapar_like(normalizar(termo))}%"}

    digitos = limpar_digitos(termo)
    if len(digitos) >= 3:
        condicoes.append("cpf LIKE :cpf")
        parametros["cpf"] = f"%{digitos}%"

    return "WHERE " + " OR ".join(condicoes), parametros


def contar(termo=""):
    filtro, parametros = _filtro_busca(termo)
    return get_db().execute(f"SELECT COUNT(*) FROM usuario {filtro}", parametros).fetchone()[0]


def listar(termo="", pagina=1):
    filtro, parametros = _filtro_busca(termo)
    parametros = {**parametros, "limite": POR_PAGINA, "offset": (pagina - 1) * POR_PAGINA}
    return get_db().execute(
        f"{_SELECT_USUARIOS} {filtro} ORDER BY normalizar(nome), id_usuario LIMIT :limite OFFSET :offset",
        parametros,
    ).fetchall()


def obter(id_usuario):
    return get_db().execute(f"{_SELECT_USUARIOS} WHERE id_usuario = ?", (id_usuario,)).fetchone()


def buscar_por_cpf(cpf):
    return get_db().execute("SELECT id_usuario, nome FROM usuario WHERE cpf = ?", (cpf,)).fetchone()


def total_usuarios():
    return get_db().execute("SELECT COUNT(*) FROM usuario").fetchone()[0]


def opcoes_para_emprestimo():
    """Todos os usuários, para o formulário de empréstimo."""
    return get_db().execute(f"{_SELECT_USUARIOS} ORDER BY normalizar(nome)").fetchall()


def contar_emprestimos(id_usuario):
    return get_db().execute(
        "SELECT COUNT(*) FROM emprestimo WHERE id_usuario = ?", (id_usuario,)
    ).fetchone()[0]


def criar(dados):
    db = get_db()
    with db:
        cursor = db.execute(
            """
            INSERT INTO usuario (nome, cpf, telefone, tipo_usuario, email, endereco)
            VALUES (:nome, :cpf, :telefone, :tipo_usuario, :email, :endereco)
            """,
            dados,
        )
    return cursor.lastrowid


def atualizar(id_usuario, dados):
    db = get_db()
    with db:
        db.execute(
            """
            UPDATE usuario
               SET nome = :nome, cpf = :cpf, telefone = :telefone,
                   tipo_usuario = :tipo_usuario, email = :email, endereco = :endereco
             WHERE id_usuario = :id_usuario
            """,
            {**dados, "id_usuario": id_usuario},
        )


def excluir(id_usuario):
    if contar_emprestimos(id_usuario) > 0:
        raise UsuarioComEmprestimos(id_usuario)
    db = get_db()
    with db:
        db.execute("DELETE FROM usuario WHERE id_usuario = ?", (id_usuario,))
