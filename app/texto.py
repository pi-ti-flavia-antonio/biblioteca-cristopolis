import re
import unicodedata
from datetime import date


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


def limpar_digitos(texto):
    """Mantém só os dígitos de um texto (CPF, telefone etc.)."""
    return re.sub(r"\D", "", texto or "")


def cpf_valido(digitos):
    """Valida um CPF de 11 dígitos pelo algoritmo oficial de dígitos verificadores."""
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False

    def digito_verificador(parcial):
        peso = len(parcial) + 1
        soma = sum(int(d) * (peso - i) for i, d in enumerate(parcial))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = digito_verificador(digitos[:9])
    d2 = digito_verificador(digitos[:9] + d1)
    return digitos[-2:] == d1 + d2


def formatar_cpf(digitos):
    if not digitos or len(digitos) != 11:
        return digitos or ""
    return f"{digitos[0:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:11]}"


def formatar_data(iso):
    """Converte 'aaaa-mm-dd' em 'dd/mm/aaaa' para exibição."""
    if not iso:
        return ""
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def formatar_telefone(digitos):
    if not digitos:
        return ""
    if len(digitos) == 11:
        return f"({digitos[0:2]}) {digitos[2:7]}-{digitos[7:11]}"
    if len(digitos) == 10:
        return f"({digitos[0:2]}) {digitos[2:6]}-{digitos[6:10]}"
    return digitos
