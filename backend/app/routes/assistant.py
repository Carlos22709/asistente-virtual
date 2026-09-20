"""Endpoints de conversacion y transcripcion del asistente multiagente."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantTranscriptionResponse,
)
from ..services.llm import (
    InvalidLLMResponseError,
    LLMUnavailableError,
    OllamaToolCallingClient,
)
from ..services.email import GmailEmailService
from ..services.orchestrator import AssistantOrchestrator
from ..services.transcription import (
    AudioTranscriptionError,
    FasterWhisperTranscriber,
    TranscriptionUnavailableError,
)

router = APIRouter(prefix="/assistant", tags=["Asistente"])


@lru_cache
def get_orchestrator() -> AssistantOrchestrator:
    settings = get_settings()
    client = OllamaToolCallingClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
    email_service = GmailEmailService(settings.gmail_token_file)
    return AssistantOrchestrator(client, email_service=email_service)


@lru_cache
def get_transcriber() -> FasterWhisperTranscriber:
    settings = get_settings()
    return FasterWhisperTranscriber(
        model_name=settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


@router.post("/transcribe", response_model=AssistantTranscriptionResponse)
async def transcribe(
    audio: Annotated[UploadFile, File(description="Audio grabado desde el cliente móvil")],
    transcriber: Annotated[FasterWhisperTranscriber, Depends(get_transcriber)],
) -> AssistantTranscriptionResponse:
    settings = get_settings()
    try:
        content = await audio.read(settings.whisper_max_audio_bytes + 1)
    finally:
        await audio.close()

    if len(content) > settings.whisper_max_audio_bytes:
        raise HTTPException(status_code=413, detail="El audio supera el límite de 12 MB.")
    if not content:
        raise HTTPException(status_code=400, detail="El audio está vacío.")

    filename = Path(audio.filename or "voice.m4a").name
    try:
        result = await run_in_threadpool(transcriber.transcribe, content, filename)
    except AudioTranscriptionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TranscriptionUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "La transcripción local no está disponible. Revisa faster-whisper "
                "y la descarga del modelo configurado."
            ),
        ) from exc
    return AssistantTranscriptionResponse(text=result.text, language=result.language)


@router.post("/chat", response_model=AssistantChatResponse)
async def chat(
    payload: AssistantChatRequest,
    db: Annotated[Session, Depends(get_db)],
    orchestrator: Annotated[AssistantOrchestrator, Depends(get_orchestrator)],
) -> AssistantChatResponse:
    try:
        return await orchestrator.route(payload, db)
    except LLMUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "El modelo de lenguaje no está disponible. Comprueba que Ollama esté "
                "iniciado y que 'ollama list' muestre el modelo configurado."
            ),
        ) from exc
    except InvalidLLMResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail="El modelo no produjo una decisión de enrutamiento válida.",
        ) from exc
