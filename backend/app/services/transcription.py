"""Transcribe audio movil con Faster Whisper y elimina temporales al finalizar."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any


class AudioTranscriptionError(RuntimeError):
    """The uploaded audio is valid, but no useful speech could be extracted."""


class TranscriptionUnavailableError(RuntimeError):
    """The local transcription engine could not be loaded or executed."""


@dataclass(frozen=True)
class TranscriptionResult:
    """Texto reconocido y codigo de idioma detectado."""

    text: str
    language: str


class FasterWhisperTranscriber:
    """Carga Whisper bajo demanda y reutiliza una unica instancia segura."""

    _allowed_suffixes = {".aac", ".caf", ".m4a", ".mp3", ".mp4", ".ogg", ".wav", ".webm"}

    def __init__(self, model_name: str, device: str, compute_type: str) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._model: Any | None = None
        self._model_lock = Lock()

    def _get_model(self) -> Any:
        """Inicializa el modelo una sola vez incluso con solicitudes concurrentes."""

        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is not None:
                return self._model
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise TranscriptionUnavailableError(
                    "faster-whisper no está instalado."
                ) from exc
            try:
                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type,
                )
            except Exception as exc:
                raise TranscriptionUnavailableError(
                    "No fue posible cargar el modelo local de voz."
                ) from exc
        return self._model

    def transcribe(self, audio: bytes, filename: str | None = None) -> TranscriptionResult:
        """Transcribe bytes de audio y garantiza la eliminacion del temporal."""

        if not audio:
            raise AudioTranscriptionError("El audio está vacío.")

        suffix = Path(filename or "").suffix.lower()
        if suffix not in self._allowed_suffixes:
            suffix = ".m4a"

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
                temporary_file.write(audio)
                temporary_path = Path(temporary_file.name)

            model = self._get_model()
            segments, information = model.transcribe(
                str(temporary_path),
                language="es",
                beam_size=3,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
            if not text:
                raise AudioTranscriptionError(
                    "No se detectó una frase clara. Intenta hablar más cerca del micrófono."
                )
            return TranscriptionResult(
                text=text,
                language=getattr(information, "language", None) or "es",
            )
        except AudioTranscriptionError:
            raise
        except TranscriptionUnavailableError:
            raise
        except Exception as exc:
            raise TranscriptionUnavailableError(
                "No fue posible procesar el audio con el modelo local."
            ) from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
