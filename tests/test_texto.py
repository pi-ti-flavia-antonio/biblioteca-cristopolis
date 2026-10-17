from app.texto import link_whatsapp


def test_link_do_whatsapp_com_celular():
    assert link_whatsapp("67999990000", "Olá") == "https://wa.me/5567999990000?text=Ol%C3%A1"


def test_link_do_whatsapp_aceita_telefone_formatado_e_fixo():
    assert link_whatsapp("(67) 3333-4444", "oi").startswith("https://wa.me/556733334444?text=")


def test_link_do_whatsapp_sem_ddd_ou_vazio_nao_gera_link():
    assert link_whatsapp("99990000", "oi") == ""
    assert link_whatsapp("", "oi") == ""
    assert link_whatsapp(None, "oi") == ""
