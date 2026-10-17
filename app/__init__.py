import os
import secrets
from pathlib import Path

from flask import Flask, render_template

from . import database, security
from .texto import formatar_cpf, formatar_data, formatar_telefone, mascarar_cpf

MENSAGENS_ERRO = {
    400: "Não foi possível concluir a ação. Volte à página anterior e tente de novo.",
    404: "Página não encontrada.",
}


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("BIBLIOTECA_SECRET_KEY") or secrets.token_hex(32),
        DATABASE=Path(app.root_path).parent / "data" / "biblioteca.db",
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)

    database.init_app(app)
    security.init_app(app)
    app.jinja_env.filters["cpf"] = formatar_cpf
    app.jinja_env.filters["telefone"] = formatar_telefone
    app.jinja_env.filters["data_br"] = formatar_data
    app.jinja_env.filters["cpf_mascarado"] = mascarar_cpf

    from .emprestimos import reservas_repository
    from .devolucoes import devolucoes_bp
    from .emprestimos import emprestimos_bp
    from .livros import livros_bp
    from .relatorios import relatorios_bp
    from .routes import main_bp
    from .usuarios import usuarios_bp

    app.context_processor(lambda: {"reservas_prontas": reservas_repository.contar_prontas})
    app.register_blueprint(main_bp)
    app.register_blueprint(livros_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(emprestimos_bp)
    app.register_blueprint(devolucoes_bp)
    app.register_blueprint(relatorios_bp)
    app.register_error_handler(400, _pagina_erro)
    app.register_error_handler(404, _pagina_erro)

    return app


def _pagina_erro(erro):
    mensagem = MENSAGENS_ERRO[erro.code]
    return render_template("erro.html", codigo=erro.code, mensagem=mensagem), erro.code
