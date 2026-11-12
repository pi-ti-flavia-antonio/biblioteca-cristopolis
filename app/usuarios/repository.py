from ..database import get_db
from ..texto import limpar_digitos, normalizar
from .validacao import ULTIMO_NUMERO_RESERVADO

POR_PAGINA = 25

_SELECT_USUARIOS = """
    SELECT id_usuario, nome, cpf, telefone, email, endereco, tipo_usuario, ativo, numero_carteirinha,
           EXISTS (SELECT 1 FROM usuario_foto WHERE usuario_foto.id_usuario = usuario.id_usuario) AS tem_foto
      FROM usuario
"""


class UsuarioComPendencia(Exception):
    """Usuário com livro emprestado ou reserva ativa não pode ser excluído nem inativado."""


class UsuarioComHistorico(Exception):
    """Usuário com empréstimos ou reservas no histórico só pode ser inativado."""


def _escapar_like(texto):
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filtro_busca(termo, incluir_inativos=False):
    condicoes = []
    parametros = {}

    termo = termo.strip()
    if termo:
        busca = ["normalizar(nome) LIKE :texto ESCAPE '\\'"]
        parametros["texto"] = f"%{_escapar_like(normalizar(termo))}%"
        digitos = limpar_digitos(termo)
        if len(digitos) >= 3:
            busca.append("cpf LIKE :cpf")
            parametros["cpf"] = f"%{digitos}%"
        if termo.isdigit():
            busca.append("numero_carteirinha = :carteirinha")
            parametros["carteirinha"] = int(termo)
        condicoes.append("(" + " OR ".join(busca) + ")")

    if not incluir_inativos:
        condicoes.append("ativo = 1")

    return ("WHERE " + " AND ".join(condicoes) if condicoes else ""), parametros


def contar(termo="", incluir_inativos=False):
    filtro, parametros = _filtro_busca(termo, incluir_inativos)
    return get_db().execute(f"SELECT COUNT(*) FROM usuario {filtro}", parametros).fetchone()[0]


def listar(termo="", pagina=1, incluir_inativos=False):
    filtro, parametros = _filtro_busca(termo, incluir_inativos)
    parametros = {**parametros, "limite": POR_PAGINA, "offset": (pagina - 1) * POR_PAGINA}
    return get_db().execute(
        f"{_SELECT_USUARIOS} {filtro} ORDER BY normalizar(nome), id_usuario LIMIT :limite OFFSET :offset",
        parametros,
    ).fetchall()


def sugerir(termo, limite=6, incluir_inativos=False):
    """Poucos usuários que combinam com o que está sendo digitado, para as sugestões."""
    if not termo.strip():
        return []
    filtro, parametros = _filtro_busca(termo, incluir_inativos)
    return get_db().execute(
        f"{_SELECT_USUARIOS} {filtro} ORDER BY normalizar(nome), id_usuario LIMIT :limite",
        {**parametros, "limite": limite},
    ).fetchall()


def obter(id_usuario):
    return get_db().execute(f"{_SELECT_USUARIOS} WHERE id_usuario = ?", (id_usuario,)).fetchone()


def buscar_por_cpf(cpf):
    return get_db().execute(
        "SELECT id_usuario, nome, ativo FROM usuario WHERE cpf = ?", (cpf,)
    ).fetchone()


def buscar_por_carteirinha(numero):
    return get_db().execute(
        "SELECT id_usuario, nome, ativo FROM usuario WHERE numero_carteirinha = ?", (numero,)
    ).fetchone()


def proximo_numero_carteirinha():
    """O maior número já usado acima da faixa reservada, mais 1 (o primeiro é 11047)."""
    maior = get_db().execute(
        "SELECT MAX(numero_carteirinha) FROM usuario WHERE numero_carteirinha > ?", (ULTIMO_NUMERO_RESERVADO,)
    ).fetchone()[0]
    return (maior or ULTIMO_NUMERO_RESERVADO) + 1


def obter_foto(id_usuario):
    return get_db().execute(
        "SELECT tipo_conteudo, dados FROM usuario_foto WHERE id_usuario = ?", (id_usuario,)
    ).fetchone()


def salvar_foto(id_usuario, tipo_conteudo, dados):
    db = get_db()
    with db:
        db.execute(
            "INSERT OR REPLACE INTO usuario_foto (id_usuario, tipo_conteudo, dados) VALUES (?, ?, ?)",
            (id_usuario, tipo_conteudo, dados),
        )


def remover_foto(id_usuario):
    db = get_db()
    with db:
        db.execute("DELETE FROM usuario_foto WHERE id_usuario = ?", (id_usuario,))


def total_usuarios():
    return get_db().execute("SELECT COUNT(*) FROM usuario WHERE ativo = 1").fetchone()[0]


def opcoes_para_emprestimo(termo=""):
    """Usuários ativos para o formulário de empréstimo, filtrados por nome ou CPF."""
    filtro, parametros = _filtro_busca(termo)
    return get_db().execute(
        f"{_SELECT_USUARIOS} {filtro} ORDER BY normalizar(nome)", parametros
    ).fetchall()


def contar_emprestimos(id_usuario):
    return get_db().execute(
        "SELECT COUNT(*) FROM emprestimo WHERE id_usuario = ?", (id_usuario,)
    ).fetchone()[0]


def contar_pendencias(id_usuario):
    """Empréstimos em aberto mais reservas ativas."""
    return get_db().execute(
        "SELECT (SELECT COUNT(*) FROM emprestimo WHERE id_usuario = :u AND status = 'ativo')"
        " + (SELECT COUNT(*) FROM reserva WHERE id_usuario = :u AND status = 'ativa')",
        {"u": id_usuario},
    ).fetchone()[0]


def contar_historico(id_usuario):
    """Todos os empréstimos e reservas, em qualquer situação."""
    return get_db().execute(
        "SELECT (SELECT COUNT(*) FROM emprestimo WHERE id_usuario = :u)"
        " + (SELECT COUNT(*) FROM reserva WHERE id_usuario = :u)",
        {"u": id_usuario},
    ).fetchone()[0]


def situacao_para_remover(id_usuario):
    """'pendencia' (nada pode ser feito), 'historico' (só inativar) ou 'livre' (pode excluir)."""
    if contar_pendencias(id_usuario) > 0:
        return "pendencia"
    if contar_historico(id_usuario) > 0:
        return "historico"
    return "livre"


def criar(dados):
    db = get_db()
    with db:
        cursor = db.execute(
            """
            INSERT INTO usuario (nome, cpf, telefone, tipo_usuario, email, endereco, numero_carteirinha)
            VALUES (:nome, :cpf, :telefone, :tipo_usuario, :email, :endereco, :numero_carteirinha)
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
                   tipo_usuario = :tipo_usuario, email = :email, endereco = :endereco,
                   numero_carteirinha = :numero_carteirinha
             WHERE id_usuario = :id_usuario
            """,
            {**dados, "id_usuario": id_usuario},
        )


def excluir(id_usuario):
    situacao = situacao_para_remover(id_usuario)
    if situacao == "pendencia":
        raise UsuarioComPendencia(id_usuario)
    if situacao == "historico":
        raise UsuarioComHistorico(id_usuario)
    db = get_db()
    with db:
        db.execute("DELETE FROM usuario WHERE id_usuario = ?", (id_usuario,))


def inativar(id_usuario):
    if contar_pendencias(id_usuario) > 0:
        raise UsuarioComPendencia(id_usuario)
    db = get_db()
    with db:
        db.execute("UPDATE usuario SET ativo = 0 WHERE id_usuario = ?", (id_usuario,))


def reativar(id_usuario):
    db = get_db()
    with db:
        db.execute("UPDATE usuario SET ativo = 1 WHERE id_usuario = ?", (id_usuario,))
