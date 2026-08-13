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
import threading
from typing import Optional

from engines.base_engine import BaseEngine, EngineState, VoiceInfo

logger = logging.getLogger(__name__)


def _init_com_if_windows():
    """Garante que o COM Apartment esteja inicializado na thread atual no Windows."""
    if sys.platform == "win32":
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass


class NativeEngine(BaseEngine):
    """Motor de TTS nativo via pyttsx3 (SAPI5/NSSpeech/eSpeak)."""

    def __init__(self):
        self._engine = None
        self._state = EngineState.IDLE
        self._current_voice: Optional[str] = None
        self._rate: float = 1.0
        self._pitch: float = 1.0
        self._lock = threading.Lock()

    def initialize(self) -> None:
        with self._lock:
            _init_com_if_windows()
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", int(self._rate * 200))
                self._state = EngineState.IDLE
                logger.info("Motor nativo inicializado com sucesso.")
            except Exception as e:
                self._state = EngineState.ERROR
                logger.error(f"Falha ao inicializar motor nativo: {e}")
                raise

    def get_available_voices(self) -> list[VoiceInfo]:
        with self._lock:
            _init_com_if_windows()
            if not self._engine:
                try:
                    import pyttsx3
                    self._engine = pyttsx3.init()
                except Exception:
                    return []
            try:
                voices = self._engine.getProperty("voices") or []
            except Exception as e:
                logger.error(f"Erro ao obter vozes nativas: {e}")
                return []

            result = []
            for v in voices:
                lang = "unknown"
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
        with self._lock:
            _init_com_if_windows()
            self._current_voice = voice_id
            if self._engine:
                try:
                    self._engine.setProperty("voice", voice_id)
                except Exception as e:
                    logger.warning(f"Erro ao definir voz nativa {voice_id}: {e}")

    def set_rate(self, rate: float) -> None:
        with self._lock:
            _init_com_if_windows()
            self._rate = rate
            if self._engine:
                try:
                    self._engine.setProperty("rate", int(rate * 200))
                except Exception:
                    pass

    def set_pitch(self, pitch: float) -> None:
        with self._lock:
            _init_com_if_windows()
            self._pitch = pitch
            if self._engine:
                try:
                    self._engine.setProperty("volume", min(max(pitch, 0.0), 1.0))
                except Exception:
                    pass

    def synthesize(self, text: str) -> Optional[str]:
        with self._lock:
            _init_com_if_windows()
            if not self._engine:
                try:
                    import pyttsx3
                    self._engine = pyttsx3.init()
                except Exception as e:
                    logger.error(f"Não foi possível instanciar pyttsx3: {e}")
                    return None

            try:
                self._state = EngineState.SPEAKING
                import uuid

                # Reaplicar configurações
                if self._current_voice:
                    try:
                        self._engine.setProperty("voice", self._current_voice)
                    except Exception:
                        pass
                self._engine.setProperty("rate", int(self._rate * 200))
                self._engine.setProperty("volume", min(max(self._pitch, 0.0), 1.0))

                tmp_path = os.path.join(
                    tempfile.gettempdir(),
                    f"sn_native_{uuid.uuid4().hex[:8]}.wav",
                )
                self._engine.save_to_file(text, tmp_path)
                
                # Executar ciclo de processamento com segurança
                loop_started = False
                try:
                    self._engine.startLoop(False)
                    loop_started = True
                    self._engine.iterate()
                finally:
                    if loop_started:
                        try:
                            self._engine.endLoop()
                        except Exception:
                            pass

                self._state = EngineState.IDLE
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    return tmp_path
                return None
            except Exception as e:
                self._state = EngineState.ERROR
                logger.error(f"Erro na síntese nativa: {e}", exc_info=True)
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
