"""Abstrae Gmail y convierte mensajes remotos en objetos del dominio."""

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials
from requests import RequestException


GMAIL_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
)
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class EmailNotConfiguredError(RuntimeError):
    """La cuenta de Gmail todavía no fue autorizada."""


class EmailServiceError(RuntimeError):
    """Gmail no pudo completar la operación solicitada."""


@dataclass(frozen=True)
class MailMessage:
    id: str
    thread_id: str
    sender: str
    subject: str
    received_at: datetime | None
    snippet: str
    body: str


@dataclass(frozen=True)
class MailDraft:
    id: str
    to: str
    subject: str


@dataclass(frozen=True)
class SentMail:
    id: str
    thread_id: str


class EmailService(Protocol):
    def list_unread(self, limit: int = 5) -> list[MailMessage]: ...

    def search(self, query: str, limit: int = 5) -> list[MailMessage]: ...

    def get_thread(self, thread_id: str) -> list[MailMessage]: ...

    def create_draft(self, to: str, subject: str, body: str) -> MailDraft: ...

    def send_draft(self, draft_id: str) -> SentMail: ...


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _decode_body(data: str) -> str:
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="replace")
    except (ValueError, UnicodeError):
        return ""


def _plain_text(payload: dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")
    if mime_type == "text/plain" and body_data:
        return _decode_body(body_data)

    parts = payload.get("parts", [])
    for part in parts:
        text = _plain_text(part)
        if text:
            return text

    if mime_type == "text/html" and body_data:
        parser = _TextExtractor()
        parser.feed(_decode_body(body_data))
        return unescape("\n".join(parser.parts))
    return ""


def _header(payload: dict[str, Any], name: str) -> str:
    for item in payload.get("headers", []):
        if item.get("name", "").lower() == name.lower():
            return str(item.get("value", ""))
    return ""


def _message_from_payload(payload: dict[str, Any]) -> MailMessage:
    content = payload.get("payload", {})
    received_at: datetime | None = None
    date_header = _header(content, "Date")
    if date_header:
        try:
            received_at = parsedate_to_datetime(date_header)
        except (TypeError, ValueError):
            received_at = None
    if received_at is None and payload.get("internalDate"):
        try:
            received_at = datetime.fromtimestamp(
                int(payload["internalDate"]) / 1000, tz=timezone.utc
            )
        except (TypeError, ValueError, OSError):
            received_at = None

    return MailMessage(
        id=str(payload.get("id", "")),
        thread_id=str(payload.get("threadId", "")),
        sender=_header(content, "From") or "Remitente desconocido",
        subject=_header(content, "Subject") or "(Sin asunto)",
        received_at=received_at,
        snippet=str(payload.get("snippet", "")),
        body=_plain_text(content)[:8_000],
    )


class GmailEmailService:
    def __init__(self, token_file: str | Path) -> None:
        self.token_file = Path(token_file)

    def _credentials(self) -> Credentials:
        if not self.token_file.is_file():
            raise EmailNotConfiguredError(
                "Falta autorizar Gmail. Ejecuta scripts/connect-gmail.ps1."
            )
        try:
            return Credentials.from_authorized_user_file(
                str(self.token_file), scopes=GMAIL_SCOPES
            )
        except (ValueError, OSError, GoogleAuthError) as exc:
            raise EmailNotConfiguredError(
                "El archivo de autorización de Gmail no es válido."
            ) from exc

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        credentials = self._credentials()
        try:
            with AuthorizedSession(credentials) as session:
                response = session.request(
                    method,
                    f"{GMAIL_API_BASE}/{path.lstrip('/')}",
                    params=params,
                    json=json,
                    timeout=20,
                )
                response.raise_for_status()
                result = response.json()
        except (GoogleAuthError, RequestException, ValueError) as exc:
            raise EmailServiceError("No fue posible comunicarse con Gmail.") from exc

        if not isinstance(result, dict):
            raise EmailServiceError("Gmail devolvió una respuesta inesperada.")
        return result

    def _list(self, query: str, limit: int) -> list[MailMessage]:
        result = self._request(
            "GET", "messages", params={"q": query, "maxResults": limit}
        )
        messages: list[MailMessage] = []
        for item in result.get("messages", []):
            message_id = item.get("id")
            if not message_id:
                continue
            detail = self._request(
                "GET", f"messages/{message_id}", params={"format": "full"}
            )
            messages.append(_message_from_payload(detail))
        return messages

    def list_unread(self, limit: int = 5) -> list[MailMessage]:
        return self._list("is:unread", limit)

    def search(self, query: str, limit: int = 5) -> list[MailMessage]:
        return self._list(query, limit)

    def get_thread(self, thread_id: str) -> list[MailMessage]:
        result = self._request(
            "GET", f"threads/{thread_id}", params={"format": "full"}
        )
        return [_message_from_payload(item) for item in result.get("messages", [])]

    def create_draft(self, to: str, subject: str, body: str) -> MailDraft:
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        result = self._request(
            "POST", "drafts", json={"message": {"raw": raw}}
        )
        draft_id = str(result.get("id", ""))
        if not draft_id:
            raise EmailServiceError("Gmail no devolvió el identificador del borrador.")
        return MailDraft(id=draft_id, to=to, subject=subject)

    def send_draft(self, draft_id: str) -> SentMail:
        result = self._request("POST", "drafts/send", json={"id": draft_id})
        message_id = str(result.get("id", ""))
        if not message_id:
            raise EmailServiceError("Gmail no confirmó el envío del borrador.")
        return SentMail(id=message_id, thread_id=str(result.get("threadId", "")))
