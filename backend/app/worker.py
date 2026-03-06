from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.core.database import DatabaseManager
from app.services.ingestion.service import ingest_from_runzero_api
from app.services.policies import ensure_component_types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def worker_loop() -> None:
    settings = get_settings()
    db = DatabaseManager(settings.database_url)
    try:
        while True:
            if not settings.runzero_schedule_enabled:
                logger.info('RunZero schedule disabled; sleeping.')
            elif not settings.runzero_export_token:
                logger.warning('RunZero export token missing; skipping scheduled pull.')
            else:
                try:
                    async with db.session_factory() as session:
                        await ensure_component_types(session)
                        await ingest_from_runzero_api(session, settings)
                        await session.commit()
                        logger.info('Scheduled runZero ingestion completed successfully.')
                except Exception:
                    logger.exception('Scheduled runZero ingestion failed.')
            await asyncio.sleep(max(settings.runzero_schedule_interval_minutes, 1) * 60)
    finally:
        await db.dispose()


if __name__ == '__main__':
    asyncio.run(worker_loop())
