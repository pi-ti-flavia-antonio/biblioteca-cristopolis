    # Backup e restauração — Biblioteca Municipal de Cristópolis

> Documentação técnica para a equipe de desenvolvimento e para a implantação.
> Estado: implementação e testes locais realizados em outubro de 2026. Atualizado em 30/10/2026 com a preparação do executável para Windows e o envio a uma pasta definida do Google Drive.
> **Atenção:** este repositório não contém credenciais, chave de criptografia, banco de dados nem configuração do Agendador de Tarefas.

## 1. Objetivo e visão geral

Proteger o banco SQLite da aplicação (`data/biblioteca.db`) contra perda de dados, mantendo cópias locais criptografadas e enviando-as ao Google Drive. O sistema funciona em computador Windows, com execução agendada pelo Agendador de Tarefas, que pode chamar um arquivo `.bat` (com o Python do projeto) ou o executável `BackupBiblioteca.exe` (seção 10).

Fluxo de uma execução:

```text
Banco SQLite (data/biblioteca.db)
       |
       v
backup.py -> cópia consistente e verificação de integridade
       |
       v
criptografia.py -> arquivo biblioteca_AAAA-MM-DD_HH-MM-SS.db.enc
       |
       +--> permanece em data/backups/ se não houver internet
       |
       v
drive_backup.py -> autenticação OAuth -> pasta do Google Drive
       |                                (BIBLIOTECA_DRIVE_FOLDER_ID)
       |
       v
controle_backups.py -> registra o ID do arquivo enviado
       |
       v
retém até 7 arquivos locais já enviados; preserva os pendentes
```

O backup é feito com a API de backup do SQLite, em vez de copiar diretamente um banco em uso. Os arquivos `.db.enc` são protegidos por criptografia simétrica Fernet. A chave deve ser guardada separadamente e não pode ser recuperada do Google Drive se for perdida.

## 2. Arquivos do projeto

| Arquivo | Responsabilidade |
| --- | --- |
| `caminhos.py` | Define a pasta de dados (`pasta_dados()`) e o caminho do banco (`caminho_banco()`), conforme o sistema rode com Python ou como executável (seção 2.1). Usado por `app/__init__.py`, `backup.py`, `criptografia.py`, `controle_backups.py` e `drive_backup.py`. |
| `backup.py` | Cria cópia do SQLite e verifica a integridade. |
| `criptografia.py` | Gera/carrega a chave Fernet, criptografa e descriptografa backups. |
| `drive_backup.py` | Orquestra criação, criptografia, envio à pasta do Drive, registro, retenção e sinalização de falhas. |
| `controle_backups.py` | Mantém o controle local dos nomes e IDs de arquivos enviados; remove cópias locais antigas já enviadas. |
| `executar_backup.bat` | Executa o script com o Python do ambiente virtual e registra saída em log. |
| `backup_main.py` | Ponto de entrada do executável de backup: chama o `drive_backup.py` como programa principal. |
| `BibliotecaCristopolis.spec` e `BackupBiblioteca.spec` | Configuração do PyInstaller para gerar o executável do sistema e o do backup (seção 10). |
| `restaurar_drive.py` | Baixa um backup do Drive, descriptografa e verifica o banco recuperado. |
| `testar_restauracao.py` | Teste local de restauração e integridade. |
| `verificar_dados_restaurados.py` | Compara a quantidade de registros do banco original com a cópia recuperada. |

### 2.1 Onde ficam os dados

O `caminhos.py` escolhe a pasta de dados conforme a forma de execução:

| Item | Com Python (`python main.py`) | Pelo executável |
| --- | --- | --- |
| Banco | `data/biblioteca.db`, na pasta do projeto | `%LOCALAPPDATA%\BibliotecaCristopolis\data\biblioteca.db` |
| Backups, controle de envios e chave | `data/backups/`, `data/controle_backups.json`, `data/chave_backup.key` | as mesmas pastas e arquivos, dentro de `%LOCALAPPDATA%\BibliotecaCristopolis\data\` |
| `client_secret.json` e `token.json` | raiz do projeto | `%LOCALAPPDATA%\BibliotecaCristopolis\` (uma pasta acima de `data`) |

Duas consequências importantes:

- **O executável não usa o banco do projeto.** Quem passar do `python main.py` para o executável começa com o banco vazio e precisa copiar o `biblioteca.db` e a chave original para a pasta do executável (seção 10).
- **Alguns scripts ainda usam só a pasta do projeto.** `executar_backup.bat`, `restaurar_drive.py`, `testar_restauracao.py` e `verificar_dados_restaurados.py` continuam apontando para `data/` dentro do projeto. O `redefinir_senha.py` usa o caminho do `caminhos.py`, que no uso com Python também é a pasta do projeto. Eles servem para o ambiente com Python.

### Arquivos locais que **não** devem ir para o GitHub

- `client_secret*.json`: credenciais OAuth do aplicativo Google Cloud.
- `token*.json`: token OAuth autorizado para a conta do Google Drive.
- `data/chave_backup.key` (ou qualquer `*.key`): chave secreta Fernet usada para descriptografar os backups.
- `data/biblioteca.db`, `data/backups/`, `data/teste_restauracao/` e qualquer `*.db.enc`: banco e cópias locais.
- `data/controle_backups.json`, `data/controle_backups.tmp`: controle local de envios.
- `data/logs/`: registros de execução.
- `build/`, `dist/` e `*.exe`: arquivos gerados pelo PyInstaller.

Esses caminhos constam no `.gitignore`. **O `.gitignore` não remove segredos que já tenham sido commitados**: antes de publicar, confira também os arquivos rastreados pelo Git.

## 3. Dependências e serviços

| Tecnologia | Uso |
| --- | --- |
| Python 3.12 (ambiente testado) | Execução dos scripts. |
| SQLite / `sqlite3` (biblioteca padrão) | Banco de dados, backup e integridade. |
| `cryptography` (Fernet) | Criptografia e descriptografia. |
| `google-api-python-client` | Operações com arquivos na API do Google Drive. |
| `google-auth` | Credenciais e renovação de tokens. |
| `google-auth-oauthlib` | Autorização OAuth no navegador. |
| Google Drive API v3 | Armazenamento remoto dos backups criptografados. |
| Agendador de Tarefas do Windows | Execução diária às 16h30 no computador de teste. |
| PyInstaller | Só para gerar o executável. Não está no `requirements.txt`; instale com `pip install pyinstaller` quando for gerar. |

Instale as dependências no ambiente virtual do projeto. **Consulte o `requirements.txt` existente e atualize-o** com as bibliotecas realmente utilizadas; não substitua as dependências atuais do sistema por esta lista. Exemplo de instalação das bibliotecas específicas de backup:

```bash
python -m pip install cryptography google-api-python-client google-auth google-auth-oauthlib
```

As versões efetivas devem ser registradas a partir do ambiente de desenvolvimento e testadas em uma instalação limpa.

## 4. Preparação de um novo computador

1. Clone o repositório e crie/ative um ambiente virtual Python.
2. Instale as dependências da aplicação e as bibliotecas indicadas na seção anterior.
3. Configure o banco SQLite da instalação conforme o procedimento do projeto. **Não substitua o banco existente sem antes fazer uma cópia segura.**
4. No Google Cloud, habilite a **Google Drive API**, configure a tela de consentimento OAuth e um cliente OAuth do tipo **aplicativo para computador**. Baixe o arquivo de credenciais e coloque-o com o nome esperado pelo script (`client_secret.json`), na raiz do projeto (com Python) ou em `%LOCALAPPDATA%\BibliotecaCristopolis\` (executável). Não o versione.
5. Autorize a conta do Google Drive na primeira execução interativa. O `drive_backup.py` usa o escopo `https://www.googleapis.com/auth/drive.file` e salva o token localmente em `token.json`, ao lado do `client_secret.json`.
6. **Defina a pasta do Google Drive que vai receber os backups.** Crie a pasta no Drive da conta autorizada e copie o ID, que é o trecho final do endereço (`https://drive.google.com/drive/folders/ID_DA_PASTA`). Guarde o ID na variável de ambiente `BIBLIOTECA_DRIVE_FOLDER_ID` do usuário que executa o backup:

   ```bash
   setx BIBLIOTECA_DRIVE_FOLDER_ID "ID_DA_PASTA"
   ```

   O `setx` só vale para programas abertos depois dele, então abra um novo terminal. **Sem essa variável o envio é recusado** com a mensagem "A pasta de backup do Google Drive não foi configurada": o backup local criptografado é criado e fica pendente em `data/backups/`, a execução termina com falha e o envio é tentado de novo na execução seguinte. Se o Drive recusar a pasta, o erro aparece no log, e o arquivo também fica pendente.
7. Configure a chave Fernet. **Se for uma instalação nova sem backups anteriores**, gere uma chave seguindo o fluxo previsto em `criptografia.py` e faça cópia segura fora do computador. **Se for recuperar backups antigos, use a chave original correspondente a esses backups; nunca gere outra chave para tentar abri-los.**
8. Execute um backup manual e confirme que o arquivo aparece **dentro da pasta indicada** no Drive antes de criar o agendamento. Depois de criar a tarefa, rode-a uma vez pelo Agendador e confirme que ela enxerga a variável, porque uma tarefa que não a encontra falha no envio.

**Atenção ao OAuth:** o fluxo inicial pode abrir um navegador. Uma tarefa agendada sem usuário presente não deve depender dessa autorização interativa; faça a autorização previamente e valide a renovação do token no ambiente de implantação.

## 5. Execução manual e automática

Na raiz do projeto, com o ambiente virtual ativo:

```bash
python drive_backup.py
```

No Git Bash, para testar o arquivo `.bat` do Windows:

```bash
cmd.exe //c executar_backup.bat
```

O arquivo `.bat` usa o Python em `venv\Scripts\python.exe` e registra a saída em `data/logs/backup.log`. Se o ambiente virtual tiver outro nome (o README usa `.venv`), ajuste o `.bat` antes de agendar.

Com o executável, a tarefa chama o `BackupBiblioteca.exe` direto (seção 10). Ele só escreve na tela, então, para ter um log, redirecione a saída na própria tarefa, como no `.bat`.

### Agendamento no Windows

No **Agendador de Tarefas** (`taskschd.msc`), crie uma tarefa com:

- **Disparador:** diariamente às **16h30** (horário da máquina; alterável).
- **Programa:** `C:\Windows\System32\cmd.exe`.
- **Argumentos:** `/c "CAMINHO_ABSOLUTO_DO_PROJETO\executar_backup.bat"`.
- **Iniciar em:** `CAMINHO_ABSOLUTO_DO_PROJETO` (sem aspas).
- **Configurações recomendadas:** executar assim que possível se o horário for perdido; não iniciar segunda instância se já estiver executando; definir tentativas de reinício em caso de falha.

O computador deve estar ligado ou configurado para despertar da suspensão; a tarefa não liga uma máquina completamente desligada. A configuração do Agendador **não é transferida pelo Git** e precisa ser refeita em outro computador.

### Como conferir a execução

1. No Agendador, veja **Última Execução** e **Resultado da Última Execução** (`0x0` indica sucesso do processo perante o Windows).
2. Confira o trecho mais recente de `data/logs/backup.log`, especialmente `Processo de backup finalizado com sucesso.` e `Resultado: CONCLUIDO`.
3. Confirme que o arquivo `.db.enc` correspondente aparece no Google Drive.

**Importante:** a mensagem `CONCLUIDO` não substitui a conferência periódica dos arquivos remotos e de sua capacidade de restauração.

## 6. Falhas de internet e retenção

Se o Google Drive estiver indisponível, o arquivo `.db.enc` permanece em `data/backups/`. A execução registra falha, e a próxima execução tenta enviar novamente os arquivos não registrados como enviados.

Após envios bem-sucedidos, o sistema mantém **até sete backups locais criptografados que já constam no controle de envios**. Arquivos pendentes não são excluídos pela rotina de retenção. Essa política **não apaga arquivos antigos do Google Drive**; a retenção remota deve ser avaliada separadamente.

O controle de envios fica em `data/controle_backups.json`. Não o apague: sua perda pode fazer o programa tentar reenviar backups já existentes, criando duplicatas no Drive. A implementação atual não é um mecanismo de deduplicação remota.

## 7. Restauração segura

**Não execute a restauração diretamente sobre `data/biblioteca.db` enquanto o sistema estiver em uso.**

1. Identifique o arquivo de backup desejado no Google Drive e confirme que a chave Fernet correspondente está disponível.
2. Faça uma cópia de segurança do banco atual, se existir, e feche a aplicação.
3. Execute o script de teste:

   ```bash
   python restaurar_drive.py
   ```

4. O script baixa o arquivo `.db.enc` para `data/teste_restauracao/`, descriptografa e verifica a integridade SQLite. **Confira o código de `restaurar_drive.py` antes da execução:** a versão testada seleciona um arquivo do Drive por ID definido no script, portanto pode ser necessário atualizar esse ID para o backup desejado.
5. Confira as tabelas e, se for útil, execute:

   ```bash
   python verificar_dados_restaurados.py
   ```

6. Valide os dados relevantes e o funcionamento da aplicação usando **uma cópia** do banco recuperado. A substituição definitiva do banco de produção deve seguir um procedimento de manutenção, com aplicativo fechado e possibilidade de reversão.

A comparação de **quantidade de registros** não comprova, por si só, igualdade do conteúdo. Para validação mais rigorosa, compare registros e/ou hashes de bancos que deveriam ser idênticos.

## 8. Testes realizados (outubro de 2026)

- Criação de backup SQLite e verificação de integridade: **aprovadas**.
- Criptografia Fernet, download e descriptografia: **aprovados**.
- Upload ao Google Drive: **aprovado**.
- Falha simulada de internet: backup ficou pendente; após reconexão, os arquivos pendentes foram enviados: **aprovado**.
- Retenção local dos arquivos já enviados: **observada em funcionamento**.
- Restauração de arquivo do Drive: integridade SQLite `OK`, seis tabelas encontradas: **aprovada**.
- Contagem de registros original versus recuperado: **20 versus 20** (2 categorias, 10 livros, 2 usuários, 6 empréstimos, 0 reservas, 0 funcionários).
- Execução pelo Agendador do Windows: disparo automático confirmado às **16h30 de 23/10/2026**, com log `CONCLUIDO`.

### Validações recomendadas antes do uso definitivo

- Restaurar em **outro computador ou instalação limpa**.
- Validar a renovação do token OAuth em execução não interativa.
- Confirmar que a chave de criptografia está guardada em local seguro, acessível apenas aos responsáveis autorizados.
- Comparar dados de forma mais rigorosa do que apenas contagem de registros.
- Definir política de retenção e limpeza dos arquivos antigos **no Google Drive**.
- Rever o script de restauração para selecionar o backup desejado sem editar um ID fixo no código.
- Confirmar, em cada computador, o envio à pasta definida em `BIBLIOTECA_DRIVE_FOLDER_ID`, inclusive pela tarefa agendada (esta verificação não consta nos testes de outubro, que foram feitos antes dessa variável existir).
- Gerar o executável, instalá-lo em um computador limpo e conferir abertura, banco, backup e restauração com ele (seção 10).

## 9. Cuidados de segurança e operação

- **Nunca** publique `client_secret*.json`, `token.json`, `data/chave_backup.key`, bancos ou logs com informações sensíveis.
- Não substitua a chave de criptografia: sem a chave original, backups antigos não poderão ser descriptografados.
- Restrinja o acesso à conta Google utilizada e ao computador que executa os backups.
- O escopo OAuth `drive.file` limita o acesso da aplicação aos arquivos permitidos por esse escopo; não representa acesso irrestrito a todo o Drive.
- A criptografia protege o conteúdo dos arquivos `.db.enc`, mas o banco ativo `data/biblioteca.db` permanece sem essa criptografia adicional; proteja também o computador e suas permissões.
- O histórico do Git e os arquivos locais devem ser revisados antes de qualquer publicação pública.
- O servidor local do sistema (Flask) aceita conexões só do próprio computador (`127.0.0.1`, porta 5000), sem modo de depuração e sem recarregamento automático. Outros computadores da rede não conseguem abrir o sistema.

## 10. Executável para Windows (PyInstaller)

O repositório tem os arquivos `BibliotecaCristopolis.spec` (o sistema, com a janela) e `BackupBiblioteca.spec` (o backup) para gerar executáveis que rodam sem o Python instalado. Os dois arquivos vêm da preparação feita em 30/10/2026; **a geração e a instalação em um computador limpo ainda precisam ser validadas** (seção 8).

Para gerar, no ambiente virtual do projeto:

```bash
pip install pyinstaller
pyinstaller BibliotecaCristopolis.spec
pyinstaller BackupBiblioteca.spec
```

Os resultados ficam em `dist/BibliotecaCristopolis/` e `dist/BackupBiblioteca/`. As pastas `build/` e `dist/` e os arquivos `.exe` não vão para o GitHub. O `BibliotecaCristopolis.spec` inclui junto os modelos de página, os arquivos estáticos e o `schema.sql`.

Para instalar em um computador:

1. Copie as duas pastas de `dist/` para o computador.
2. Se for manter os dados atuais, copie o `biblioteca.db` e a `chave_backup.key` para `%LOCALAPPDATA%\BibliotecaCristopolis\data\` **antes** de abrir o sistema pela primeira vez. Sem isso, o executável cria um banco vazio.
3. Coloque o `client_secret.json` em `%LOCALAPPDATA%\BibliotecaCristopolis\` e rode o `BackupBiblioteca.exe` uma vez para autorizar o Google (gera o `token.json`).
4. Defina `BIBLIOTECA_DRIVE_FOLDER_ID` (seção 4, passo 6).
5. Crie a tarefa agendada apontando para o `BackupBiblioteca.exe` e confira o envio.

Limitações conhecidas do executável:

- Os dois `.spec` estão com `console=True`, então abrem com uma janela de console preta junto com o sistema.
- Não há versão executável do `redefinir_senha.py`. Para redefinir a senha de uma instalação feita só com o executável é preciso ter o Python e apontar o script para a pasta de dados do executável.
- Os scripts de restauração e verificação (seção 2.1) usam a pasta `data/` do projeto, não a do executável.
- A localização dos dados muda em relação ao uso com Python, o que afeta cópia de segurança manual e mudança de computador.

## 11. Referência rápida para a equipe

```bash
# Executar backup
python drive_backup.py

# Testar restauração (não substitui o banco de produção)
python restaurar_drive.py

# Comparar contagens de registros
python verificar_dados_restaurados.py

# Conferir arquivos preparados para commit
git diff --cached --name-only
git diff --cached --check
```

### Atualização do README.md

Adicionar uma referência na seção de documentação do projeto:

```markdown
### Backup e recuperação

O sistema possui backups criptografados do banco SQLite, envio ao Google Drive,
reenvio de arquivos pendentes e execução agendada no Windows.

Consulte o [manual técnico de backup e restauração](docs/BACKUP_E_RESTAURACAO.md)
para conhecer as dependências, configuração, segurança, testes e recuperação.
```

---

**Manutenção deste documento:** sempre que mudar a API, as dependências, os nomes dos scripts, o formato dos backups ou o procedimento de restauração, atualize este manual e o `requirements.txt` correspondente.