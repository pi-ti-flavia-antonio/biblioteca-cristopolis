from ..database import get_db
from ..texto import limpar_isbn, normalizar

POR_PAGINA = 25

_SELECT_LIVROS = """
    SELECT l.id_livro, l.titulo, l.autor, l.isbn, l.ano_publicacao,
           l.quantidade_total, c.nome AS categoria,
           COALESCE(e.ativos, 0) AS emprestimos_ativos,
           l.quantidade_total - COALESCE(e.ativos, 0) AS quantidade_disponivel
      FROM livro l
      LEFT JOIN categoria c ON c.id_categoria = l.id_categoria
      LEFT JOIN (
            SELECT id_livro, COUNT(*) AS ativos
              FROM emprestimo
             WHERE status = 'ativo'
          GROUP BY id_livro
      ) e ON e.id_livro = l.id_livro
"""


class LivroComEmprestimos(Exception):
    """Livro com histórico de empréstimos não pode ser excluído."""


def _escapar_like(texto):
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filtro_busca(termo):
    termo = termo.strip()
    if not termo:
        return "", {}

    condicoes = [
        "normalizar(l.titulo) LIKE :texto ESCAPE '\\'",
        "normalizar(l.autor) LIKE :texto ESCAPE '\\'",
    ]
    parametros = {"texto": f"%{_escapar_like(normalizar(termo))}%"}

    isbn = limpar_isbn(termo)
    if len(isbn) >= 3:
        condicoes.append("l.isbn LIKE :isbn")
        parametros["isbn"] = f"%{isbn}%"

    return "WHERE " + " OR ".join(condicoes), parametros


def contar(termo=""):
    filtro, parametros = _filtro_busca(termo)
    return get_db().execute(f"SELECT COUNT(*) FROM livro l {filtro}", parametros).fetchone()[0]


def listar(termo="", pagina=1):
    filtro, parametros = _filtro_busca(termo)
    parametros = {**parametros, "limite": POR_PAGINA, "offset": (pagina - 1) * POR_PAGINA}
    return get_db().execute(
        f"{_SELECT_LIVROS} {filtro} ORDER BY normalizar(l.titulo), l.id_livro LIMIT :limite OFFSET :offset",
        parametros,
    ).fetchall()


def obter(id_livro):
    return get_db().execute(f"{_SELECT_LIVROS} WHERE l.id_livro = ?", (id_livro,)).fetchone()


def buscar_por_isbn(isbn):
    return get_db().execute("SELECT id_livro, titulo FROM livro WHERE isbn = ?", (isbn,)).fetchone()


def nomes_categorias():
    linhas = get_db().execute("SELECT nome FROM categoria ORDER BY nome").fetchall()
    return [linha["nome"] for linha in linhas]


def total_exemplares():
    return get_db().execute("SELECT COALESCE(SUM(quantidade_total), 0) FROM livro").fetchone()[0]


def contar_emprestimos(id_livro):
    return get_db().execute(
        "SELECT COUNT(*) FROM emprestimo WHERE id_livro = ?", (id_livro,)
    ).fetchone()[0]


def _resolver_categoria(db, nome):
    if not nome:
        return None
    alvo = normalizar(nome)
    for linha in db.execute("SELECT id_categoria, nome FROM categoria"):
        if normalizar(linha["nome"]) == alvo:
            return linha["id_categoria"]
    return db.execute("INSERT INTO categoria (nome) VALUES (?)", (nome,)).lastrowid


def criar(dados):
    db = get_db()
    with db:
        parametros = {**dados, "id_categoria": _resolver_categoria(db, dados["categoria"])}
        cursor = db.execute(
            """
            INSERT INTO livro (titulo, autor, isbn, ano_publicacao, id_categoria, quantidade_total)
            VALUES (:titulo, :autor, :isbn, :ano_publicacao, :id_categoria, :quantidade)
            """,
            parametros,
        )
    return cursor.lastrowid


def atualizar(id_livro, dados):
    db = get_db()
    with db:
        parametros = {
            **dados,
            "id_livro": id_livro,
            "id_categoria": _resolver_categoria(db, dados["categoria"]),
        }
        db.execute(
            """
            UPDATE livro
               SET titulo = :titulo, autor = :autor, isbn = :isbn,
                   ano_publicacao = :ano_publicacao, id_categoria = :id_categoria,
                   quantidade_total = :quantidade
             WHERE id_livro = :id_livro
            """,
            parametros,
        )


def excluir(id_livro):
    if contar_emprestimos(id_livro) > 0:
        raise LivroComEmprestimos(id_livro)
    db = get_db()
    with db:
        db.execute("DELETE FROM livro WHERE id_livro = ?", (id_livro,))
