# biblioteca-cristopolis

Sistema de gestão de acervo e empréstimos da Biblioteca Municipal de Cristópolis (BA), desenvolvido no Projeto Integrador de Tecnologia da Informação II (UFMS Digital).

O sistema abre como um programa de mesa e funciona sem internet. A conexão só é usada de forma opcional, para buscar os dados de um livro pelo ISBN.

## O que o sistema faz

- **Todas as buscas** mostram sugestões enquanto se digita. Escolher uma sugestão faz a busca na hora, e Enter busca o que foi digitado.
- **Livros:** cadastro, edição, exclusão e consulta por título, autor ou ISBN (sem diferenciar acentos nem maiúsculas). Ao digitar o ISBN, o botão "Buscar dados" preenche título, autor e ano pela Open Library, com o Google Books como segunda tentativa. Sem internet, o cadastro continua manual.
- **Usuários:** cadastro, edição e busca por nome ou CPF (com ou sem pontuação). O CPF é validado pelos dígitos verificadores. O telefone precisa ter um DDD existente e o formato de celular (DDD, 9 e 8 dígitos) ou de fixo (DDD e 8 dígitos); o e-mail, se informado, precisa ter um formato válido. O sistema não confirma que o número ou o e-mail realmente existem.
- **Excluir, inativar e reativar usuário:** quem está com livro emprestado ou reserva ativa não pode ser excluído nem inativado. Quem nunca teve empréstimo nem reserva pode ser excluído. Quem tem histórico não pode ser excluído, porque os relatórios mostram o nome nos empréstimos antigos, mas pode ser inativado: o cadastro some das buscas de empréstimo e reserva e continua no histórico. Para reativar, o cadastro aparece na lista com o filtro "Mostrar inativos" (ou ao buscar por um nome ou CPF que só existe como inativo), e quem tenta cadastrar o CPF de um inativo recebe a opção de reativá-lo.
- **Empréstimos:** o usuário e o livro são escolhidos em campos de busca que mostram sugestões enquanto se digita, ignorando acentos. O prazo padrão é de 30 dias, e o sistema bloqueia um novo empréstimo para quem ainda está com um livro. Se o usuário ou o livro não existir, há um atalho para cadastrá-lo e voltar ao empréstimo.
- **Reservas:** reserva de livros sem exemplar disponível, com fila por ordem de chegada. Quando um exemplar volta, só a reserva mais antiga é sinalizada para retirada, com mensagem na devolução, um contador vermelho no menu e na aba Reservas (que some quando a aba é aberta) e um aviso fixo no topo da tela, que continua enquanto a retirada não for registrada, com o telefone e um botão que abre o WhatsApp com a mensagem pronta.
- **Devoluções:** registro da devolução, com atualização automática do estoque e aviso de atraso.
- **Relatórios:** empréstimos por período (de até 1 ano), com aviso de geração e exportação em PDF, e lista de empréstimos em atraso.
- **Confirmação:** cadastrar, salvar alterações, registrar empréstimo, reserva, retirada e devolução, e cancelar uma reserva abrem uma caixa com a pergunta (por exemplo, "Confirmar devolução?") e os botões Sim e Não. Só o Sim grava; Não e a tecla Esc voltam sem alterar nada. Excluir livro ou usuário já tem uma página própria de confirmação.
- **Painel inicial:** totais do acervo, empréstimos ativos, usuários e empréstimos recentes.
- **Login:** o sistema tem uma conta só, para a funcionária. Na primeira vez que abre sem conta, pede o nome, o usuário e a senha (mínimo de 8 caracteres), e a senha fica gravada só como hash. Sem entrar, nenhuma página abre. A sessão expira depois de 30 minutos parada, o menu tem "Minha conta" (para mudar o nome, o usuário e a senha) e "Sair", e depois de 5 senhas erradas o login espera 60 segundos. Quem esquece a senha ou o usuário roda `python redefinir_senha.py` no computador da biblioteca. O login protege a tela do sistema, não o arquivo `data/biblioteca.db`: quem abrir a pasta do computador consegue ler o banco, então a máquina também precisa de senha no Windows.

## Tecnologias

- **Backend:** Python com Flask
- **Interface:** HTML gerado com templates Jinja e CSS responsivo. O JavaScript se limita a dois trechos: as sugestões enquanto se digita (em todas as barras de busca e nos campos de usuário e livro de empréstimos e reservas) e o aviso de geração do PDF na tela de relatórios
- **Banco de dados:** SQLite, salvo localmente em `data/biblioteca.db` (ou em `%LOCALAPPDATA%\BibliotecaCristopolis\data` quando o sistema roda como executável)
- **Janela do sistema:** pywebview, que exibe o sistema como programa, sem barra de endereço
- **Bibliotecas auxiliares:** requests (busca por ISBN) e reportlab (geração do PDF)
- **Backup:** cryptography (Fernet) e as bibliotecas do Google para a API do Drive
- **Executável para Windows:** PyInstaller (opcional, só para gerar o `.exe`)

## Principais decisões de desenvolvimento

- **Flask, SQLite e pywebview:** poucos recursos, nenhum servidor para instalar e funcionamento sem internet, adequado ao único computador da biblioteca e a uma servidora que opera o sistema sozinha.
- **Uso em computador:** o sistema é pensado para o computador da biblioteca, não para celulares ou tablets. O CSS responsivo ajusta o layout a monitores, notebooks e à janela redimensionada (mínimo de 900 x 600).
- **Regras de negócio no servidor:** disponibilidade, atraso e bloqueio de um segundo empréstimo são calculados em um só lugar. Uma versão com script no navegador repetia essas regras e foi removida.
- **Busca de dados por ISBN com APIs REST, opcional:** o protocolo Z39.50 exige uma biblioteca em C e depende de servidores públicos instáveis. Sem internet, o cadastro continua manual.
- **Busca com sugestões ao digitar no empréstimo:** a lista suspensa com todos os usuários e livros ficava difícil de usar com um acervo grande. As sugestões vêm do servidor, que continua sendo a única fonte das regras, e o CPF aparece mascarado.
- **Reservas em fila por ordem de chegada:** quando um exemplar volta, só a reserva mais antiga é sinalizada.
- **Servidor só local:** o Flask aceita conexões apenas do próprio computador (`127.0.0.1`), sem modo de depuração, então o sistema não fica aberto para a rede.
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

### Executável para Windows (opcional)

Para rodar sem o Python instalado, o repositório traz as configurações do PyInstaller (`BibliotecaCristopolis.spec` para o sistema e `BackupBiblioteca.spec` para o backup):

```bash
pip install pyinstaller
pyinstaller BibliotecaCristopolis.spec
pyinstaller BackupBiblioteca.spec
```

Os executáveis saem em `dist/`, que não vai para o GitHub. **Atenção:** o executável guarda os dados em `%LOCALAPPDATA%\BibliotecaCristopolis\data`, e não na pasta do projeto. Quem já usa o sistema com Python precisa copiar o `biblioteca.db` e a chave de backup para lá antes da primeira abertura, senão começa com um banco vazio. Este caminho ainda precisa de validação em um computador limpo. Os detalhes e as limitações estão na [documentação técnica](docs/BACKUP_E_RESTAURACAO.md#10-executável-para-windows-pyinstaller).

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes usam um banco temporário, então não mexem nos dados de `data/`.

## Organização do código

- `main.py`: sobe o Flask em segundo plano e abre a janela do sistema
- `caminhos.py`: define a pasta de dados e o caminho do banco, conforme o sistema rode com Python ou como executável
- `app/__init__.py`: cria o app, configura o banco e registra os módulos
- `app/schema.sql`: tabelas do banco, seguindo o Diagrama Entidade-Relacionamento do projeto
- `app/security.py`: proteção contra requisições forjadas (token CSRF) em todos os formulários
- `app/texto.py`: funções de apoio (busca sem acento, validação de CPF, formatação de datas)
- `app/livros/`, `app/usuarios/`, `app/emprestimos/`, `app/devolucoes/`, `app/relatorios/`: um módulo para cada área do sistema. Quando o módulo é maior, ele se divide em `routes.py` (recebe as requisições), `validacao.py` (confere os campos) e `repository.py` (fala com o banco)
- `app/templates/`: páginas HTML (`base.html` tem o menu lateral, as demais herdam dele)
- `app/static/css/style.css`: estilos do sistema, com ajustes para telas menores
- `tests/`: testes automatizados de cada módulo
- `backup.py`, `criptografia.py`, `drive_backup.py`, `controle_backups.py`, `restaurar_drive.py`: backup criptografado, envio ao Google Drive e restauração (veja a seção Backup e recuperação)
- `backup_main.py` e os arquivos `.spec`: geração dos executáveis para Windows


## Backup e recuperação

O sistema possui uma rotina de backup automático do banco de
dados SQLite, com criptografia Fernet e armazenamento no Google Drive.

A implementação inclui:
- Criação e verificação de backups.
- Criptografia dos arquivos.
- Integração com a Google Drive API.
- Reenvio após falhas de conexão.
- Envio para uma pasta definida do Drive, indicada pela variável de ambiente `BIBLIOTECA_DRIVE_FOLDER_ID`. **Sem ela o envio é recusado**: o backup criptografado fica pendente no computador e a execução termina com falha.
- Retenção de até 7 backups locais já enviados.
- Execução automática pelo Agendador de Tarefas do Windows, com o Python do projeto ou com o `BackupBiblioteca.exe`.
- Procedimentos de recuperação e testes de integridade.

O arquivo de credenciais do Google, o token, a chave de criptografia e os bancos não vão para o GitHub (estão no `.gitignore`).

Para informações sobre instalação, bibliotecas, APIs, configuração
e restauração, consulte a
[documentação técnica de backup](docs/BACKUP_E_RESTAURACAO.md).
