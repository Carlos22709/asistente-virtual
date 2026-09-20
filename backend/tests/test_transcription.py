"""Pruebas del endpoint de transcripcion con un transcriptor controlado."""

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

temporary_directory = tempfile.TemporaryDirectory()
database_path = Path(temporary_directory.name) / "transcription_test.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")

from app.main import app  # noqa: E402
from app.routes.assistant import get_transcriber  # noqa: E402
from app.services.transcription import TranscriptionResult  # noqa: E402


class FakeTranscriber:
    def transcribe(self, audio: bytes, filename: str | None = None) -> TranscriptionResult:
        if not audio:
            raise AssertionError("El endpoint debe rechazar audio vacío antes del servicio")
        return TranscriptionResult(
            text="¿Cuánto dinero me queda este mes?",
            language="es",
        )


class TranscriptionApiTest(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_transcriber] = FakeTranscriber

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_transcriber, None)

    def test_transcribes_a_mobile_audio_upload(self) -> None:
        client = TestClient(app)
        try:
            response = client.post(
                "/assistant/transcribe",
                files={"audio": ("voice.m4a", b"fake-audio", "audio/m4a")},
            )
        finally:
            client.close()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"text": "¿Cuánto dinero me queda este mes?", "language": "es"},
        )

    def test_rejects_an_empty_audio_upload(self) -> None:
        client = TestClient(app)
        try:
            response = client.post(
                "/assistant/transcribe",
                files={"audio": ("voice.m4a", b"", "audio/m4a")},
            )
        finally:
            client.close()
        self.assertEqual(response.status_code, 400)


def tearDownModule() -> None:
    temporary_directory.cleanup()
