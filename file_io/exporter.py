"""
Exportador de áudio: mescla chunks de áudio e exporta em WAV ou MP3.
Usa ffmpeg diretamente via subprocess para conversão de formato.
"""

import os
import wave
import shutil
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def merge_wav_files(wav_paths: list[str], output_path: str) -> str:
    """
    Mescla múltiplos arquivos WAV em um único arquivo.
    
    Args:
        wav_paths: Lista de caminhos dos arquivos WAV.
        output_path: Caminho do arquivo de saída.
    
    Returns:
        Caminho do arquivo mesclado.
    """
    if not wav_paths:
        raise ValueError("Nenhum arquivo WAV para mesclar.")

    # Ler parâmetros do primeiro arquivo
    with wave.open(wav_paths[0], "rb") as first:
        params = first.getparams()

    # Criar arquivo de saída
    output = wave.open(output_path, "wb")
    output.setparams(params)

    for wav_path in wav_paths:
        if not os.path.exists(wav_path):
            logger.warning(f"Arquivo ignorado (não encontrado): {wav_path}")
            continue
        try:
            with wave.open(wav_path, "rb") as wf:
                output.writeframes(wf.readframes(wf.getnframes()))
        except Exception as e:
            logger.error(f"Erro ao mesclar {wav_path}: {e}")

    output.close()
    logger.info(f"Áudio mesclado salvo em: {output_path}")
    return output_path


def export_mp3(wav_path: str, output_path: str) -> str:
    """
    Converte WAV para MP3 usando ffmpeg diretamente.
    
    Args:
        wav_path: Caminho do arquivo WAV de entrada.
        output_path: Caminho do arquivo MP3 de saída.
    
    Returns:
        Caminho do arquivo MP3.
    """
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", wav_path,
            "-codec:a", "libmp3lame",
            "-b:a", "192k",
            output_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou: {result.stderr}")
    logger.info(f"MP3 exportado em: {output_path}")
    return output_path


def merge_and_export(
    wav_paths: list[str],
    output_path: str,
    format: str = "wav",
) -> str:
    """
    Mescla chunks WAV e exporta no formato desejado.
    
    Args:
        wav_paths: Lista de caminhos dos arquivos WAV.
        output_path: Caminho do arquivo de saída.
        format: 'wav' ou 'mp3'.
    
    Returns:
        Caminho do arquivo final.
    """
    # Mesclar em WAV temporário primeiro
    tmp_wav = os.path.join(tempfile.gettempdir(), "simple_narrator_merged.wav")
    merge_wav_files(wav_paths, tmp_wav)

    if format.lower() == "mp3":
        return export_mp3(tmp_wav, output_path)
    else:
        # Se já é WAV, apenas copiar/rename
        if tmp_wav != output_path:
            import shutil
            shutil.copy2(tmp_wav, output_path)
        return output_path
