import re

from ..texto import cpf_valido, limpar_digitos

CAMPOS = ("nome", "cpf", "telefone", "tipo_usuario", "email", "endereco", "carteirinha_modo", "numero_carteirinha")

TIPOS_USUARIO = ("aluno", "professor", "comunidade", "responsável")

# Os números de 1 a 11046 são reservados para os usuários antigos, que a bibliotecária digita.
# Os usuários novos recebem os números a partir de 11047.
ULTIMO_NUMERO_RESERVADO = 11046

TAMANHO_MAX_NOME = 150
TAMANHO_MAX_EMAIL = 150
TAMANHO_MAX_ENDERECO = 200

_PARTE_LOCAL = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
_DOMINIO = r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}"
_EMAIL_RE = re.compile(rf"^{_PARTE_LOCAL}@{_DOMINIO}$")

def erro_de_email(email):
    """Mensagem de erro para um e-mail preenchido, ou None se ele for aceito."""
    if len(email) > TAMANHO_MAX_EMAIL:
        return f"O e-mail pode ter no máximo {TAMANHO_MAX_EMAIL} caracteres."
    if not _EMAIL_RE.match(email):
        return "Informe um e-mail válido."
    return None


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
    return {**{campo: "" for campo in CAMPOS}, "carteirinha_modo": "manual"}


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
        "carteirinha_modo": "manual",
        "numero_carteirinha": str(usuario["numero_carteirinha"] or ""),
    }


def validar_carteirinha(valores, numero_atual, edicao, erros):
    """Devolve o número digitado, ou None (sem número, ou para o sistema gerar)."""
    if not edicao and valores["carteirinha_modo"] == "automatico":
        return None

    texto = valores["numero_carteirinha"]
    if not texto:
        if not edicao or numero_atual:
            erros["numero_carteirinha"] = "Informe o número da carteirinha."
        return None
    if not texto.isdigit() or len(texto) > 9:
        erros["numero_carteirinha"] = "Digite só números no número da carteirinha."
        return None
    numero = int(texto)
    if numero != numero_atual and not 1 <= numero <= ULTIMO_NUMERO_RESERVADO:
        erros["numero_carteirinha"] = (
            f"Digite um número de 1 a {ULTIMO_NUMERO_RESERVADO}. "
            f"Os números acima de {ULTIMO_NUMERO_RESERVADO} são gerados pelo sistema."
        )
        return None
    return numero


TAMANHO_MAX_FOTO = 1_000_000
_ASSINATURAS_DE_IMAGEM = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


def validar_foto(arquivo):
    """Devolve (tipo, bytes, erro). Sem arquivo escolhido, devolve (None, None, None)."""
    if arquivo is None or not arquivo.filename:
        return None, None, None
    dados = arquivo.read(TAMANHO_MAX_FOTO + 1)
    if not dados:
        return None, None, None
    if len(dados) > TAMANHO_MAX_FOTO:
        return None, None, "A foto pode ter no máximo 1 MB."
    # O tipo vem do conteúdo do arquivo, não do nome nem do que o navegador diz.
    for assinatura, tipo in _ASSINATURAS_DE_IMAGEM:
        if dados.startswith(assinatura):
            return tipo, dados, None
    return None, None, "A foto precisa ser uma imagem JPEG ou PNG."


def validar_usuario(valores, numero_atual=None, edicao=False):
    erros = {}

    nome = valores["nome"]
    if not nome:
        erros["nome"] = "Informe o nome."
    elif len(nome) > TAMANHO_MAX_NOME:
        erros["nome"] = f"O nome pode ter no máximo {TAMANHO_MAX_NOME} caracteres."

    cpf = None
    if valores["cpf"]:
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
        erro_email = erro_de_email(email)
        if erro_email:
            erros["email"] = erro_email

    endereco = valores["endereco"] or None
    if not endereco:
        erros["endereco"] = "Informe o endereço."
    elif len(endereco) > TAMANHO_MAX_ENDERECO:
        erros["endereco"] = f"O endereço pode ter no máximo {TAMANHO_MAX_ENDERECO} caracteres."

    numero_carteirinha = validar_carteirinha(valores, numero_atual, edicao, erros)

    dados = {
        "nome": nome,
        "cpf": cpf,
        "telefone": telefone,
        "tipo_usuario": tipo_usuario,
        "email": email,
        "endereco": endereco,
        "numero_carteirinha": numero_carteirinha,
    }
    return dados, erros
