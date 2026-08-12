"""
Motor nativo multiplataforma usando pyttsx3.
Utiliza as APIs de acessibilidade do sistema operacional:
  - Windows: SAPI5
  - macOS: NSSpeechSynthesizer
  - Linux: eSpeak-NG / Speech-Dispatcher
"""

import os
import sys
import platform
import tempfile
import wave
import logging
from typing import Optional

from engines.base_engine import BaseEngine, EngineState, VoiceInfo

logger = logging.getLogger(__name__)


class NativeEngine(BaseEngine):
    """Motor de TTS nativo via pyttsx3 (SAPI5/NSSpeech/eSpeak)."""

    def __init__(self):
        self._engine = None
        self._state = EngineState.IDLE
        self._current_voice: Optional[str] = None
        self._rate: float = 1.0
        self._pitch: float = 1.0

    def initialize(self) -> None:
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            # Aplicar configurações padrão
            self._engine.setProperty("rate", int(self._rate * 200))
            self._state = EngineState.IDLE
            logger.info("Motor nativo inicializado com sucesso.")
        except Exception as e:
            self._state = EngineState.ERROR
            logger.error(f"Falha ao inicializar motor nativo: {e}")
            raise

    def get_available_voices(self) -> list[VoiceInfo]:
        if not self._engine:
            return []
        voices = self._engine.getProperty("voices") or []
        result = []
        for v in voices:
            lang = "unknown"
            # pyttsx3 retorna idiomas de formas diferentes por SO
            if hasattr(v, "languages") and v.languages:
                lang = v.languages[0] if isinstance(v.languages, list) else v.languages
            result.append(
                VoiceInfo(
                    id=v.id,
                    name=v.name,
                    language=str(lang),
                    gender=getattr(v, "gender", None),
                    engine_type="native",
                )
            )
        return result

    def set_voice(self, voice_id: str) -> None:
        if self._engine:
            self._engine.setProperty("voice", voice_id)
            self._current_voice = voice_id

    def set_rate(self, rate: float) -> None:
        self._rate = rate
        if self._engine:
            # pyttsx3 usa words-per-minute (~200 = normal)
            self._engine.setProperty("rate", int(rate * 200))

    def set_pitch(self, pitch: float) -> None:
        self._pitch = pitch
        if self._engine:
            # pyttsx3 usa volume como proxy; pitch real depende do SO
            self._engine.setProperty("volume", min(max(pitch, 0.0), 1.0))

    def synthesize(self, text: str) -> Optional[str]:
        if not self._engine:
            return None
        try:
            self._state = EngineState.SPEAKING
            import uuid

            tmp_path = os.path.join(
                tempfile.gettempdir(),
                f"sn_native_{uuid.uuid4().hex[:8]}.wav",
            )
            self._engine.save_to_file(text, tmp_path)
            # Usar iterate() em vez de runAndWait() para evitar
            # o bug conhecido do pyttsx3 que trava no segundo uso.
            self._engine.startLoop(False)
            self._engine.iterate()
            self._engine.endLoop()
            self._state = EngineState.IDLE
            return tmp_path
        except Exception as e:
            self._state = EngineState.ERROR
            logger.error(f"Erro na síntese nativa: {e}")
            return None

    def synthesize_stream(self, text: str):
        # pyttsx3 não suporta streaming nativo;
        # gera o arquivo completo e retorna os bytes.
        audio_path = self.synthesize(text)
        if audio_path and os.path.exists(audio_path):
            with wave.open(audio_path, "rb") as wf:
                chunk_size = 4096
                data = wf.readframes(chunk_size)
                while data:
                    yield data
                    data = wf.readframes(chunk_size)

    def shutdown(self) -> None:
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
            self._engine = None
        self._state = EngineState.IDLE

    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def engine_name(self) -> str:
        system = platform.system()
        api_map = {
            "Windows": "SAPI5",
            "Darwin": "NSSpeech",
            "Linux": "eSpeak",
        }
        api = api_map.get(system, "Desconhecido")
        return f"Nativo do S.O. ({api} - Apenas CPU)"
