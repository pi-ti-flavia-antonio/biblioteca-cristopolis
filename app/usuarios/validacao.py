import re

from ..texto import cpf_valido, limpar_digitos

CAMPOS = ("nome", "cpf", "telefone", "tipo_usuario", "email", "endereco")

TIPOS_USUARIO = ("aluno", "professor", "comunidade")

TAMANHO_MAX_NOME = 150
TAMANHO_MAX_EMAIL = 150
TAMANHO_MAX_ENDERECO = 200

_PARTE_LOCAL = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
_DOMINIO = r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}"
_EMAIL_RE = re.compile(rf"^{_PARTE_LOCAL}@{_DOMINIO}$")

# DDDs que existem no Brasil.
DDDS = frozenset(
    list(range(11, 20))
    + [21, 22, 24, 27, 28]
    + list(range(31, 36)) + [37, 38]
    + list(range(41, 50))
    + [51, 53, 54, 55]
    + list(range(61, 70))
    + [71, 73, 74, 75, 77, 79]
    + list(range(81, 90))
    + list(range(91, 100))
)

MENSAGEM_TELEFONE = "Informe um telefone válido com DDD, como (77) 99999-9999 ou (77) 3333-3333."


def telefone_valido(digitos):
    """Celular: DDD + 9 + 8 dígitos. Fixo: DDD + 2 a 5 + 7 dígitos."""
    if len(digitos) not in (10, 11) or int(digitos[:2]) not in DDDS:
        return False
    numero = digitos[2:]
    if len(set(numero)) == 1:
        return False
    if len(digitos) == 11:
        return numero[0] == "9"
    return numero[0] in "2345"


def valores_iniciais():
    return {campo: "" for campo in CAMPOS}


def valores_do_formulario(form):
    return {campo: form.get(campo, "").strip() for campo in CAMPOS}


def valores_do_usuario(usuario):
    return {
        "nome": usuario["nome"],
        "cpf": usuario["cpf"] or "",
        "telefone": usuario["telefone"] or "",
        "tipo_usuario": usuario["tipo_usuario"] or "",
        "email": usuario["email"] or "",
        "endereco": usuario["endereco"] or "",
    }


def validar_usuario(valores):
    erros = {}

    nome = valores["nome"]
    if not nome:
        erros["nome"] = "Informe o nome."
    elif len(nome) > TAMANHO_MAX_NOME:
        erros["nome"] = f"O nome pode ter no máximo {TAMANHO_MAX_NOME} caracteres."

    cpf = None
    if not valores["cpf"]:
        erros["cpf"] = "Informe o CPF."
    else:
        digitos = limpar_digitos(valores["cpf"])
        if cpf_valido(digitos):
            cpf = digitos
        else:
            erros["cpf"] = "Informe um CPF válido, com 11 dígitos."

    telefone = None
    if not valores["telefone"]:
        erros["telefone"] = "Informe o telefone."
    else:
        digitos_tel = limpar_digitos(valores["telefone"])
        if telefone_valido(digitos_tel):
            telefone = digitos_tel
        else:
            erros["telefone"] = MENSAGEM_TELEFONE

    tipo_usuario = valores["tipo_usuario"] or None
    if tipo_usuario and tipo_usuario not in TIPOS_USUARIO:
        erros["tipo_usuario"] = "Selecione um tipo de usuário válido."

    email = valores["email"] or None
    if email:
        if len(email) > TAMANHO_MAX_EMAIL:
            erros["email"] = f"O e-mail pode ter no máximo {TAMANHO_MAX_EMAIL} caracteres."
        elif not _EMAIL_RE.match(email):
            erros["email"] = "Informe um e-mail válido."

    endereco = valores["endereco"] or None
    if endereco and len(endereco) > TAMANHO_MAX_ENDERECO:
        erros["endereco"] = f"O endereço pode ter no máximo {TAMANHO_MAX_ENDERECO} caracteres."

    dados = {
        "nome": nome,
        "cpf": cpf,
        "telefone": telefone,
        "tipo_usuario": tipo_usuario,
        "email": email,
        "endereco": endereco,
    }
    return dados, erros
