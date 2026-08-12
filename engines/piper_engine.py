"""
Motor Piper TTS.
Utiliza modelos ONNX para síntese de voz offline de alta qualidade.
"""
import os
import uuid
import tempfile
import logging
from typing import Optional, List

from engines.base_engine import BaseEngine, EngineState, VoiceInfo

logger = logging.getLogger(__name__)

class PiperEngine(BaseEngine):
    """Motor de TTS baseado no Piper TTS (modelos ONNX)."""

    def __init__(self, models_dir: str = "models"):
        self._state = EngineState.IDLE
        self.models_dir = os.path.abspath(models_dir)
        self._voice_id: Optional[str] = None
        self._voice = None
        self._rate_scale = 1.0  # Piper usa length_scale (maior = mais lento)
        self.use_cuda = False

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
            import wave
            wav_file = None
            for chunk in self._voice.synthesize(text):
                if wav_file is None:
                    wav_file = wave.open(temp_file, "wb")
                    wav_file.setnchannels(chunk.sample_channels)
                    wav_file.setsampwidth(chunk.sample_width)
                    wav_file.setframerate(chunk.sample_rate)
                wav_file.writeframes(chunk.audio_int16_bytes)

            if wav_file:
                wav_file.close()
                self._state = EngineState.IDLE
                return temp_file
            else:
                logger.warning("Nenhum chunk de áudio gerado pelo Piper.")
                self._state = EngineState.IDLE
                return None
        except Exception as e:
            logger.error(f"Erro ao sintetizar via Piper: {e}")
            self._state = EngineState.ERROR
            return None

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
