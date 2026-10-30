import os
import sys
from pathlib import Path


def pasta_dados():
    if getattr(sys, "frozen", False):
        base = Path(
            os.environ.get("LOCALAPPDATA")
            or Path.home() / "AppData" / "Local"
        )
        destino = base / "BibliotecaCristopolis" / "data"
    else:
        destino = Path(__file__).resolve().parent / "data"

    destino.mkdir(parents=True, exist_ok=True)
    return destino


def caminho_banco():
    return pasta_dados() / "biblioteca.db"
