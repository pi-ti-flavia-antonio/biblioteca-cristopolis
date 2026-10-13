# biblioteca-cristopolis

Sistema de gestão de acervo e empréstimos da Biblioteca Municipal de Cristópolis (BA), desenvolvido no Projeto Integrador de Tecnologia da Informação II (UFMS Digital).

O sistema abre como um programa de mesa e funciona sem internet. A conexão só é usada de forma opcional, para buscar os dados de um livro pelo ISBN.

## O que o sistema faz

- **Livros:** cadastro, edição, exclusão e consulta por título, autor ou ISBN (sem diferenciar acentos nem maiúsculas). Ao digitar o ISBN, o botão "Buscar dados" preenche título, autor e ano pela Open Library, com o Google Books como segunda tentativa. Sem internet, o cadastro continua manual.
- **Usuários:** cadastro, edição, exclusão e busca por nome ou CPF (com ou sem pontuação). O CPF é validado pelos dígitos verificadores.
- **Empréstimos:** o usuário e o livro são escolhidos por busca, com lista de opções. O prazo padrão é de 30 dias, e o sistema bloqueia um novo empréstimo para quem ainda está com um livro. Se o usuário ou o livro não existir, há um atalho para cadastrá-lo e voltar ao empréstimo.
- **Reservas:** reserva de livros sem exemplar disponível, com fila por ordem de chegada. Quando um exemplar volta, só a reserva mais antiga é sinalizada para retirada.
- **Devoluções:** registro da devolução, com atualização automática do estoque e aviso de atraso.
- **Relatórios:** empréstimos por período (de até 1 ano), com aviso de geração e exportação em PDF, e lista de empréstimos em atraso.
- **Painel inicial:** totais do acervo, empréstimos ativos, usuários e empréstimos recentes.

Ainda não implementados: backup do banco para a nuvem e login de funcionários.

## Tecnologias

- **Backend:** Python com Flask
- **Interface:** HTML gerado com templates Jinja e CSS responsivo. O único JavaScript é um pequeno trecho na tela de relatórios, que mostra o aviso de geração do PDF
- **Banco de dados:** SQLite, salvo localmente em `data/biblioteca.db`
- **Janela do sistema:** pywebview, que exibe o sistema como programa, sem barra de endereço
- **Bibliotecas auxiliares:** requests (busca por ISBN) e reportlab (geração do PDF)

## Principais decisões de desenvolvimento

- **Flask, SQLite e pywebview:** poucos recursos, nenhum servidor para instalar e funcionamento sem internet, adequado ao único computador da biblioteca e a uma servidora que opera o sistema sozinha.
- **Uso em computador:** o sistema é pensado para o computador da biblioteca, não para celulares ou tablets. O CSS responsivo ajusta o layout a monitores, notebooks e à janela redimensionada (mínimo de 900 x 600).
- **Regras de negócio no servidor:** disponibilidade, atraso e bloqueio de um segundo empréstimo são calculados em um só lugar. Uma versão com script no navegador repetia essas regras e foi removida.
- **Busca de dados por ISBN com APIs REST, opcional:** o protocolo Z39.50 exige uma biblioteca em C e depende de servidores públicos instáveis. Sem internet, o cadastro continua manual.
- **Busca com lista de opções no empréstimo:** a lista suspensa com todos os usuários e livros ficava difícil de usar com um acervo grande.
- **Reservas em fila por ordem de chegada:** quando um exemplar volta, só a reserva mais antiga é sinalizada.
- **Acessibilidade:** HTML semântico (`nav`, `header`, `main`, um `h1` por página), campos com rótulo, avisos com `role`, item atual do menu marcado e link para pular ao conteúdo.

## Como instalar e usar

Desenvolvido e testado com Python 3.12 ([python.org](https://www.python.org/downloads/)).

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

- `main.py`: sobe o Flask em segundo plano e abre a janela do sistema
- `app/__init__.py`: cria o app, configura o banco e registra os módulos
- `app/schema.sql`: tabelas do banco, seguindo o Diagrama Entidade-Relacionamento do projeto
- `app/security.py`: proteção contra requisições forjadas (token CSRF) em todos os formulários
- `app/texto.py`: funções de apoio (busca sem acento, validação de CPF, formatação de datas)
- `app/livros/`, `app/usuarios/`, `app/emprestimos/`, `app/devolucoes/`, `app/relatorios/`: um módulo para cada área do sistema. Quando o módulo é maior, ele se divide em `routes.py` (recebe as requisições), `validacao.py` (confere os campos) e `repository.py` (fala com o banco)
- `app/templates/`: páginas HTML (`base.html` tem o menu lateral, as demais herdam dele)
- `app/static/css/style.css`: estilos do sistema, com ajustes para telas menores
- `tests/`: testes automatizados de cada módulo
