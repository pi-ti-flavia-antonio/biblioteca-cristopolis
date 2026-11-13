
import os
from pathlib import Path
from cryptography.fernet import Fernet

pasta = (
    Path(os.environ["LOCALAPPDATA"])
    / "BibliotecaCristopolis"
    / "data"
)

arquivo = pasta / "chave_backup.key"

if arquivo.exists():
    print("A chave de criptografia já existe.")
    print("Nenhuma alteração foi realizada.")
else:
    print("ATENÇÃO!")
    print("Uma nova chave NÃO recupera backups antigos.")
    print("Verifique se existe uma cópia da chave original.")

    resposta = input(
        "Deseja criar uma nova chave? (SIM/NAO): "
    )

    if resposta.strip().upper() != "SIM":
        print("Operação cancelada.")
        raise SystemExit(0)

    pasta.mkdir(parents=True, exist_ok=True)

    with arquivo.open("xb") as f:
        f.write(Fernet.generate_key())

    print("Nova chave criada com sucesso!")
    print("Guarde uma cópia em local seguro.")

print("Arquivo:", "OK" if arquivo.is_file() else "AUSENTE")
