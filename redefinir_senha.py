"""Redefine a senha e, se quiser, o nome de usuário da conta de acesso.

Serve para quem esqueceu a senha ou o usuário. Rode no computador da biblioteca:

    python redefinir_senha.py
"""

import getpass
import sys

from app import auth, create_app


def main():
    app = create_app()
    with app.app_context():
        funcionaria = auth.conta()
        if funcionaria is None:
            print("Ainda não existe uma conta. Abra o sistema e crie a conta no primeiro acesso.")
            return 1

        print(f"Conta atual: usuário '{funcionaria['login']}' ({funcionaria['nome']})")
        novo_login = input("Novo nome de usuário (Enter para manter o atual): ").strip() or funcionaria["login"]
        erro = auth.validar_login(novo_login)
        if erro:
            print(erro)
            return 1

        senha = getpass.getpass("Nova senha (Enter para manter a atual): ")
        if senha:
            confirmacao = getpass.getpass("Repita a nova senha: ")
            erro = auth.validar_nova_senha(senha, confirmacao, novo_login)
            if erro:
                print(erro)
                return 1

        if novo_login == funcionaria["login"] and not senha:
            print("Nada foi alterado.")
            return 0

        if novo_login != funcionaria["login"]:
            auth.alterar_dados(funcionaria["nome"], novo_login)
        if senha:
            auth.redefinir_senha(senha)
        print("Pronto. Já é possível entrar com os novos dados.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
