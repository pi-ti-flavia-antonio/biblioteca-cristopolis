from datetime import date

from ..database import get_db
from ..texto import link_whatsapp
from .repository import LivroIndisponivel
from .repository import criar as criar_emprestimo
from .repository import livro_disponivel

_SELECT_RESERVAS = """
    SELECT r.id_reserva, r.data_reserva, r.status, r.id_usuario, r.id_livro, r.aviso_visto,
           l.titulo AS livro_titulo, l.autor AS livro_autor,
           u.nome AS usuario_nome, u.telefone AS usuario_telefone
      FROM reserva r
      JOIN livro l ON l.id_livro = r.id_livro
      JOIN usuario u ON u.id_usuario = r.id_usuario
"""


class LivroComExemplarDisponivel(Exception):
    """O livro tem exemplares disponíveis; não há necessidade de reservar."""


class ReservaDuplicada(Exception):
    """O usuário já tem uma reserva ativa para este livro."""


class ReservaInvalida(Exception):
    """A reserva não existe ou não está mais ativa."""


def _marcar_disponiveis(linhas):
    """A cada exemplar livre, só a reserva mais antiga daquele livro é
    sinalizada como pronta para retirada (RF7.3), respeitando a ordem
    de chegada quando há mais de uma pessoa esperando o mesmo título."""
    vagas_por_livro = {}
    resultado = []
    for linha in linhas:
        id_livro = linha["id_livro"]
        if id_livro not in vagas_por_livro:
            vagas_por_livro[id_livro] = livro_disponivel(id_livro) or 0
        pronta = vagas_por_livro[id_livro] > 0
        if pronta:
            vagas_por_livro[id_livro] -= 1
        item = {**dict(linha), "disponivel_para_retirada": pronta, "whatsapp_url": ""}
        if pronta:
            primeiro_nome = linha["usuario_nome"].split()[0]
            item["whatsapp_url"] = link_whatsapp(
                linha["usuario_telefone"],
                f'Olá, {primeiro_nome}! O livro "{linha["livro_titulo"]}" que você reservou na '
                "Biblioteca Municipal de Cristópolis já está disponível para retirada.",
            )
        resultado.append(item)
    return resultado


def listar_ativas():
    linhas = get_db().execute(
        f"{_SELECT_RESERVAS} WHERE r.status = 'ativa' ORDER BY r.data_reserva, r.id_reserva"
    ).fetchall()
    return _marcar_disponiveis(linhas)


def listar_prontas():
    """Reservas ativas cujo livro já voltou e está esperando a pessoa vir buscar."""
    return [r for r in listar_ativas() if r["disponivel_para_retirada"]]


def contar_novas():
    """Reservas prontas que a bibliotecária ainda não viu na aba Reservas."""
    return sum(1 for r in listar_prontas() if not r["aviso_visto"])


def marcar_avisos_como_vistos():
    ids = [r["id_reserva"] for r in listar_prontas() if not r["aviso_visto"]]
    if not ids:
        return
    db = get_db()
    with db:
        db.execute(
            f"UPDATE reserva SET aviso_visto = 1 WHERE id_reserva IN ({','.join('?' * len(ids))})", ids
        )


def contar_ativas():
    return get_db().execute("SELECT COUNT(*) FROM reserva WHERE status = 'ativa'").fetchone()[0]


def _tem_reserva_ativa(id_usuario, id_livro):
    linha = get_db().execute(
        "SELECT COUNT(*) FROM reserva WHERE id_usuario = ? AND id_livro = ? AND status = 'ativa'",
        (id_usuario, id_livro),
    ).fetchone()
    return linha[0] > 0


def criar(id_usuario, id_livro):
    disponivel = livro_disponivel(id_livro)
    if disponivel is None:
        raise LivroIndisponivel(id_livro)
    if disponivel > 0:
        raise LivroComExemplarDisponivel(id_livro)
    if _tem_reserva_ativa(id_usuario, id_livro):
        raise ReservaDuplicada(id_livro)

    db = get_db()
    with db:
        cursor = db.execute(
            "INSERT INTO reserva (data_reserva, status, id_usuario, id_livro) VALUES (?, 'ativa', ?, ?)",
            (date.today().isoformat(), id_usuario, id_livro),
        )
    return cursor.lastrowid


def obter(id_reserva):
    return get_db().execute(f"{_SELECT_RESERVAS} WHERE r.id_reserva = ?", (id_reserva,)).fetchone()


def cancelar(id_reserva):
    reserva = obter(id_reserva)
    if reserva is None or reserva["status"] != "ativa":
        raise ReservaInvalida(id_reserva)
    db = get_db()
    with db:
        db.execute("UPDATE reserva SET status = 'cancelada' WHERE id_reserva = ?", (id_reserva,))


def retirar(id_reserva):
    """Converte a reserva em empréstimo de verdade, reaproveitando as
    mesmas regras de negócio (disponibilidade e pendência do usuário)."""
    reserva = obter(id_reserva)
    if reserva is None or reserva["status"] != "ativa":
        raise ReservaInvalida(id_reserva)

    _, prevista = criar_emprestimo(reserva["id_usuario"], reserva["id_livro"])

    db = get_db()
    with db:
        db.execute("UPDATE reserva SET status = 'concluida' WHERE id_reserva = ?", (id_reserva,))
    return prevista
