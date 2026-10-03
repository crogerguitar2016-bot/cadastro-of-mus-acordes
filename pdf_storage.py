# -*- coding: utf-8 -*-
"""Armazenamento do PDF seguindo o método funcional do projeto TRIADES.

Android:
- grava diretamente em /storage/emulated/0/Download;
- não usa MediaStore para o PDF;
- o ReportLab cria o arquivo diretamente na pasta pública.

Outros ambientes:
- usa a pasta de exportações do DataStore, para testes.
"""

import os
import shutil
from pathlib import Path

PASTA_DOWNLOAD_ANDROID = os.path.join("/storage/emulated/0", "Download")
PASTA_DESTINO_ANDROID = os.path.join(PASTA_DOWNLOAD_ANDROID, "Cadastro Of. Mus. Acordes")
DESTINO_PUBLICO_ANDROID = "Download/Cadastro Of. Mus. Acordes"
RESERVA_CRITICA_BYTES = 64 * 1024 * 1024


def _is_android():
    try:
        from kivy.utils import platform
        return platform == "android"
    except Exception:
        return False


def obter_pasta_saida_pdf(pasta_local=None):
    if _is_android():
        os.makedirs(PASTA_DESTINO_ANDROID, exist_ok=True)
        return Path(PASTA_DESTINO_ANDROID)

    pasta = Path(pasta_local or "pdf_gerados")
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def obter_destino_exibicao_pdf(pasta_local=None):
    if _is_android():
        return DESTINO_PUBLICO_ANDROID
    return str(obter_pasta_saida_pdf(pasta_local))


def verificar_espaco_para_pdf(pasta_referencia=None, reserva_minima_bytes=RESERVA_CRITICA_BYTES):
    pasta = Path(pasta_referencia or obter_pasta_saida_pdf())
    pasta.mkdir(parents=True, exist_ok=True)
    livre = shutil.disk_usage(str(pasta)).free
    if livre < reserva_minima_bytes:
        raise RuntimeError(
            "Espaço de armazenamento criticamente baixo. "
            f"Livre: {livre / (1024 * 1024):.1f} MB. "
            f"Reserve pelo menos {reserva_minima_bytes / (1024 * 1024):.0f} MB."
        )
    return livre
