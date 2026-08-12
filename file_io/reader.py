"""
Leitor de arquivos: TXT e PDF.
Extrai texto de documentos para processamento.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


def read_file(file_path: str) -> str:
    """
    Lê um arquivo e retorna o texto extraído.
    
    Suporta:
        - .txt: leitura direta
        - .pdf: extração via PyPDF2
    
    Args:
        file_path: Caminho para o arquivo.
    
    Returns:
        Texto extraído do arquivo.
    
    Raises:
        ValueError: Se o formato não for suportado.
        FileNotFoundError: Se o arquivo não existir.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    ext = path.suffix.lower()

    if ext == ".txt":
        return _read_txt(path)
    elif ext == ".pdf":
        return _read_pdf(path)
    else:
        raise ValueError(
            f"Formato '{ext}' não suportado. Use: {', '.join(SUPPORTED_EXTENSIONS)}"
        )


def _read_txt(path: Path) -> str:
    """Lê arquivo de texto puro com detecção de encoding."""
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    # Último recurso: ignorar erros
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    """Extrai texto de um PDF usando PyMuPDF, ignorando cabeçalhos e rodapés."""
    try:
        import fitz
    except ImportError:
        raise ImportError("PyMuPDF é necessário para ler PDFs. Instale com: pip install PyMuPDF")

    doc = fitz.open(str(path))
    pages_text = []
    for i, page in enumerate(doc):
        try:
            rect = page.rect
            # Ignorar 10% superior e 10% inferior para evitar cabeçalhos/rodapés
            margin_y = rect.height * 0.1
            clip = fitz.Rect(rect.x0, rect.y0 + margin_y, rect.x1, rect.y1 - margin_y)
            
            text = page.get_text("text", clip=clip)
            if text:
                pages_text.append(text.strip())
        except Exception as e:
            logger.warning(f"Erro ao extrair texto da página {i + 1}: {e}")

    return "\n\n".join(pages_text)
