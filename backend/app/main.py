from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_role
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import DatabaseManager
from app.schemas.api import EvaluateResponse
from app.services.evaluation import recompute_evaluations
from app.services.policies import ensure_component_types


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    db = DatabaseManager(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.auto_create_schema:
            await db.create_schema()
        async with db.session_factory() as session:
            await ensure_component_types(session)
            await session.commit()
        yield
        await db.dispose()

    app = FastAPI(title=settings.app_name, version='1.0.0', lifespan=lifespan)
    app.state.settings = settings
    app.state.db = db

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )

    @app.get('/healthz', tags=['platform'])
    async def healthcheck() -> dict[str, str]:
        return {'status': 'ok'}

    @app.post('/evaluate', response_model=EvaluateResponse, tags=['evaluation'], dependencies=[Depends(require_role('admin'))])
    async def evaluate(
        _: object = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> EvaluateResponse:
        evaluated_records, evaluated_at = await recompute_evaluations(session)
        await session.commit()
        return EvaluateResponse(evaluated_records=evaluated_records, evaluated_at=evaluated_at)

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
