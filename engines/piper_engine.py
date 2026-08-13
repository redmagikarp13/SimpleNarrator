"""
Motor Piper TTS.
Utiliza modelos ONNX para síntese de voz offline de alta qualidade.
"""
import os
import uuid
import tempfile
import logging
import threading
from typing import Optional, List

from engines.base_engine import BaseEngine, EngineState, VoiceInfo

logger = logging.getLogger(__name__)


def _register_nvidia_dll_paths():
    """Registra todos os diretórios de DLLs NVIDIA (cuDNN, cuBLAS, NVRTC) para o ONNX Runtime."""
    try:
        import nvidia
        nvidia_root = nvidia.__path__[0]
        dirs_to_add = []
        for pkg_name in os.listdir(nvidia_root):
            bin_dir = os.path.join(nvidia_root, pkg_name, "bin")
            if os.path.isdir(bin_dir):
                dirs_to_add.append(bin_dir)
        for path in dirs_to_add:
            os.add_dll_directory(path)
        # Também adicionar ao PATH para garantir que dependências cruzadas sejam encontradas
        if dirs_to_add:
            current_path = os.environ.get("PATH", "")
            os.environ["PATH"] = os.pathsep.join(dirs_to_add + [current_path])
            logger.info(f"DLLs NVIDIA registrados no PATH ({len(dirs_to_add)} diretórios): {[os.path.basename(os.path.dirname(d)) for d in dirs_to_add]}")
    except ImportError:
        logger.debug("Pacote nvidia não encontrado, usando DLLs do sistema.")
    except Exception as e:
        logger.debug(f"Erro ao registrar DLLs NVIDIA: {e}")

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
                self._voice_id = None
                self.set_voice(curr_voice)

    def initialize(self) -> None:
        """Piper não precisa de inicialização global, apenas carregar o modelo."""
        try:
            logging.getLogger("piper").setLevel(logging.WARNING)
            logging.getLogger("piper.voice").setLevel(logging.WARNING)
            from piper.voice import PiperVoice
            self._state = EngineState.IDLE
        except ImportError:
            logger.error("piper-tts não instalado. Execute: pip install piper-tts")
            self._state = EngineState.ERROR

    def get_available_voices(self) -> List[VoiceInfo]:
        """Lista as vozes .onnx disponíveis na pasta models."""
        if not os.path.exists(self.models_dir):
            return []

        voices = []
        for file in os.listdir(self.models_dir):
            if file.endswith(".onnx"):
                voice_id = file.replace(".onnx", "")
                json_path = os.path.join(self.models_dir, f"{voice_id}.onnx.json")
                if os.path.exists(json_path):
                    voices.append(VoiceInfo(id=voice_id, name=f"Piper: {voice_id}", language="IA"))
        return voices

    def set_voice(self, voice_id: str) -> None:
        """Carrega o modelo ONNX em memória (CPU ou GPU)."""
        if self._voice_id == voice_id and self._voice is not None:
            return

        onnx_path = os.path.join(self.models_dir, f"{voice_id}.onnx")
        config_path = os.path.join(self.models_dir, f"{voice_id}.onnx.json")

        if not os.path.exists(onnx_path) or not os.path.exists(config_path):
            logger.error(f"Arquivos da voz {voice_id} não encontrados.")
            return

        try:
            from piper.voice import PiperVoice
            if self.use_cuda:
                _register_nvidia_dll_paths()
            self._voice = PiperVoice.load(onnx_path, config_path, use_cuda=self.use_cuda)
            self._voice_id = voice_id
            logger.info(f"Voz Piper carregada (use_cuda={self.use_cuda}): {voice_id}")
        except Exception as e:
            logger.error(f"Erro ao carregar voz {voice_id} (use_cuda={self.use_cuda}): {e}")
            if self.use_cuda:
                logger.info("Tentando fallback para CPU...")
                try:
                    self._voice = PiperVoice.load(onnx_path, config_path, use_cuda=False)
                    self._voice_id = voice_id
                    logger.info(f"Voz Piper carregada em fallback CPU: {voice_id}")
                except Exception as e2:
                    logger.error(f"Erro no fallback CPU: {e2}")
                    self._voice = None
            else:
                self._voice = None

    def set_rate(self, rate: float) -> None:
        """
        No Piper, a velocidade é controlada pelo 'length_scale'.
        1.0 é o padrão. Valores < 1.0 são mais rápidos, > 1.0 são mais lentos.
        O rate do UI vai de 0.5 a 2.0 (onde 2.0 = 2x mais rápido).
        Então length_scale = 1.0 / rate
        """
        if rate <= 0:
            rate = 1.0
        self._rate_scale = 1.0 / rate

    def set_pitch(self, pitch: float) -> None:
        """Piper TTS (ONNX) não suporta controle de pitch nativamente de forma simples."""
        pass

    def synthesize(self, text: str) -> Optional[str]:
        """Sintetiza texto e retorna o caminho do arquivo WAV."""
        if self._voice is None:
            logger.error("Nenhuma voz Piper carregada.")
            return None

        self._state = EngineState.SPEAKING
        temp_file = os.path.join(tempfile.gettempdir(), f"sn_piper_{uuid.uuid4().hex}.wav")
        
        try:
            from piper.config import SynthesisConfig
            syn_config = SynthesisConfig(length_scale=self._rate_scale)
        except Exception:
            syn_config = None

        try:
            import wave
            wav_file = None
            with self._synth_lock:
                try:
                    for chunk in self._voice.synthesize(text, syn_config=syn_config):
                        if wav_file is None:
                            wav_file = wave.open(temp_file, "wb")
                            wav_file.setnchannels(chunk.sample_channels)
                            wav_file.setsampwidth(chunk.sample_width)
                            wav_file.setframerate(chunk.sample_rate)
                        wav_file.writeframes(chunk.audio_int16_bytes)
                finally:
                    if wav_file:
                        wav_file.close()

            if wav_file and os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                self._state = EngineState.IDLE
                return temp_file
            else:
                logger.warning("Nenhum chunk de áudio gerado pelo Piper.")
                self._state = EngineState.IDLE
                # Limpar arquivo vazio se existir
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except OSError:
                    pass
                return None
        except Exception as e:
            logger.error(f"Erro ao sintetizar via Piper: {e}", exc_info=True)
            # Se estava usando CUDA e falhou, tentar fallback para CPU
            if self.use_cuda and self._voice_id:
                logger.info("Tentando fallback de síntese para CPU...")
                try:
                    self._reload_voice_cpu_fallback()
                    # Tentar síntese novamente em CPU
                    wav_file = None
                    with self._synth_lock:
                        try:
                            for chunk in self._voice.synthesize(text, syn_config=syn_config):
                                if wav_file is None:
                                    wav_file = wave.open(temp_file, "wb")
                                    wav_file.setnchannels(chunk.sample_channels)
                                    wav_file.setsampwidth(chunk.sample_width)
                                    wav_file.setframerate(chunk.sample_rate)
                                wav_file.writeframes(chunk.audio_int16_bytes)
                        finally:
                            if wav_file:
                                wav_file.close()
                    if wav_file and os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                        logger.info("Fallback para CPU bem-sucedido.")
                        self._state = EngineState.IDLE
                        return temp_file
                except Exception as e2:
                    logger.error(f"Fallback para CPU também falhou: {e2}", exc_info=True)
            self._state = EngineState.ERROR
            return None

    def _reload_voice_cpu_fallback(self):
        """Recarrega a voz atual em modo CPU como fallback."""
        if not self._voice_id:
            return
        from piper.voice import PiperVoice
        onnx_path = os.path.join(self.models_dir, f"{self._voice_id}.onnx")
        config_path = os.path.join(self.models_dir, f"{self._voice_id}.onnx.json")
        self._voice = PiperVoice.load(onnx_path, config_path, use_cuda=False)
        logger.info(f"Voz recarregada em CPU (fallback): {self._voice_id}")

    def synthesize_stream(self, text: str):
        """Streaming de áudio - retorna iterator de bytes raw PCM."""
        if self._voice is None:
            return iter([])

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
