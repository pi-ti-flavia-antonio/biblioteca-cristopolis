"""Testes do backup: cópia íntegra, criptografia, envio ao Drive (simulado), pendências e restauração.

Os módulos do backup guardam os caminhos em variáveis do módulo. Aqui cada teste troca esses caminhos
por uma pasta temporária e usa uma chave nova, então nada toca no banco, na chave nem no Drive de verdade.
"""

import json
import sqlite3
from contextlib import closing

import pytest
from cryptography.fernet import Fernet, InvalidToken

import backup
import controle_backups
import criptografia
import drive_backup
from app import create_app
from app.database import get_db

TABELAS = ["categoria", "livro", "usuario", "emprestimo", "reserva", "funcionario"]


def contar_registros(caminho):
    with closing(sqlite3.connect(caminho)) as con:
        return {tabela: con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0] for tabela in TABELAS}


class DriveFalso:
    """Imita o que o programa usa do Google Drive: files().create(...).execute()."""

    def __init__(self, falhar_em=()):
        self.enviados = []
        self.falhar_em = set(falhar_em)

    def files(self):
        return self

    def create(self, body, media_body, fields):
        self._nome = body["name"]
        self._pasta = body.get("parents")
        return self

    def execute(self):
        if self._nome in self.falhar_em:
            raise OSError("sem internet")
        self.enviados.append((self._nome, self._pasta))
        return {"id": f"id-{self._nome}", "name": self._nome}


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """Banco com alguns dados, pasta de backups, chave e controle em pasta temporária."""
    banco = tmp_path / "biblioteca.db"
    app = create_app({"TESTING": True, "DATABASE": banco, "SECRET_KEY": "teste"})
    with app.app_context():
        db = get_db()
        with db:
            db.execute("INSERT INTO categoria (nome) VALUES ('Romance')")
            db.execute("INSERT INTO livro (titulo, autor, quantidade_total, id_categoria) VALUES ('Dom Casmurro', 'Machado de Assis', 2, 1)")
            db.execute("INSERT INTO usuario (nome, telefone, endereco) VALUES ('Maria Teste', '77999990000', 'Rua A, 1')")
            db.execute("INSERT INTO funcionario (nome, login, senha_hash) VALUES ('Func', 'func', 'x')")

    chave = tmp_path / "chave_backup.key"
    chave.write_bytes(Fernet.generate_key())
    pasta = tmp_path / "backups"

    monkeypatch.setattr(backup, "BANCO_ORIGINAL", banco)
    monkeypatch.setattr(backup, "PASTA_BACKUPS", pasta)
    monkeypatch.setattr(criptografia, "ARQUIVO_CHAVE", chave)
    monkeypatch.setattr(controle_backups, "ARQUIVO_CONTROLE", tmp_path / "controle_backups.json")
    monkeypatch.setattr(drive_backup, "ID_PASTA_BACKUP", "pasta-de-teste")
    return {"banco": banco, "pasta": pasta, "chave": chave, "tmp": tmp_path}


def _drive(monkeypatch, drive):
    monkeypatch.setattr(drive_backup, "conectar_google_drive", lambda: drive)


def _sem_internet(monkeypatch):
    def falhar():
        raise OSError("sem internet")

    monkeypatch.setattr(drive_backup, "conectar_google_drive", falhar)


def _nomes(pasta, padrao):
    return sorted(arquivo.name for arquivo in pasta.glob(padrao))


# Cópia do banco


def test_backup_copia_o_banco_com_os_mesmos_dados(ambiente):
    arquivo = backup.criar_backup()

    assert arquivo.is_file() and arquivo.parent == ambiente["pasta"]
    assert contar_registros(arquivo) == contar_registros(ambiente["banco"])
    assert contar_registros(arquivo)["livro"] == 1


def test_backup_nao_altera_o_banco_original(ambiente):
    antes = contar_registros(ambiente["banco"])

    backup.criar_backup()

    assert contar_registros(ambiente["banco"]) == antes


def test_backup_passa_na_verificacao_de_integridade(ambiente):
    arquivo = backup.criar_backup()

    with closing(sqlite3.connect(arquivo)) as con:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_backup_sem_banco_avisa_e_nao_deixa_arquivo(ambiente, monkeypatch):
    monkeypatch.setattr(backup, "BANCO_ORIGINAL", ambiente["tmp"] / "nao_existe.db")

    with pytest.raises(FileNotFoundError):
        backup.criar_backup()

    assert not ambiente["pasta"].exists() or list(ambiente["pasta"].iterdir()) == []


def test_backup_com_falha_de_integridade_apaga_a_copia(ambiente, monkeypatch):
    class ConexaoFalsa:
        def __init__(self, real):
            self.real = real

        def execute(self, sql, *args):
            if "integrity_check" in sql:
                return type("R", (), {"fetchone": lambda _: ("corrompido",)})()
            return self.real.execute(sql, *args)

        def __getattr__(self, nome):
            return getattr(self.real, nome)

    original = sqlite3.connect
    conexoes = []

    def conectar(*args, **kwargs):
        conexoes.append(1)
        real = original(*args, **kwargs)
        # As duas primeiras conexões fazem a cópia; a terceira confere a integridade.
        return ConexaoFalsa(real) if len(conexoes) == 3 else real

    monkeypatch.setattr(backup.sqlite3, "connect", conectar)

    with pytest.raises(RuntimeError, match="verificação"):
        backup.criar_backup()

    assert list(ambiente["pasta"].glob("*.db")) == []


# Criptografia


def test_criptografia_esconde_o_conteudo_do_banco(ambiente):
    arquivo = backup.criar_backup()

    criptografado = criptografia.criptografar_backup(arquivo)

    bytes_cifrados = criptografado.read_bytes()
    assert criptografado.name.endswith(".db.enc")
    assert b"SQLite format 3" not in bytes_cifrados
    assert b"Maria Teste" not in bytes_cifrados
    assert b"Dom Casmurro" not in bytes_cifrados


def test_descriptografar_devolve_o_mesmo_banco(ambiente):
    arquivo = backup.criar_backup()
    criptografado = criptografia.criptografar_backup(arquivo)

    recuperado = criptografia.descriptografar_backup(criptografado, ambiente["tmp"] / "recuperado.db")

    assert recuperado.read_bytes() == arquivo.read_bytes()
    assert contar_registros(recuperado) == contar_registros(ambiente["banco"])


def test_chave_errada_e_recusada(ambiente):
    criptografado = criptografia.criptografar_backup(backup.criar_backup())
    ambiente["chave"].write_bytes(Fernet.generate_key())

    with pytest.raises(InvalidToken):
        criptografia.descriptografar_backup(criptografado, ambiente["tmp"] / "recuperado.db")

    assert not (ambiente["tmp"] / "recuperado.db").exists()


def test_arquivo_adulterado_e_recusado(ambiente):
    criptografado = criptografia.criptografar_backup(backup.criar_backup())
    dados = bytearray(criptografado.read_bytes())
    dados[len(dados) // 2] ^= 0xFF
    criptografado.write_bytes(bytes(dados))

    with pytest.raises(InvalidToken):
        criptografia.descriptografar_backup(criptografado, ambiente["tmp"] / "recuperado.db")


def test_descriptografar_nao_sobrescreve_arquivo_existente(ambiente):
    criptografado = criptografia.criptografar_backup(backup.criar_backup())
    destino = ambiente["tmp"] / "recuperado.db"
    destino.write_bytes(b"importante")

    with pytest.raises(FileExistsError):
        criptografia.descriptografar_backup(criptografado, destino)

    assert destino.read_bytes() == b"importante"


def test_sem_chave_nao_criptografa(ambiente):
    arquivo = backup.criar_backup()
    ambiente["chave"].unlink()

    with pytest.raises(FileNotFoundError):
        criptografia.criptografar_backup(arquivo)


def test_criptografar_arquivo_que_nao_existe(ambiente):
    with pytest.raises(FileNotFoundError):
        criptografia.criptografar_backup(ambiente["tmp"] / "nao_existe.db")


def test_chave_existente_nao_e_substituida(ambiente):
    antes = ambiente["chave"].read_bytes()

    with pytest.raises(FileExistsError):
        criptografia.gerar_chave()

    assert ambiente["chave"].read_bytes() == antes


def test_gerar_chave_cria_chave_valida(ambiente):
    ambiente["chave"].unlink()

    criptografia.gerar_chave()

    Fernet(ambiente["chave"].read_bytes())  # levanta erro se a chave não for válida


# Controle dos envios


def test_controle_registra_e_lembra_o_envio(ambiente):
    assert not controle_backups.ja_enviado("biblioteca_1.db.enc")

    controle_backups.registrar_envio("biblioteca_1.db.enc", "id-1")

    assert controle_backups.ja_enviado("biblioteca_1.db.enc")
    assert not controle_backups.ja_enviado("biblioteca_2.db.enc")


def test_controle_nao_deixa_arquivo_temporario(ambiente):
    controle_backups.registrar_envio("biblioteca_1.db.enc", "id-1")

    assert [arquivo.name for arquivo in ambiente["tmp"].glob("controle_backups*")] == ["controle_backups.json"]


def test_controle_com_formato_invalido_e_recusado(ambiente):
    (ambiente["tmp"] / "controle_backups.json").write_text(json.dumps(["nao", "e", "dicionario"]))

    with pytest.raises(ValueError):
        controle_backups.carregar_controle()


def test_retencao_mantem_7_enviados_e_nunca_apaga_pendentes(ambiente):
    pasta = ambiente["pasta"]
    pasta.mkdir()
    for dia in range(1, 11):
        nome = f"biblioteca_2026-10-{dia:02d}_16-30-00.db.enc"
        (pasta / nome).write_bytes(b"x")
        if dia != 9:  # o dia 9 ficou pendente
            controle_backups.registrar_envio(nome, f"id-{dia}")

    controle_backups.limpar_backups_antigos(pasta, manter=7)

    restantes = _nomes(pasta, "biblioteca_*.db.enc")
    assert "biblioteca_2026-10-09_16-30-00.db.enc" in restantes
    enviados_que_ficaram = [n for n in restantes if n != "biblioteca_2026-10-09_16-30-00.db.enc"]
    # Dos 9 enviados ficam os 7 mais recentes (dias 3 a 8 e 10); saem os dias 1 e 2.
    assert enviados_que_ficaram == [f"biblioteca_2026-10-{dia:02d}_16-30-00.db.enc" for dia in (3, 4, 5, 6, 7, 8, 10)]


# Envio ao Drive


def test_envio_manda_o_arquivo_para_a_pasta_configurada(ambiente):
    criptografado = criptografia.criptografar_backup(backup.criar_backup())
    drive = DriveFalso()

    resultado = drive_backup.enviar_backup(drive, criptografado)

    assert resultado["id"] == f"id-{criptografado.name}"
    assert drive.enviados == [(criptografado.name, ["pasta-de-teste"])]


def test_envio_sem_pasta_configurada_avisa(ambiente, monkeypatch):
    criptografado = criptografia.criptografar_backup(backup.criar_backup())
    monkeypatch.setattr(drive_backup, "ID_PASTA_BACKUP", None)

    with pytest.raises(RuntimeError, match="pasta de backup"):
        drive_backup.enviar_backup(DriveFalso(), criptografado)


def test_envio_de_arquivo_que_nao_existe(ambiente):
    with pytest.raises(FileNotFoundError):
        drive_backup.enviar_backup(DriveFalso(), ambiente["tmp"] / "nao_existe.db.enc")


# Execução completa do backup


def test_execucao_cria_criptografa_envia_e_nao_deixa_copia_aberta(ambiente, monkeypatch):
    drive = DriveFalso()
    _drive(monkeypatch, drive)

    drive_backup.executar()

    assert len(_nomes(ambiente["pasta"], "biblioteca_*.db.enc")) == 1
    assert _nomes(ambiente["pasta"], "biblioteca_*.db") == []  # a cópia sem criptografia foi apagada
    assert len(drive.enviados) == 1
    assert controle_backups.ja_enviado(drive.enviados[0][0])


def test_sem_internet_o_arquivo_fica_pendente_e_a_execucao_falha(ambiente, monkeypatch):
    _sem_internet(monkeypatch)

    with pytest.raises(SystemExit) as saida:
        drive_backup.executar()

    assert saida.value.code == 1
    pendentes = _nomes(ambiente["pasta"], "biblioteca_*.db.enc")
    assert len(pendentes) == 1
    assert not controle_backups.ja_enviado(pendentes[0])
    assert _nomes(ambiente["pasta"], "biblioteca_*.db") == []


def test_pendente_sai_na_execucao_seguinte(ambiente, monkeypatch):
    _sem_internet(monkeypatch)
    with pytest.raises(SystemExit):
        drive_backup.executar()
    pendente = _nomes(ambiente["pasta"], "biblioteca_*.db.enc")[0]
    # Os nomes têm segundos: a segunda execução precisa de um nome diferente.
    segundo = ambiente["pasta"] / "biblioteca_9999-01-01_00-00-00.db"
    monkeypatch.setattr(backup, "criar_backup", lambda: _copiar_como(ambiente["banco"], segundo))
    drive = DriveFalso()
    _drive(monkeypatch, drive)

    drive_backup.executar()

    enviados = sorted(nome for nome, _ in drive.enviados)
    assert enviados == sorted([pendente, "biblioteca_9999-01-01_00-00-00.db.enc"])
    assert all(controle_backups.ja_enviado(nome) for nome in enviados)


def _copiar_como(origem, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(origem)) as de, closing(sqlite3.connect(destino)) as para:
        de.backup(para)
    return destino


def test_falha_no_envio_de_um_arquivo_mantem_ele_para_nova_tentativa(ambiente, monkeypatch):
    drive = DriveFalso()
    _drive(monkeypatch, drive)
    nome = None

    def criar_com_nome_fixo():
        return _copiar_como(ambiente["banco"], ambiente["pasta"] / "biblioteca_2026-11-01_16-30-00.db")

    monkeypatch.setattr(backup, "criar_backup", criar_com_nome_fixo)
    drive.falhar_em = {"biblioteca_2026-11-01_16-30-00.db.enc"}

    with pytest.raises(SystemExit):
        drive_backup.executar()

    nome = "biblioteca_2026-11-01_16-30-00.db.enc"
    assert (ambiente["pasta"] / nome).is_file()
    assert not controle_backups.ja_enviado(nome)


def test_falha_na_criptografia_nao_envia_nada_e_mantem_a_copia(ambiente, monkeypatch):
    # Sem a chave o backup não é criptografado. O arquivo em claro continua na pasta,
    # para a pessoa responsável perceber, e nada é enviado ao Drive.
    ambiente["chave"].unlink()
    drive = DriveFalso()
    _drive(monkeypatch, drive)

    with pytest.raises(FileNotFoundError):
        drive_backup.executar()

    assert drive.enviados == []
    assert _nomes(ambiente["pasta"], "biblioteca_*.db.enc") == []
    assert len(_nomes(ambiente["pasta"], "biblioteca_*.db")) == 1


# Restauração


def test_restauracao_devolve_as_mesmas_quantidades(ambiente, monkeypatch):
    drive = DriveFalso()
    _drive(monkeypatch, drive)
    drive_backup.executar()
    criptografado = ambiente["pasta"] / drive.enviados[0][0]

    recuperado = criptografia.descriptografar_backup(criptografado, ambiente["tmp"] / "recuperado.db")

    assert contar_registros(recuperado) == contar_registros(ambiente["banco"])
    with closing(sqlite3.connect(f"file:{recuperado.as_posix()}?mode=ro", uri=True)) as con:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_restauracao_guarda_o_que_foi_feito_depois_do_backup_de_fora(ambiente, monkeypatch):
    drive = DriveFalso()
    _drive(monkeypatch, drive)
    drive_backup.executar()
    with closing(sqlite3.connect(ambiente["banco"])) as con, con:
        con.execute("INSERT INTO usuario (nome, telefone, endereco) VALUES ('Depois', '77999990001', 'Rua B, 2')")

    recuperado = criptografia.descriptografar_backup(
        ambiente["pasta"] / drive.enviados[0][0], ambiente["tmp"] / "recuperado.db"
    )

    assert contar_registros(recuperado)["usuario"] == 1
    assert contar_registros(ambiente["banco"])["usuario"] == 2
