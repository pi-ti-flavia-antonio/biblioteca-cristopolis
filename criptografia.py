
from pathlib import Path
from cryptography.fernet import Fernet

from caminhos import pasta_dados

ARQUIVO_CHAVE = pasta_dados() / "chave_backup.key"


def gerar_chave():
    if ARQUIVO_CHAVE.exists():
        raise FileExistsError(
            "Já existe uma chave de criptografia. "
            "Ela não deve ser substituída."
        )

    ARQUIVO_CHAVE.parent.mkdir(parents=True, exist_ok=True)

    chave = Fernet.generate_key()

    with ARQUIVO_CHAVE.open("xb") as arquivo:
        arquivo.write(chave)

    print("Chave de criptografia criada com sucesso!")
    print("Guarde uma cópia segura dessa chave.")


def carregar_chave():
    if not ARQUIVO_CHAVE.is_file():
        raise FileNotFoundError(
            "Chave de criptografia não encontrada. "
            "Não é possível criptografar ou restaurar backups."
        )

    return ARQUIVO_CHAVE.read_bytes()


def criptografar_backup(caminho_backup):
    caminho_backup = Path(caminho_backup)

    if not caminho_backup.is_file():
        raise FileNotFoundError("Arquivo de backup não encontrado.")

    chave = carregar_chave()
    fernet = Fernet(chave)

    caminho_criptografado = caminho_backup.with_suffix(".db.enc")

    dados = caminho_backup.read_bytes()
    dados_criptografados = fernet.encrypt(dados)

    caminho_criptografado.write_bytes(dados_criptografados)

    print("Backup criptografado com sucesso!")
    print(f"Arquivo: {caminho_criptografado}")

    return caminho_criptografado


def descriptografar_backup(caminho_criptografado, destino):
    caminho_criptografado = Path(caminho_criptografado)
    destino = Path(destino)

    chave = carregar_chave()
    fernet = Fernet(chave)

    dados_criptografados = caminho_criptografado.read_bytes()
    dados = fernet.decrypt(dados_criptografados)

    if destino.exists():
        raise FileExistsError(
            "O arquivo de destino já existe. "
            "Escolha outro caminho para evitar sobrescrita."
        )

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(dados)

    print("Backup descriptografado com sucesso!")
    return destino


if __name__ == "__main__":
    gerar_chave()
