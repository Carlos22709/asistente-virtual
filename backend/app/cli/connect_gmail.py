"""Autoriza Gmail mediante OAuth y guarda el token para el agente secretario."""

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from ..config import get_settings
from ..services.email import GMAIL_SCOPES


def main() -> None:
    settings = get_settings()
    client_secrets = Path(settings.gmail_client_secrets_file).resolve()
    token_file = Path(settings.gmail_token_file).resolve()

    if not client_secrets.is_file():
        raise SystemExit(
            "No encontré las credenciales OAuth de Google en "
            f"{client_secrets}. Descarga el JSON de una aplicación de escritorio y "
            "guárdalo con ese nombre."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets), scopes=GMAIL_SCOPES
    )
    credentials = flow.run_local_server(
        port=0,
        open_browser=True,
        access_type="offline",
        prompt="consent",
        authorization_prompt_message=(
            "Se abrirá Google para autorizar Gmail. Si no se abre, visita esta URL:\n{url}"
        ),
        success_message="Gmail quedó conectado. Ya puedes cerrar esta pestaña.",
    )

    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    print(f"Gmail conectado. Token guardado de forma local en {token_file}.")
    print("Este archivo está excluido de Git. No lo compartas.")


if __name__ == "__main__":
    main()
