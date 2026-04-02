"""
Dürer AI — Ingestão de PDFs
Extrai texto de PDFs usando pymupdf (fitz).
"""

from pathlib import Path
import fitz  # pymupdf
from core.logger import get_logger

log = get_logger(__name__)


def extrair_texto(caminho: Path) -> str:
    """
    Extrai todo o texto de um PDF.
    Retorna string vazia se falhar.
    """
    try:
        doc = fitz.open(str(caminho))
        paginas = []
        for i, pagina in enumerate(doc):
            texto = pagina.get_text()
            if texto.strip():
                paginas.append(f"[Página {i+1}]\n{texto}")
        doc.close()
        resultado = "\n\n".join(paginas)
        log.info(f"PDF extraído: {caminho.name} ({len(doc)} páginas, {len(resultado)} chars)")
        return resultado
    except Exception as e:
        log.error(f"Falha ao extrair PDF {caminho.name}: {e}")
        return ""