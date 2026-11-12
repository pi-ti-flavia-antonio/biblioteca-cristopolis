"""Configura o Gmail que envia o código de recuperação de senha.

Jeito mais fácil: dar dois cliques em configurar_email_janela.pyw, que abre uma janela.
Pelo terminal:

    python configurar_email.py

Use uma senha de aplicativo do Google (não a senha normal da conta). Os dados
ficam no arquivo email.json, na pasta de dados do sistema, fora do Git.
"""

import getpass
import json
import sys

from app import create_app, email_envio
from caminhos import caminho_email


def configurar(remetente, senha):
    """Grava o Gmail e a senha de aplicativo e manda um e-mail de teste para o próprio Gmail.

    Devolve (deu_certo, mensagem).
    """
    remetente = remetente.strip()
    senha = senha.replace(" ", "")
    if "@" not in remetente or not senha:
        return False, "Informe o Gmail e a senha de aplicativo."

    caminho_email().write_text(json.dumps({"remetente": remetente, "senha_app": senha}), encoding="utf-8")

    app = create_app()
    with app.app_context():
        try:
            email_envio.enviar(remetente, "Teste do sistema da biblioteca", "O envio de e-mail do sistema da biblioteca está funcionando.\n")
        except email_envio.FalhaNoEnvio:
            return False, ("Os dados foram salvos, mas o e-mail de teste não saiu. "
                           "Confira a internet, se a verificação em duas etapas está ativa e se a senha de aplicativo foi copiada certa.")
    return True, f"Pronto. Um e-mail de teste foi enviado para {remetente}."


def main():
    remetente = input("Gmail que vai enviar os códigos: ")
    senha = getpass.getpass("Senha de aplicativo do Google: ")
    deu_certo, mensagem = configurar(remetente, senha)
    print(mensagem)
    return 0 if deu_certo else 1


if __name__ == "__main__":
    sys.exit(main())
