import re
import unicodedata


def normalizar(texto):
    """Minúsculas e sem acentos, para comparar textos na busca."""
    if texto is None:
        return ""
    decomposto = unicodedata.normalize("NFD", str(texto))
    sem_acentos = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
    return sem_acentos.casefold()


def limpar_isbn(texto):
    """Mantém só dígitos e o X final, sem hífens nem espaços."""
    return re.sub(r"[^0-9Xx]", "", texto or "").upper()
