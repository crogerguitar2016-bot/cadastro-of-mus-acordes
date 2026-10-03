# -*- coding: utf-8 -*-
"""Exportação PDF no padrão do projeto TRIADES / Harmonia Funcional Avançada."""

from datetime import datetime
from pathlib import Path

from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from pdf_storage import obter_pasta_saida_pdf, verificar_espaco_para_pdf

MARGEM_ESQUERDA = 55
MARGEM_DIREITA = 45
MARGEM_SUPERIOR = 55
MARGEM_INFERIOR = 55


def adicionar_marca_dagua(c, largura, altura):
    c.saveState()
    c.setFont("Helvetica-Bold", 46)
    c.setFillColor(Color(0, 0, 0, alpha=0.08))
    c.translate(largura / 2, altura / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, "PROFESSOR: CARLOS ROGERIO")
    c.rotate(-90)
    c.drawCentredString(0, 0, "PROFESSOR: CARLOS ROGERIO")
    c.restoreState()


def iniciar_pagina(c, largura, altura):
    adicionar_marca_dagua(c, largura, altura)
    return altura - MARGEM_SUPERIOR


def quebrar_linha_pdf(texto, fonte, tamanho, largura_maxima):
    palavras = str(texto).split()
    if not palavras:
        return [""]
    linhas = []
    atual = ""
    for palavra in palavras:
        teste = palavra if not atual else atual + " " + palavra
        if stringWidth(teste, fonte, tamanho) <= largura_maxima:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def escrever_linha_pdf(
    c,
    texto,
    y,
    largura,
    altura,
    fonte="Helvetica",
    tamanho=9,
    x=MARGEM_ESQUERDA,
    espacamento=13,
):
    largura_maxima = largura - x - MARGEM_DIREITA
    linhas = quebrar_linha_pdf(texto, fonte, tamanho, largura_maxima)
    for linha in linhas:
        if y < MARGEM_INFERIOR:
            c.showPage()
            y = iniciar_pagina(c, largura, altura)
        c.setFont(fonte, tamanho)
        c.drawString(x, y, linha)
        y -= espacamento
    return y


def escrever_cadastro(c, numero, record, campos_ativos, y, largura, altura):
    fonte = "Helvetica"
    tamanho = 8
    espacamento = 12
    numero_texto = f"{numero:02d}."
    x_numero = MARGEM_ESQUERDA
    largura_numero = stringWidth(numero_texto, fonte, tamanho)
    x_conteudo = x_numero + largura_numero + 8
    largura_conteudo = largura - x_conteudo - MARGEM_DIREITA

    partes = [
        str(record.get("nome", "")),
        "Contato: " + str(record.get("contato", "") or "-"),
        "Combo: " + str(record.get("grupo", "") or "-"),
        "Status: " + str(record.get("status", "Ativo")),
    ]
    obs = str(record.get("observacoes", "") or "").strip()
    if obs:
        partes.append("Observações: " + obs.replace("\n", " "))

    valores = record.get("campos", {}) if isinstance(record.get("campos"), dict) else {}
    for campo in campos_ativos:
        valor = str(valores.get(str(campo.get("id")), "") or "").strip()
        if valor:
            partes.append(f"{campo.get('nome', 'Campo')}: {valor}")

    texto = " | ".join(partes)
    linhas = quebrar_linha_pdf(texto, fonte, tamanho, largura_conteudo)
    altura_necessaria = len(linhas) * espacamento + 2
    altura_util_pagina = altura - MARGEM_SUPERIOR - MARGEM_INFERIOR
    espaco_restante = y - MARGEM_INFERIOR

    if altura_necessaria <= altura_util_pagina and altura_necessaria > espaco_restante:
        c.showPage()
        y = iniciar_pagina(c, largura, altura)

    c.setFont(fonte, tamanho)
    for indice, linha in enumerate(linhas):
        if y < MARGEM_INFERIOR:
            c.showPage()
            y = iniciar_pagina(c, largura, altura)
        if indice == 0:
            c.drawString(x_numero, y, numero_texto)
        c.drawString(x_conteudo, y, linha)
        y -= espacamento
    return y - 2


def gerar_pdf_cadastros(store, nome="Cadastro_Of_Mus_Acordes_relatorio.pdf"):
    pasta = obter_pasta_saida_pdf(store.exports_dir)
    verificar_espaco_para_pdf(pasta)
    caminho = Path(pasta) / nome
    if caminho.suffix.lower() != ".pdf":
        caminho = caminho.with_suffix(".pdf")

    registros = store.list_records("az")
    campos = [f for f in store.load_fields() if f.get("status", "Ativo") == "Ativo"]
    resumo = store.report_summary()

    largura, altura = A4
    c = canvas.Canvas(str(caminho), pagesize=A4)
    c.setTitle("Cadastro Of. Mus. Acordes - Relatório")
    c.setAuthor("Professor Carlos Rogerio")

    y = iniciar_pagina(c, largura, altura)
    y = escrever_linha_pdf(
        c,
        "CADASTRO OF. MUS. ACORDES",
        y,
        largura,
        altura,
        fonte="Helvetica-Bold",
        tamanho=14,
        espacamento=18,
    )
    y = escrever_linha_pdf(
        c,
        "PROFESSOR: CARLOS ROGERIO",
        y,
        largura,
        altura,
        fonte="Helvetica-Bold",
        tamanho=10,
        espacamento=18,
    )
    y = escrever_linha_pdf(
        c,
        "Relatório gerado em: " + datetime.now().strftime("%d/%m/%Y %H:%M"),
        y,
        largura,
        altura,
        tamanho=10,
    )
    y = escrever_linha_pdf(
        c,
        f"Total: {resumo['total']} | Ativos: {resumo['ativos']} | Inativos: {resumo['inativos']}",
        y,
        largura,
        altura,
        tamanho=10,
        espacamento=18,
    )
    y = escrever_linha_pdf(
        c,
        "CADASTROS",
        y,
        largura,
        altura,
        fonte="Helvetica-Bold",
        tamanho=11,
        espacamento=17,
    )

    if not registros:
        y = escrever_linha_pdf(c, "Nenhum cadastro encontrado.", y, largura, altura, tamanho=9)
    else:
        for indice, record in enumerate(registros, 1):
            y = escrever_cadastro(c, indice, record, campos, y, largura, altura)

    c.save()
    return caminho
