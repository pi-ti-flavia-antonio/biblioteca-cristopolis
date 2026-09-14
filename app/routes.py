from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    # Acervo ainda vazio — dados reais entram quando o módulo de
    # cadastro/empréstimos estiver implementado e o banco for populado.
    # Cada item de emprestimos_ativos deve ter: livro_titulo, livro_autor,
    # usuario_nome, data_prevista (dd/mm/aaaa), data_prevista_iso (aaaa-mm-dd).
    return render_template(
        "index.html",
        total_livros=0,
        total_usuarios=0,
        emprestimos_ativos=[],
        atrasados=0,
    )
