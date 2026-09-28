from flask import Blueprint, render_template

from .livros import repository as livros
from .usuarios import repository as usuarios

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    # Empréstimos ainda não têm módulo próprio, por isso segue zerado.
    # Cada item de emprestimos_ativos deve ter: livro_titulo, livro_autor,
    # usuario_nome, data_prevista (dd/mm/aaaa) e data_prevista_iso (aaaa-mm-dd).
    return render_template(
        "index.html",
        total_livros=livros.total_exemplares(),
        total_usuarios=usuarios.total_usuarios(),
        emprestimos_ativos=[],
        atrasados=0,
    )
