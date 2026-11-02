from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_provider
from app.core.database import get_session
from app.models.domain import InstrumentAnalysis
from app.repositories.scans import ScanRepository
from app.schemas.api import ScanListDTO, ScanRequest, ScanResultDTO
from app.services.market_data.base import MarketDataProvider
from app.services.scanning.service import ScannerService

router = APIRouter()


@router.get("/scans/latest", response_model=ScanListDTO)
async def latest_scan(
    search: str | None = Query(default=None),
    instrument_type: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    run = await ScanRepository(session).latest_run()
    if run is None:
        return ScanListDTO(scan_id=0, target_trading_date=None, status="EMPTY", total_instruments=0, successful_instruments=0, created_at=None, items=[], total=0)  # type: ignore[arg-type]
    items = [x for x in run.results if (not search or search.upper() in x.symbol.upper()) and (not instrument_type or x.instrument_type == instrument_type.upper())]
    return ScanListDTO(
        scan_id=run.scan_id,
        target_trading_date=run.target_trading_date,
        status=run.status,
        total_instruments=run.total_instruments,
        successful_instruments=run.successful_instruments,
        created_at=run.created_at,
        items=[ScanResultDTO.model_validate(item) for item in items],
        total=len(items),
    )


@router.post("/scans", response_model=dict)
async def trigger_scan(
    request: ScanRequest | None = None,
    session: AsyncSession = Depends(get_session),
    provider: MarketDataProvider = Depends(get_provider),
):
    request = request or ScanRequest()
    scan_id = await ScannerService(ScanRepository(session), provider).run(request.target_trading_date, request.levels)
    return {"scan_id": scan_id, "status": "COMPLETED"}
