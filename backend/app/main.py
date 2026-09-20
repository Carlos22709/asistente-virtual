"""Construye la aplicacion FastAPI, sus rutas y protecciones transversales."""

from contextlib import asynccontextmanager
from hmac import compare_digest
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import models  # noqa: F401 - registra los modelos antes de crear tablas
from .config import get_settings
from .database import Base, engine
from .services.database_security import secure_supabase_tables
from .routes import (
    assistant,
    budgets,
    dashboard,
    events,
    expenses,
    financial_accounts,
    financial_planning,
    incomes,
    savings_goals,
    system,
    tasks,
    webhooks,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepara el esquema y endurece permisos antes de aceptar solicitudes."""

    Base.metadata.create_all(bind=engine)
    if get_settings().uses_supabase:
        secure_supabase_tables(engine)
    yield


app = FastAPI(
    title="Kirby Assistant API",
    description="API personal con orquestación por IA, tareas, gastos, presupuestos y agenda.",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=settings.allowed_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(expenses.router)
app.include_router(incomes.router)
app.include_router(financial_accounts.router)
app.include_router(financial_planning.router)
app.include_router(savings_goals.router)
app.include_router(budgets.router)
app.include_router(events.router)
app.include_router(dashboard.router)
app.include_router(assistant.router)
app.include_router(webhooks.router)
app.include_router(system.router)


@app.middleware("http")
async def protect_and_trace_requests(request: Request, call_next):
    """Autentica rutas privadas y agrega trazabilidad sin registrar secretos."""

    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started = perf_counter()
    public_path = request.url.path in {"/health", "/docs", "/openapi.json", "/redoc"}
    is_webhook = request.url.path.startswith("/webhooks/")
    if (
        settings.app_api_token
        and request.method != "OPTIONS"
        and not public_path
        and not is_webhook
    ):
        authorization = request.headers.get("Authorization", "")
        supplied = (
            authorization[7:]
            if authorization.lower().startswith("bearer ")
            else request.headers.get("X-API-Key", "")
        )
        # La comparacion constante evita filtrar informacion temporal del token.
        if not supplied or not compare_digest(supplied, settings.app_api_token):
            return JSONResponse(
                status_code=401,
                content={"detail": "Token personal inválido o ausente"},
                headers={"X-Request-ID": request_id},
            )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{(perf_counter() - started) * 1000:.2f}"
    return response


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado en %s", request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Ocurrió un error interno"})
