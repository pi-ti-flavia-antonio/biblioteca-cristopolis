from flask import Blueprint, render_template

from .emprestimos import repository as emprestimos
from .livros import repository as livros
from .texto import formatar_data
from .usuarios import repository as usuarios

main_bp = Blueprint("main", __name__)


def _para_painel(emprestimo):
    return {
        "livro_titulo": emprestimo["livro_titulo"],
        "livro_autor": emprestimo["livro_autor"],
        "usuario_nome": emprestimo["usuario_nome"],
        "data_prevista": formatar_data(emprestimo["data_devolucao_prevista"]),
        "atrasado": bool(emprestimo["atrasado"]),
    }


@main_bp.route("/")
def index():
    return render_template(
        "index.html",
        total_livros=livros.total_exemplares(),
        total_usuarios=usuarios.total_usuarios(),
        total_emprestimos_ativos=emprestimos.contar_ativos(),
        emprestimos_recentes=[_para_painel(e) for e in emprestimos.recentes()],
        atrasados=emprestimos.contar_atrasados(),
    )
