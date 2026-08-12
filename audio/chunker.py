"""
Chunker: divisão inteligente de texto em blocos para processamento.
Divide por frases/parágrafos respeitando limites de tamanho.
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Padrões de divisão por pontuação
SENTENCE_ENDINGS = re.compile(r"(?<=[.!?])\s+")
PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


@dataclass
class Chunk:
    """Representa um bloco de texto para síntese."""
    index: int
    text: str
    total: int


def chunk_text(text: str, max_chars: int = 500) -> list[Chunk]:
    """
    Divide o texto em blocos de no máximo `max_chars` caracteres.
    
    Estratégia:
    1. Divide por parágrafos
    2. Se um parágrafo exceder max_chars, divide por frases
    3. Se uma frase exceder max_chars, divide por vírgulas
    
    Args:
        text: Texto completo a ser dividido.
        max_chars: Tamanho máximo de cada chunk em caracteres.
    
    Returns:
        Lista de objetos Chunk.
    """
    if not text or not text.strip():
        return []

    # Passo 1: dividir por parágrafos
    paragraphs = PARAGRAPH_BREAK.split(text.strip())
    raw_chunks: list[str] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(para) <= max_chars:
            raw_chunks.append(para)
        else:
            # Passo 2: dividir por frases
            sentences = SENTENCE_ENDINGS.split(para)
            current = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if len(current) + len(sentence) + 1 <= max_chars:
                    current = f"{current} {sentence}".strip() if current else sentence
                else:
                    if current:
                        raw_chunks.append(current)
                    if len(sentence) <= max_chars:
                        current = sentence
                    else:
                        # Passo 3: dividir frase longa por vírgulas
                        sub_parts = re.split(r"(?<=[,;])\s+", sentence)
                        current = ""
                        for sp in sub_parts:
                            if len(current) + len(sp) + 1 <= max_chars:
                                current = f"{current} {sp}".strip() if current else sp
                            else:
                                if current:
                                    raw_chunks.append(current)
                                # Forçar corte se ainda exceder
                                while len(sp) > max_chars:
                                    raw_chunks.append(sp[:max_chars])
                                    sp = sp[max_chars:]
                                current = sp
            if current:
                raw_chunks.append(current)

    # Montar lista de Chunks
    total = len(raw_chunks)
    return [Chunk(index=i, text=chunk, total=total) for i, chunk in enumerate(raw_chunks)]
