
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_CONTROLE = (
    BASE_DIR / "data" / "controle_backups.json"
)


def carregar_controle():
    if not ARQUIVO_CONTROLE.exists():
        return {}

    with ARQUIVO_CONTROLE.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    if not isinstance(dados, dict):
        raise ValueError("Formato inválido do controle de backups.")

    return dados


def registrar_envio(nome_arquivo, id_drive):
    controle = carregar_controle()

    controle[nome_arquivo] = id_drive

    ARQUIVO_CONTROLE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    arquivo_temporario = ARQUIVO_CONTROLE.with_suffix(".tmp")

    with arquivo_temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(controle, arquivo, indent=4, ensure_ascii=False)

    arquivo_temporario.replace(ARQUIVO_CONTROLE)


def ja_enviado(nome_arquivo):
    controle = carregar_controle()
    return nome_arquivo in controle



def limpar_backups_antigos(pasta_backups, manter=7):
    pasta_backups = Path(pasta_backups)
    controle = carregar_controle()

    enviados = sorted(
        (
            arquivo
            for arquivo in pasta_backups.glob("biblioteca_*.db.enc")
            if arquivo.name in controle
        ),
        key=lambda arquivo: arquivo.name,
        reverse=True
    )

    antigos = enviados[manter:]

    for arquivo in antigos:
        try:
            arquivo.unlink()
            print(f"Backup local antigo removido: {arquivo.name}")
        except OSError as erro:
            print(
                f"Não foi possível remover {arquivo.name}: {erro}"
            )

    print(
        f"Retenção local: até {manter} backups enviados mantidos."
    )
