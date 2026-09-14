# biblioteca-cristopolis
Sistema de gestão de acervo e empréstimos — Biblioteca Municipal de Cristópolis

## Stack

- **Backend:** Python (Flask)
- **Frontend:** HTML, CSS, JS
- **Banco de dados:** SQLite (local)
- **Empacotamento:** pywebview (janela nativa, sem depender de navegador)

## Como rodar (desenvolvimento)

Requer Python instalado ([python.org](https://www.python.org/downloads/)).

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Isso abre uma janela do sistema apontando para o servidor Flask local.
