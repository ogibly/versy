from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, get_settings, require_role
from app.core.config import Settings
from app.schemas.api import IngestRunRequest, IngestionRunRead, UserContext
from app.services.ingestion.service import ingest_file_bytes, ingest_from_runzero_api, list_ingestion_runs

router = APIRouter(prefix='/ingest', tags=['ingestion'])


@router.post('/runzero', response_model=IngestionRunRead, dependencies=[Depends(require_role('admin'))])
async def trigger_runzero_ingestion(
    payload: IngestRunRequest,
    _: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> IngestionRunRead:
    run = await ingest_from_runzero_api(session, settings, search=payload.search, fields=payload.fields)
    await session.commit()
    return IngestionRunRead.model_validate(run)


@router.post('/file', response_model=IngestionRunRead, dependencies=[Depends(require_role('admin'))])
async def ingest_file(
    file: UploadFile = File(...),
    _: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> IngestionRunRead:
    run = await ingest_file_bytes(session, settings, data=await file.read())
    await session.commit()
    return IngestionRunRead.model_validate(run)


@router.get('/runs', response_model=list[IngestionRunRead])
async def get_ingestion_runs(
    _: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[IngestionRunRead]:
    runs = await list_ingestion_runs(session)
    return [IngestionRunRead.model_validate(run) for run in runs]
