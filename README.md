# biblioteca-cristopolis

Sistema de gestão de acervo e empréstimos da Biblioteca Municipal de Cristópolis.

## Stack

- **Backend:** Python (Flask)
- **Frontend:** HTML, CSS e JS
- **Banco de dados:** SQLite, salvo localmente em `data/biblioteca.db`
- **Janela do sistema:** pywebview (abre como programa, sem depender do navegador)

## Como rodar (desenvolvimento)

Requer Python instalado ([python.org](https://www.python.org/downloads/)).

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Isso abre a janela do sistema. O banco é criado sozinho na primeira execução.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes usam um banco temporário, então não mexem nos dados de `data/`.

## Organização do código

- `main.py`: abre a janela do sistema e sobe o Flask em segundo plano
- `app/__init__.py`: cria o app, configura o banco e registra as rotas
- `app/schema.sql`: tabelas do banco, seguindo o DER do relatório
- `app/livros/`: módulo de livros (`routes.py` recebe as requisições, `validacao.py` confere os campos, `repository.py` fala com o banco)
- `app/templates/`: páginas HTML (`base.html` tem o menu lateral, as demais herdam dele)
- `app/static/`: CSS e JS

Os próximos módulos (usuários, empréstimos, devoluções, relatórios) seguem essa mesma divisão.
