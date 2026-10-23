    # Backup e restauração — Biblioteca Municipal de Cristópolis

> Documentação técnica para a equipe de desenvolvimento e para a implantação.
> Estado: implementação e testes locais realizados em outubro de 2026.
> **Atenção:** este repositório não contém credenciais, chave de criptografia, banco de dados nem configuração do Agendador de Tarefas.

## 1. Objetivo e visão geral

Proteger o banco SQLite da aplicação (`data/biblioteca.db`) contra perda de dados, mantendo cópias locais criptografadas e enviando-as ao Google Drive. O sistema funciona em computador Windows, com execução agendada por um arquivo `.bat`.

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
drive_backup.py -> autenticação OAuth -> Google Drive
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
| `backup.py` | Cria cópia do SQLite e verifica a integridade. |
| `criptografia.py` | Gera/carrega a chave Fernet, criptografa e descriptografa backups. |
| `drive_backup.py` | Orquestra criação, criptografia, envio, registro, retenção e sinalização de falhas. |
| `controle_backups.py` | Mantém o controle local dos nomes e IDs de arquivos enviados; remove cópias locais antigas já enviadas. |
| `executar_backup.bat` | Executa o script com o Python do ambiente virtual e registra saída em log. |
| `restaurar_drive.py` | Baixa um backup do Drive, descriptografa e verifica o banco recuperado. |
| `testar_restauracao.py` | Teste local de restauração e integridade. |
| `verificar_dados_restaurados.py` | Compara a quantidade de registros do banco original com a cópia recuperada. |

### Arquivos locais que **não** devem ir para o GitHub

- `client_secret*.json`: credenciais OAuth do aplicativo Google Cloud.
- `token.json`: token OAuth autorizado para a conta do Google Drive.
- `data/chave_backup.key`: chave secreta Fernet usada para descriptografar os backups.
- `data/biblioteca.db`, `data/backups/`, `data/teste_restauracao/`: banco e cópias locais.
- `data/controle_backups.json`, `data/controle_backups.tmp`: controle local de envios.
- `data/logs/`: registros de execução.

Esses caminhos devem constar no `.gitignore`. **O `.gitignore` não remove segredos que já tenham sido commitados**: antes de publicar, confira também os arquivos rastreados pelo Git.

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

Instale as dependências no ambiente virtual do projeto. **Consulte o `requirements.txt` existente e atualize-o** com as bibliotecas realmente utilizadas; não substitua as dependências atuais do sistema por esta lista. Exemplo de instalação das bibliotecas específicas de backup:

```bash
python -m pip install cryptography google-api-python-client google-auth google-auth-oauthlib
```

As versões efetivas devem ser registradas a partir do ambiente de desenvolvimento e testadas em uma instalação limpa.

## 4. Preparação de um novo computador

1. Clone o repositório e crie/ative um ambiente virtual Python.
2. Instale as dependências da aplicação e as bibliotecas indicadas na seção anterior.
3. Configure o banco SQLite da instalação conforme o procedimento do projeto. **Não substitua o banco existente sem antes fazer uma cópia segura.**
4. No Google Cloud, habilite a **Google Drive API**, configure a tela de consentimento OAuth e um cliente OAuth do tipo **aplicativo para computador**. Baixe o arquivo de credenciais e coloque-o na raiz do projeto com o nome esperado pelo script (`client_secret.json`). Não o versione.
5. Autorize a conta do Google Drive na primeira execução interativa. O `drive_backup.py` usa o escopo `https://www.googleapis.com/auth/drive.file` e salva o token localmente em `token.json`.
6. Configure a chave Fernet. **Se for uma instalação nova sem backups anteriores**, gere uma chave seguindo o fluxo previsto em `criptografia.py` e faça cópia segura fora do computador. **Se for recuperar backups antigos, use a chave original correspondente a esses backups; nunca gere outra chave para tentar abri-los.**
7. Execute um backup manual e confirme o envio ao Drive antes de criar o agendamento.

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

O arquivo `.bat` usa o Python em `venv\Scripts\python.exe` e registra a saída em `data/logs/backup.log`. Se o ambiente virtual tiver outro nome, ajuste o `.bat` antes de agendar.

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

## 9. Cuidados de segurança e operação

- **Nunca** publique `client_secret*.json`, `token.json`, `data/chave_backup.key`, bancos ou logs com informações sensíveis.
- Não substitua a chave de criptografia: sem a chave original, backups antigos não poderão ser descriptografados.
- Restrinja o acesso à conta Google utilizada e ao computador que executa os backups.
- O escopo OAuth `drive.file` limita o acesso da aplicação aos arquivos permitidos por esse escopo; não representa acesso irrestrito a todo o Drive.
- A criptografia protege o conteúdo dos arquivos `.db.enc`, mas o banco ativo `data/biblioteca.db` permanece sem essa criptografia adicional; proteja também o computador e suas permissões.
- O histórico do Git e os arquivos locais devem ser revisados antes de qualquer publicação pública.

## 10. Referência rápida para a equipe

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