"""
Utilitário para baixar modelos ONNX do Piper TTS.
"""
import os
import json
import logging
import requests
from typing import Callable, Optional, Dict, Any, List

logger = logging.getLogger(__name__)

VOICES_JSON_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json"
BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"


class ModelDownloader:
    def __init__(self, models_dir: str):
        self.models_dir = models_dir
        self.voices_data: Dict[str, Any] = {}
        self.cached_json_path = os.path.join(models_dir, "voices.json")
        os.makedirs(models_dir, exist_ok=True)

    def fetch_voices_list(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Baixa e retorna a lista de vozes disponíveis."""
        if not force_refresh and os.path.exists(self.cached_json_path):
            try:
                with open(self.cached_json_path, "r", encoding="utf-8") as f:
                    self.voices_data = json.load(f)
                return self.voices_data
            except Exception as e:
                logger.warning(f"Erro ao ler voices.json em cache: {e}. Baixando novamente.")

        try:
            logger.info(f"Baixando lista de vozes de {VOICES_JSON_URL}")
            response = requests.get(VOICES_JSON_URL, timeout=10)
            response.raise_for_status()
            self.voices_data = response.json()
            
            with open(self.cached_json_path, "w", encoding="utf-8") as f:
                json.dump(self.voices_data, f, ensure_ascii=False, indent=2)
                
            return self.voices_data
        except Exception as e:
            logger.error(f"Erro ao buscar lista de vozes: {e}")
            raise

    def get_voice_info(self, key: str) -> Optional[Dict[str, Any]]:
        if not self.voices_data:
            self.fetch_voices_list()
        return self.voices_data.get(key)

    def is_voice_downloaded(self, key: str) -> bool:
        """Verifica se os arquivos .onnx e .onnx.json existem para a voz."""
        onnx_path = os.path.join(self.models_dir, f"{key}.onnx")
        json_path = os.path.join(self.models_dir, f"{key}.onnx.json")
        return os.path.exists(onnx_path) and os.path.exists(json_path)

    def download_voice(self, key: str, progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """
        Baixa o modelo (.onnx) e a configuração (.onnx.json) de uma voz.
        """
        voice_info = self.get_voice_info(key)
        if not voice_info:
            logger.error(f"Voz '{key}' não encontrada no voices.json")
            return False

        files_to_download = {}
        for file_path in voice_info.get("files", {}).keys():
            if file_path.endswith(".onnx") or file_path.endswith(".onnx.json"):
                # O nome final no disco será apenas a key (ex: pt_BR-faber-medium.onnx)
                ext = ".onnx.json" if file_path.endswith(".onnx.json") else ".onnx"
                dest_name = f"{key}{ext}"
                files_to_download[file_path] = os.path.join(self.models_dir, dest_name)

        total_files = len(files_to_download)
        for i, (remote_path, local_path) in enumerate(files_to_download.items()):
            url = BASE_URL + remote_path
            try:
                response = requests.get(url, stream=True, timeout=(15, 60))
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                
                block_size = 1024 * 64  # 64 KB
                downloaded = 0
                
                with open(local_path, "wb") as f:
                    for data in response.iter_content(chunk_size=block_size):
                        if data:
                            f.write(data)
                            downloaded += len(data)
                            if progress_callback and total_size > 0:
                                file_progress = downloaded / total_size
                                overall_progress = (i + file_progress) / total_files
                                filename = os.path.basename(local_path)
                                progress_callback(overall_progress, f"Baixando {filename} ({int(file_progress*100)}%)...")
                            
            except Exception as e:
                logger.error(f"Erro ao baixar {url}: {e}")
                # Limpar arquivos parciais
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except OSError:
                        pass
                return False

        if progress_callback:
            progress_callback(1.0, f"Voz {key} baixada com sucesso!")
        return True

    def delete_voice(self, key: str) -> bool:
        """Exclui os arquivos .onnx e .onnx.json de uma voz."""
        onnx_path = os.path.join(self.models_dir, f"{key}.onnx")
        json_path = os.path.join(self.models_dir, f"{key}.onnx.json")
        deleted = False
        for path in [onnx_path, json_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    deleted = True
                except Exception as e:
                    logger.error(f"Erro ao deletar {path}: {e}")
        return deleted
