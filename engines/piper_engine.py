"""
Motor Piper TTS.
Utiliza modelos ONNX para síntese de voz offline de alta qualidade.
"""
import os
import sys
import uuid
import tempfile
import logging
import threading
from typing import Optional, List

from engines.base_engine import BaseEngine, EngineState, VoiceInfo

logger = logging.getLogger(__name__)


def _register_nvidia_dll_paths():
    """Registra todos os diretórios de DLLs NVIDIA (cuDNN, cuBLAS, NVRTC) para o ONNX Runtime.
    
    Funciona tanto em ambiente de desenvolvimento quanto no executável PyInstaller.
    """
    dirs_to_add = []
    
    # Caso 0: Pasta 'cuda' local ao lado do executável ou raiz do projeto
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_cuda_dir = os.path.join(base_dir, "cuda")
    if os.path.isdir(local_cuda_dir) and local_cuda_dir not in dirs_to_add:
        dirs_to_add.append(local_cuda_dir)

    # Caso 1: PyInstaller bundle — DLLs estão em sys._MEIPASS
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        # Procurar DLLs NVIDIA na raiz do bundle e em subpastas
        for root, dirs, files in os.walk(meipass):
            for f in files:
                if f.startswith(("cudnn", "cublas")) and f.endswith(".dll"):
                    if root not in dirs_to_add:
                        dirs_to_add.append(root)
                    break  # Só precisa encontrar um DLL por diretório
    
    # Caso 2: Ambiente Python normal — usar pacote nvidia
    try:
        import nvidia
        nvidia_root = nvidia.__path__[0]
        for pkg_name in os.listdir(nvidia_root):
            bin_dir = os.path.join(nvidia_root, pkg_name, "bin")
            if os.path.isdir(bin_dir):
                dirs_to_add.append(bin_dir)
    except (ImportError, Exception):
        pass
    
    # Caso 3: CUDA instalado no sistema (NVIDIA GPU Computing Toolkit)
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        bin_dir = os.path.join(cuda_path, "bin")
        if os.path.isdir(bin_dir) and bin_dir not in dirs_to_add:
            dirs_to_add.append(bin_dir)

    # Caso 4: Buscar caminhos padrões do CUDA Toolkit no Windows
    if sys.platform == "win32":
        default_cuda_root = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"
        if os.path.isdir(default_cuda_root):
            try:
                for ver_dir in os.listdir(default_cuda_root):
                    bin_dir = os.path.join(default_cuda_root, ver_dir, "bin")
                    if os.path.isdir(bin_dir) and bin_dir not in dirs_to_add:
                        dirs_to_add.append(bin_dir)
            except Exception:
                pass

    # Registrar todos os diretórios encontrados
    for path in dirs_to_add:
        try:
            os.add_dll_directory(path)
        except Exception:
            pass

    # Também adicionar ao PATH para garantir que dependências cruzadas sejam encontradas
    if dirs_to_add:
        current_path = os.environ.get("PATH", "")
        os.environ["PATH"] = os.pathsep.join(dirs_to_add + [current_path])
        logger.info(f"DLLs NVIDIA registrados no PATH ({len(dirs_to_add)} diretórios)")
    else:
        logger.debug("Nenhuma DLL NVIDIA encontrada.")


class PiperEngine(BaseEngine):
    """Motor de TTS baseado no Piper TTS (modelos ONNX)."""

    def __init__(self, models_dir: str = "models"):
        self._state = EngineState.IDLE
        self.models_dir = os.path.abspath(models_dir)
        self._voice_id: Optional[str] = None
        self._voice = None
        self._rate_scale = 1.0  # Piper usa length_scale (maior = mais lento)
        self.use_cuda = False
        self._synth_lock = threading.Lock()

    def set_use_cuda(self, use_cuda: bool) -> None:
        """Define se deve usar aceleração por GPU (CUDA)."""
        if self.use_cuda != use_cuda:
            self.use_cuda = use_cuda
            if self._voice_id:
                curr_voice = self._voice_id
                self._voice = None
                self._load_voice(curr_voice)

    def initialize(self) -> None:
        pass

    def get_available_voices(self) -> list[VoiceInfo]:
        from piper.download import get_voices
        result = []
        voices_data = self._get_local_voices_data()
        for voice_key, voice_meta in voices_data.items():
            lang = voice_meta.get("language", {}).get("code", "unknown")
            quality = voice_meta.get("quality", "unknown")
            name = f"{voice_key} ({quality})"
            result.append(
                VoiceInfo(
                    id=voice_key,
                    name=name,
                    language=lang,
                    gender=None,
                    engine_type="piper",
                )
            )
        return result

    def _get_local_voices_data(self) -> dict:
        import json
        json_path = os.path.join(self.models_dir, "voices.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao ler voices.json local: {e}")
        return {}

    def set_voice(self, voice_id: str) -> None:
        self._voice_id = voice_id
        self._load_voice(voice_id)

    def _load_voice(self, voice_id: str) -> None:
        from piper import PiperVoice
        onnx_file = os.path.join(self.models_dir, f"{voice_id}.onnx")
        config_file = os.path.join(self.models_dir, f"{voice_id}.onnx.json")

        if not os.path.exists(onnx_file):
            self._voice = None
            return

        _register_nvidia_dll_paths()

        try:
            cfg = config_file if os.path.exists(config_file) else None
            self._voice = PiperVoice.load(
                onnx_file,
                config_path=cfg,
                use_cuda=self.use_cuda,
            )
            logger.info(f"Voz Piper '{voice_id}' carregada (CUDA: {self.use_cuda}).")
        except Exception as e:
            if self.use_cuda:
                logger.warning(f"Falha ao carregar modelo com CUDA ({e}). Tentando CPU...")
                try:
                    cfg = config_file if os.path.exists(config_file) else None
                    self._voice = PiperVoice.load(
                        onnx_file,
                        config_path=cfg,
                        use_cuda=False,
                    )
                    self.use_cuda = False
                    logger.info(f"Voz Piper '{voice_id}' carregada em modo CPU após fallback.")
                    return
                except Exception as fallback_err:
                    logger.error(f"Fallback para CPU também falhou: {fallback_err}")
            logger.error(f"Erro ao carregar modelo Piper: {e}")
            self._voice = None

    def set_rate(self, rate: float) -> None:
        if rate <= 0:
            rate = 1.0
        self._rate_scale = 1.0 / rate

    def set_pitch(self, pitch: float) -> None:
        pass

    def synthesize(self, text: str) -> Optional[str]:
        if not self._voice:
            if self._voice_id:
                self._load_voice(self._voice_id)
            if not self._voice:
                logger.error("Nenhuma voz Piper carregada.")
                return None

        self._state = EngineState.SPEAKING
        tmp_path = os.path.join(
            tempfile.gettempdir(),
            f"sn_piper_{uuid.uuid4().hex[:8]}.wav",
        )
        wav_file = None
        try:
            import wave
            with self._synth_lock:
                wav_file = wave.open(tmp_path, "wb")
                self._voice.synthesize(
                    text,
                    wav_file,
                    length_scale=self._rate_scale,
                )
            self._state = EngineState.IDLE
            return tmp_path
        except Exception as e:
            logger.error(f"Erro na síntese Piper: {e}")
            self._state = EngineState.ERROR
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return None
        finally:
            if wav_file is not None:
                try:
                    wav_file.close()
                except Exception:
                    pass

    def synthesize_stream(self, text: str):
        if not self._voice:
            if self._voice_id:
                self._load_voice(self._voice_id)
            if not self._voice:
                logger.error("Nenhuma voz Piper carregada para streaming.")
                return

        self._state = EngineState.SPEAKING
        try:
            for chunk in self._voice.synthesize(text):
                yield chunk.audio_int16_bytes
            self._state = EngineState.IDLE
        except Exception as e:
            logger.error(f"Erro no stream Piper: {e}")
            self._state = EngineState.ERROR
            yield b""

    def shutdown(self) -> None:
        self._state = EngineState.IDLE
        self._voice = None

    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def engine_name(self) -> str:
        return "IA (Piper TTS)"

    # ─────────────────────────────────────────────
    #  GERENCIAMENTO DE GPU (Instalação sob demanda)
    # ─────────────────────────────────────────────

    @staticmethod
    def is_gpu_available() -> bool:
        """Verifica se o suporte GPU (CUDA) está disponível e funcional."""
        try:
            _register_nvidia_dll_paths()
            import onnxruntime
            providers = onnxruntime.get_available_providers()
            if "CUDAExecutionProvider" not in providers:
                return False

            # No Windows, validar se as DLLs essenciais da NVIDIA podem ser carregadas
            if sys.platform == "win32":
                import ctypes
                for dll in ("cublas64_12.dll", "cublas64_11.dll", "cublas64_10.dll"):
                    try:
                        ctypes.WinDLL(dll)
                        return True
                    except Exception:
                        continue
                return False
            return True
        except Exception:
            return False

    @classmethod
    def install_gpu_support(cls, progress_callback=None) -> bool:
        """Baixa e extrai as DLLs NVIDIA CUDA/cuDNN diretamente para a pasta 'cuda' local."""
        import zipfile
        import shutil
        import requests

        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cuda_dir = os.path.join(base_dir, "cuda")
        os.makedirs(cuda_dir, exist_ok=True)

        packages = [
            ("nvidia-cuda-runtime-cu12", "Baixando CUDA Runtime..."),
            ("nvidia-cuda-nvrtc-cu12", "Baixando NVRTC..."),
            ("nvidia-cublas-cu12", "Baixando cuBLAS..."),
            ("nvidia-cudnn-cu12", "Baixando cuDNN..."),
        ]

        total_pkgs = len(packages)
        for i, (pkg_name, label) in enumerate(packages):
            if progress_callback:
                progress_callback(i / total_pkgs, f"Buscando {pkg_name}...")
            try:
                pypi_resp = requests.get(f"https://pypi.org/pypi/{pkg_name}/json", timeout=15)
                pypi_resp.raise_for_status()
                data = pypi_resp.json()
                win_urls = [u for u in data.get("urls", []) if "win_amd64.whl" in u.get("filename", "")]
                if not win_urls:
                    logger.error(f"Nenhum wheel Windows encontrado para {pkg_name}")
                    return False

                wheel_info = win_urls[-1]
                wheel_url = wheel_info["url"]
                total_size = int(wheel_info.get("size", 0))

                tmp_wheel = os.path.join(tempfile.gettempdir(), f"{pkg_name}.whl")
                downloaded = 0
                with requests.get(wheel_url, stream=True, timeout=(15, 60)) as resp:
                    resp.raise_for_status()
                    with open(tmp_wheel, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=1024 * 128):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if progress_callback and total_size > 0:
                                    file_pct = downloaded / total_size
                                    overall = (i + file_pct) / total_pkgs
                                    mb_done = downloaded / (1024 * 1024)
                                    mb_total = total_size / (1024 * 1024)
                                    progress_callback(overall, f"{label} ({mb_done:.0f}/{mb_total:.0f} MB)")

                if progress_callback:
                    progress_callback((i + 0.95) / total_pkgs, f"Extraindo DLLs de {pkg_name}...")

                with zipfile.ZipFile(tmp_wheel, "r") as zf:
                    for member in zf.namelist():
                        if member.lower().endswith(".dll"):
                            filename = os.path.basename(member)
                            if filename:
                                target_path = os.path.join(cuda_dir, filename)
                                with zf.open(member) as src, open(target_path, "wb") as dst:
                                    shutil.copyfileobj(src, dst)

                try:
                    os.remove(tmp_wheel)
                except OSError:
                    pass

            except Exception as e:
                logger.error(f"Erro ao baixar/extrair {pkg_name}: {e}", exc_info=True)
                return False

        _register_nvidia_dll_paths()
        if progress_callback:
            progress_callback(1.0, "DLLs instaladas com sucesso!")
        logger.info("Suporte GPU instalado com sucesso na pasta cuda/.")
        return True

    @classmethod
    def uninstall_gpu_support(cls) -> bool:
        """Remove a pasta local 'cuda' com as DLLs NVIDIA."""
        import shutil
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cuda_dir = os.path.join(base_dir, "cuda")
        if os.path.exists(cuda_dir):
            try:
                shutil.rmtree(cuda_dir)
                logger.info("Pasta cuda/ removida com sucesso.")
                return True
            except Exception as e:
                logger.error(f"Erro ao remover pasta cuda/: {e}")
                return False
        return True
