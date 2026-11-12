"""Janela para configurar o Gmail que envia o código de recuperação de senha. Dois cliques para abrir."""

import tkinter as tk
from tkinter import messagebox

from configurar_email import configurar


def salvar():
    botao.config(state="disabled", text="Enviando e-mail de teste...")
    janela.update()
    deu_certo, mensagem = configurar(campo_gmail.get(), campo_senha.get())
    botao.config(state="normal", text="Salvar e testar")
    if deu_certo:
        messagebox.showinfo("Biblioteca", mensagem + "\n\nOlhe a caixa de entrada (e o spam) desse Gmail.")
        janela.destroy()
    else:
        messagebox.showerror("Biblioteca", mensagem)


janela = tk.Tk()
janela.title("E-mail de recuperação de senha")
janela.resizable(False, False)

tk.Label(janela, text="Gmail que vai enviar os códigos:").grid(row=0, column=0, sticky="w", padx=14, pady=(14, 2))
campo_gmail = tk.Entry(janela, width=42)
campo_gmail.grid(row=1, column=0, padx=14)

tk.Label(janela, text="Senha de aplicativo do Google (16 letras):").grid(row=2, column=0, sticky="w", padx=14, pady=(10, 2))
campo_senha = tk.Entry(janela, width=42, show="*")
campo_senha.grid(row=3, column=0, padx=14)

botao = tk.Button(janela, text="Salvar e testar", command=salvar, width=20)
botao.grid(row=4, column=0, pady=14)

campo_gmail.focus()
janela.mainloop()
