"""
Player de áudio com suporte a fila, play/pause/stop.
Usa sounddevice para reprodução precisa e multiplataforma.
"""

import threading
import logging
import wave
import os
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class PlayerState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class AudioPlayer:
    """Player de áudio com controle de fila e estado."""

    def __init__(self):
        self._state = PlayerState.STOPPED
        self._queue: list[str] = []
        self._current_file: Optional[str] = None
        self._play_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Inicia sem pausa
        self._on_chunk_finished = None

    @property
    def state(self) -> PlayerState:
        return self._state

    def enqueue(self, audio_path: str) -> None:
        """Adiciona um arquivo de áudio à fila de reprodução."""
        self._queue.append(audio_path)

    def clear_queue(self) -> None:
        """Limpa a fila de reprodução."""
        self._queue.clear()

    def play(self, on_chunk_finished=None) -> None:
        """Inicia a reprodução da fila de áudio."""
        self._on_chunk_finished = on_chunk_finished
        if self._state == PlayerState.PAUSED:
            self._pause_event.set()
            self._state = PlayerState.PLAYING
            return

        self._stop_event.clear()
        self._pause_event.set()
        self._state = PlayerState.PLAYING
        self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self._play_thread.start()

    def pause(self) -> None:
        """Pausa a reprodução."""
        if self._state == PlayerState.PLAYING:
            self._pause_event.clear()
            self._state = PlayerState.PAUSED

    def stop(self) -> None:
        """Interrompe a reprodução e limpa a fila."""
        self._stop_event.set()
        self._pause_event.set()  # Destrava caso esteja pausado
        self._queue.clear()
        self._state = PlayerState.STOPPED

    def _play_loop(self) -> None:
        """Loop principal de reprodução da fila."""
        import numpy as np

        while self._queue and not self._stop_event.is_set():
            self._current_file = self._queue.pop(0)
            try:
                self._play_file(self._current_file)
            except Exception as e:
                logger.error(f"Erro ao reproduzir {self._current_file}: {e}")

            if self._on_chunk_finished:
                self._on_chunk_finished()

        if not self._stop_event.is_set():
            self._state = PlayerState.STOPPED

    def _play_file(self, file_path: str) -> None:
        """Reproduz um único arquivo WAV com suporte a pausa/stop."""
        import sounddevice as sd

        if not os.path.exists(file_path):
            logger.warning(f"Arquivo não encontrado: {file_path}")
            return

        with wave.open(file_path, "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

        import numpy as np
        dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
        dtype = dtype_map.get(sample_width, np.int16)
        audio_data = np.frombuffer(frames, dtype=dtype)

        if channels > 1:
            audio_data = audio_data.reshape(-1, channels)

        # Normalizar para float32 [-1, 1]
        audio_float = audio_data.astype(np.float32) / np.iinfo(dtype).max

        block_size = 1024
        pos = 0
        total = len(audio_float)

        while pos < total and not self._stop_event.is_set():
            self._pause_event.wait()  # Aguarda se pausado
            if self._stop_event.is_set():
                break

            end = min(pos + block_size, total)
            sd.play(audio_float[pos:end], sample_rate)
            sd.wait()
            pos = end

        sd.stop()
