import re

from ..texto import cpf_valido, limpar_digitos

CAMPOS = ("nome", "cpf", "telefone", "tipo_usuario", "email", "endereco")

TIPOS_USUARIO = ("aluno", "professor", "comunidade")

TAMANHO_MAX_NOME = 150
TAMANHO_MAX_EMAIL = 150
TAMANHO_MAX_ENDERECO = 200

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
        if 10 <= len(digitos_tel) <= 11:
            telefone = digitos_tel
        else:
            erros["telefone"] = "Informe um telefone válido, com DDD (10 ou 11 dígitos)."

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
