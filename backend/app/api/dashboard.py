from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.schemas.api import DashboardSummary, UserContext
from app.services.evaluation import dashboard_summary

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


@router.get('/summary', response_model=DashboardSummary)
async def get_dashboard_summary(
    _: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardSummary:
    return DashboardSummary.model_validate(await dashboard_summary(session))
