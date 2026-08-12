"""
Motor base abstrato para todos os engines de TTS.
Define a interface comum que todo motor deve implementar.
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class EngineState(Enum):
    IDLE = "idle"
    SPEAKING = "speaking"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class VoiceInfo:
    """Informações de uma voz disponível."""
    id: str
    name: str
    language: str
    gender: Optional[str] = None
    engine_type: str = ""


class BaseEngine(ABC):
    """Interface abstrata para motores de síntese de voz."""

    @abstractmethod
    def initialize(self) -> None:
        """Inicializa o motor e carrega recursos necessários."""
        ...

    @abstractmethod
    def get_available_voices(self) -> list[VoiceInfo]:
        """Retorna lista de vozes disponíveis para este motor."""
        ...

    @abstractmethod
    def set_voice(self, voice_id: str) -> None:
        """Define a voz ativa pelo seu ID."""
        ...

    @abstractmethod
    def set_rate(self, rate: float) -> None:
        """Define a velocidade de fala (0.5 = metade, 1.0 = normal, 2.0 = dobro)."""
        ...

    @abstractmethod
    def set_pitch(self, pitch: float) -> None:
        """Define o tom da voz (0.5 = grave, 1.0 = normal, 2.0 = agudo)."""
        ...

    @abstractmethod
    def synthesize(self, text: str) -> Optional[str]:
        """
        Sintetiza texto em áudio.
        Retorna o caminho do arquivo de áudio temporário gerado,
        ou None em caso de erro.
        """
        ...

    @abstractmethod
    def synthesize_stream(self, text: str):
        """
        Sintetiza texto e retorna um gerador de chunks de áudio (bytes).
        Usado para streaming em tempo real.
        """
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Libera recursos do motor."""
        ...

    @property
    @abstractmethod
    def state(self) -> EngineState:
        """Retorna o estado atual do motor."""
        ...

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Nome legível do motor (ex: 'Nativo (SAPI5)')."""
        ...
