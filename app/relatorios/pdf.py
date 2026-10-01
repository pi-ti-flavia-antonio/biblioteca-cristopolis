from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..texto import formatar_data

COR_PRIMARIA = colors.HexColor("#1d4e89")
COR_LINHA_PAR = colors.HexColor("#f5f7fa")
COR_BORDA = colors.HexColor("#e3e7ed")


def _status_do_emprestimo(emprestimo):
    if emprestimo["status"] == "devolvido":
        return "Devolvido"
    if emprestimo["atrasado"]:
        return "Atrasado"
    return "Ativo"


def gerar_pdf_periodo(data_inicio, data_fim, total, emprestimos):
    """Gera o PDF do relatório de empréstimos por período e retorna um BytesIO."""
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer, pagesize=A4,
        title="Relatório de Empréstimos",
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )
    estilos = getSampleStyleSheet()

    elementos = [
        Paragraph("Biblioteca Municipal de Cristópolis", estilos["Title"]),
        Paragraph("Relatório de Empréstimos por Período", estilos["Heading2"]),
        Spacer(1, 10),
        Paragraph(f"Período: {formatar_data(data_inicio.isoformat())} a {formatar_data(data_fim.isoformat())}", estilos["Normal"]),
        Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilos["Normal"]),
        Paragraph(f"Total de empréstimos: {total}", estilos["Normal"]),
        Spacer(1, 16),
    ]

    linhas = [["Livro", "Usuário", "Empréstimo", "Status"]]
    for emprestimo in emprestimos:
        linhas.append([
            Paragraph(emprestimo["livro_titulo"], estilos["BodyText"]),
            Paragraph(emprestimo["usuario_nome"], estilos["BodyText"]),
            formatar_data(emprestimo["data_emprestimo"]),
            _status_do_emprestimo(emprestimo),
        ])

    if not emprestimos:
        elementos.append(Paragraph("Nenhum empréstimo registrado nesse período.", estilos["Normal"]))
    else:
        tabela = Table(linhas, repeatRows=1, colWidths=[6.5 * cm, 5 * cm, 2.8 * cm, 2.7 * cm])
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, COR_BORDA),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_LINHA_PAR]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elementos.append(tabela)

    documento.build(elementos)
    buffer.seek(0)
    return buffer
