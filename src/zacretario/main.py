import hmac
import json
import logging
from datetime import UTC, datetime

import anthropic
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

import zacretario.agent  # noqa: F401  (registers all skills)
from zacretario.agent.agent import Agent
from zacretario.agent.registry import all_tools
from zacretario.calendar.base import CalendarProvider
from zacretario.calendar.google import build_google_provider
from zacretario.channels.whatsapp import WhatsAppClient, parse_webhook, verify_signature
from zacretario.config import Settings, get_settings
from zacretario.db import make_session_factory
from zacretario.repositories.credentials import get_refresh_token
from zacretario.service import Deps, handle_message

logger = logging.getLogger(__name__)


def create_app(deps: Deps) -> FastAPI:
    app = FastAPI(title="Zacretário")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/webhook")
    def verify_webhook(request: Request) -> PlainTextResponse:
        params = request.query_params
        if params.get("hub.mode") == "subscribe" and hmac.compare_digest(
            params.get("hub.verify_token", "").encode(),
            deps.settings.whatsapp_verify_token.encode(),
        ):
            return PlainTextResponse(params.get("hub.challenge", ""))
        raise HTTPException(status_code=403)

    @app.post("/webhook")
    async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256")
        if not verify_signature(deps.settings.whatsapp_app_secret, body, signature):
            raise HTTPException(status_code=401)
        try:
            payload = json.loads(body)
        except ValueError:
            # Always 200 so Meta does not keep retrying a payload we can never parse.
            logger.warning("Ignoring webhook with invalid JSON body")
            return {"status": "ok"}
        if not isinstance(payload, dict):
            logger.warning("Ignoring webhook with unexpected payload shape")
            return {"status": "ok"}
        for message in parse_webhook(payload):
            background_tasks.add_task(handle_message, message, deps)
        return {"status": "ok"}

    return app


def build_deps(settings: Settings) -> Deps:
    def calendar_for(session: Session, owner: str) -> CalendarProvider:
        token = get_refresh_token(session, owner)
        if token is None:
            raise RuntimeError(
                f"Google não autorizado para {owner}: rode scripts/authorize_google.py"
            )
        return build_google_provider(token, settings)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return Deps(
        settings=settings,
        session_factory=make_session_factory(settings.database_url),
        agent=Agent(client, settings.anthropic_model, all_tools()),
        sender=WhatsAppClient(
            settings.whatsapp_access_token,
            settings.whatsapp_phone_number_id,
            settings.whatsapp_api_version,
        ),
        calendar_for=calendar_for,
        clock=lambda: datetime.now(UTC),
    )


def get_app() -> FastAPI:
    """uvicorn factory: `uvicorn zacretario.main:get_app --factory`."""
    logging.basicConfig(level=logging.INFO)
    return create_app(build_deps(get_settings()))
