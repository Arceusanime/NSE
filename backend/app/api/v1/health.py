from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.api import HealthDTO
from app.services.calendar.service import MarketCalendar
from app.services.market_data.base import MarketDataProvider
from app.core.dependencies import get_provider

router = APIRouter()


@router.get("/health", response_model=HealthDTO)
async def health(session: AsyncSession = Depends(get_session), provider: MarketDataProvider = Depends(get_provider)):
    try:
        await session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"
    return HealthDTO(
        status="ok" if database == "ok" else "degraded",
        database=database,
        market_session=MarketCalendar().session_status(datetime.now(ZoneInfo("Asia/Kolkata"))),
        provider=provider.name,
        provider_status=await provider.get_status(),
    )
