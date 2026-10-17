from datetime import date, timedelta

from ..database import get_db
from ..texto import normalizar

POR_PAGINA = 25
PRAZO_PADRAO_DIAS = 30

_SELECT_EMPRESTIMOS = """
    SELECT emp.id_emprestimo, emp.id_livro, emp.data_emprestimo, emp.data_devolucao_prevista,
           emp.status,
           l.titulo AS livro_titulo, l.autor AS livro_autor,
           u.nome AS usuario_nome, u.telefone AS usuario_telefone,
           (emp.status = 'ativo' AND date(emp.data_devolucao_prevista) < date('now'))
               AS atrasado
      FROM emprestimo emp
      JOIN livro l ON l.id_livro = emp.id_livro
      JOIN usuario u ON u.id_usuario = emp.id_usuario
"""


class LivroIndisponivel(Exception):
    """O livro não tem exemplares disponíveis no momento."""


class UsuarioComPendencia(Exception):
    """O usuário já está com um exemplar emprestado."""


class EmprestimoInvalido(Exception):
    """O empréstimo não existe ou já foi devolvido."""


def _escapar_like(texto):
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filtro_busca(termo, apenas_ativos=False):
    termo = termo.strip()
    condicoes = ["emp.status = 'ativo'"] if apenas_ativos else []
    parametros = {}

    if termo:
        parametros["texto"] = f"%{_escapar_like(normalizar(termo))}%"
        busca = (
            "(normalizar(l.titulo) LIKE :texto ESCAPE '\\' "
            "OR normalizar(u.nome) LIKE :texto ESCAPE '\\')"
        )
        condicoes.append(busca)

    if not condicoes:
        return "", {}
    return "WHERE " + " AND ".join(condicoes), parametros


def sugerir(termo, apenas_ativos=False, limite=6):
    """Livros e usuários que aparecem em empréstimos e combinam com o que está sendo digitado."""
    termo = termo.strip()
    if not termo:
        return []
    ativo = "emp.status = 'ativo' AND " if apenas_ativos else ""
    parametros = {"texto": f"%{_escapar_like(normalizar(termo))}%", "limite": max(limite // 2, 1)}
    db = get_db()
    livros = db.execute(
        f"SELECT DISTINCT l.titulo AS titulo, l.autor AS subtitulo FROM emprestimo emp "
        f"JOIN livro l ON l.id_livro = emp.id_livro "
        f"WHERE {ativo}normalizar(l.titulo) LIKE :texto ESCAPE '\\' ORDER BY normalizar(l.titulo) LIMIT :limite",
        parametros,
    ).fetchall()
    usuarios = db.execute(
        f"SELECT DISTINCT u.nome AS titulo FROM emprestimo emp "
        f"JOIN usuario u ON u.id_usuario = emp.id_usuario "
        f"WHERE {ativo}normalizar(u.nome) LIKE :texto ESCAPE '\\' ORDER BY normalizar(u.nome) LIMIT :limite",
        parametros,
    ).fetchall()
    return (
        [{"titulo": l["titulo"], "subtitulo": l["subtitulo"], "rotulo": "Livro"} for l in livros]
        + [{"titulo": u["titulo"], "subtitulo": "", "rotulo": "Usuário"} for u in usuarios]
    )


def contar(termo=""):
    filtro, parametros = _filtro_busca(termo)
    return get_db().execute(
        f"SELECT COUNT(*) FROM emprestimo emp JOIN livro l ON l.id_livro = emp.id_livro "
        f"JOIN usuario u ON u.id_usuario = emp.id_usuario {filtro}",
        parametros,
    ).fetchone()[0]


def listar(termo="", pagina=1):
    filtro, parametros = _filtro_busca(termo)
    parametros = {**parametros, "limite": POR_PAGINA, "offset": (pagina - 1) * POR_PAGINA}
    return get_db().execute(
        f"{_SELECT_EMPRESTIMOS} {filtro} "
        f"ORDER BY emp.data_emprestimo DESC, emp.id_emprestimo DESC LIMIT :limite OFFSET :offset",
        parametros,
    ).fetchall()


def contar_ativos_busca(termo=""):
    filtro, parametros = _filtro_busca(termo, apenas_ativos=True)
    return get_db().execute(
        f"SELECT COUNT(*) FROM emprestimo emp JOIN livro l ON l.id_livro = emp.id_livro "
        f"JOIN usuario u ON u.id_usuario = emp.id_usuario {filtro}",
        parametros,
    ).fetchone()[0]


def listar_ativos(termo="", pagina=1):
    filtro, parametros = _filtro_busca(termo, apenas_ativos=True)
    parametros = {**parametros, "limite": POR_PAGINA, "offset": (pagina - 1) * POR_PAGINA}
    return get_db().execute(
        f"{_SELECT_EMPRESTIMOS} {filtro} "
        f"ORDER BY emp.data_devolucao_prevista, emp.id_emprestimo LIMIT :limite OFFSET :offset",
        parametros,
    ).fetchall()


def obter(id_emprestimo):
    return get_db().execute(
        f"{_SELECT_EMPRESTIMOS} WHERE emp.id_emprestimo = ?", (id_emprestimo,)
    ).fetchone()


def registrar_devolucao(id_emprestimo):
    emprestimo = obter(id_emprestimo)
    if emprestimo is None or emprestimo["status"] != "ativo":
        raise EmprestimoInvalido(id_emprestimo)

    hoje = date.today()
    prevista = date.fromisoformat(emprestimo["data_devolucao_prevista"])
    dias_atraso = max((hoje - prevista).days, 0)

    db = get_db()
    with db:
        db.execute(
            "UPDATE emprestimo SET status = 'devolvido', data_devolucao_real = ? WHERE id_emprestimo = ?",
            (hoje.isoformat(), id_emprestimo),
        )
        db.execute(
            "UPDATE reserva SET aviso_visto = 0 WHERE id_livro = ? AND status = 'ativa'",
            (emprestimo["id_livro"],),
        )

    return {
        "id_livro": emprestimo["id_livro"],
        "livro_titulo": emprestimo["livro_titulo"],
        "usuario_nome": emprestimo["usuario_nome"],
        "dias_atraso": dias_atraso,
    }


def recentes(limite=5):
    return get_db().execute(
        f"{_SELECT_EMPRESTIMOS} WHERE emp.status = 'ativo' "
        f"ORDER BY emp.data_devolucao_prevista LIMIT :limite",
        {"limite": limite},
    ).fetchall()


def contar_ativos():
    return get_db().execute("SELECT COUNT(*) FROM emprestimo WHERE status = 'ativo'").fetchone()[0]


def contar_atrasados():
    return get_db().execute(
        "SELECT COUNT(*) FROM emprestimo "
        "WHERE status = 'ativo' AND date(data_devolucao_prevista) < date('now')"
    ).fetchone()[0]


def listar_atrasados(pagina=1):
    parametros = {"limite": POR_PAGINA, "offset": (pagina - 1) * POR_PAGINA}
    return get_db().execute(
        f"{_SELECT_EMPRESTIMOS} WHERE emp.status = 'ativo' "
        f"AND date(emp.data_devolucao_prevista) < date('now') "
        f"ORDER BY emp.data_devolucao_prevista LIMIT :limite OFFSET :offset",
        parametros,
    ).fetchall()


def contar_por_periodo(data_inicio, data_fim):
    return get_db().execute(
        "SELECT COUNT(*) FROM emprestimo emp "
        "WHERE date(emp.data_emprestimo) BETWEEN :inicio AND :fim",
        {"inicio": data_inicio.isoformat(), "fim": data_fim.isoformat()},
    ).fetchone()[0]


def listar_por_periodo(data_inicio, data_fim, pagina=1):
    parametros = {
        "inicio": data_inicio.isoformat(),
        "fim": data_fim.isoformat(),
        "limite": POR_PAGINA,
        "offset": (pagina - 1) * POR_PAGINA,
    }
    return get_db().execute(
        f"{_SELECT_EMPRESTIMOS} WHERE date(emp.data_emprestimo) BETWEEN :inicio AND :fim "
        f"ORDER BY emp.data_emprestimo DESC, emp.id_emprestimo DESC LIMIT :limite OFFSET :offset",
        parametros,
    ).fetchall()


def listar_por_periodo_completo(data_inicio, data_fim):
    """Todos os empréstimos do período, sem paginação (para o PDF do relatório)."""
    return get_db().execute(
        f"{_SELECT_EMPRESTIMOS} WHERE date(emp.data_emprestimo) BETWEEN :inicio AND :fim "
        f"ORDER BY emp.data_emprestimo DESC, emp.id_emprestimo DESC",
        {"inicio": data_inicio.isoformat(), "fim": data_fim.isoformat()},
    ).fetchall()


def livro_disponivel(id_livro):
    linha = get_db().execute(
        """
        SELECT l.quantidade_total - COALESCE((
            SELECT COUNT(*) FROM emprestimo WHERE id_livro = l.id_livro AND status = 'ativo'
        ), 0) AS disponivel
          FROM livro l
         WHERE l.id_livro = ?
        """,
        (id_livro,),
    ).fetchone()
    return linha["disponivel"] if linha else None


def usuario_tem_pendencia(id_usuario):
    linha = get_db().execute(
        "SELECT COUNT(*) FROM emprestimo WHERE id_usuario = ? AND status = 'ativo'",
        (id_usuario,),
    ).fetchone()
    return linha[0] > 0


def criar(id_usuario, id_livro):
    disponivel = livro_disponivel(id_livro)
    if disponivel is None or disponivel <= 0:
        raise LivroIndisponivel(id_livro)
    if usuario_tem_pendencia(id_usuario):
        raise UsuarioComPendencia(id_usuario)

    hoje = date.today()
    prevista = hoje + timedelta(days=PRAZO_PADRAO_DIAS)
    db = get_db()
    with db:
        cursor = db.execute(
            """
            INSERT INTO emprestimo (data_emprestimo, data_devolucao_prevista, status, id_usuario, id_livro)
            VALUES (?, ?, 'ativo', ?, ?)
            """,
            (hoje.isoformat(), prevista.isoformat(), id_usuario, id_livro),
        )
    return cursor.lastrowid, prevista
