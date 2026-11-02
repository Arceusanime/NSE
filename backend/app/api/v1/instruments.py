from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.domain import HistogramStrike, Instrument, InstrumentAnalysis, InstrumentType, LevelSide, SelectedStrikeLevel
from app.repositories.scans import ScanRepository
from app.schemas.api import AnalysisDTO, HistogramDTO, LevelDTO, PineDataDTO
from app.services.pine import PINE_SCRIPT, format_pine_data

router = APIRouter()


def _analysis(result, levels: int) -> InstrumentAnalysis:
    all_levels = [
        SelectedStrikeLevel(
            strike_price=x.strike_price,
            oi=x.oi,
            oi_change=x.oi_change,
            side=LevelSide(x.side),
            point_gap=x.point_gap,
            percentage_gap=x.percentage_gap,
            rank_within_side=x.rank_within_side,
            call_oi=x.call_oi,
            put_oi=x.put_oi,
        )
        for x in result.levels
    ]
    upper = tuple(x for x in all_levels if x.side is LevelSide.UPPER and x.rank_within_side <= levels)
    lower = tuple(x for x in all_levels if x.side is LevelSide.LOWER and x.rank_within_side <= levels)
    histogram = tuple(
        HistogramStrike(
            strike_price=Decimal(x["strike_price"]),
            call_oi=x["call_oi"],
            put_oi=x["put_oi"],
            selected_side=LevelSide(x["selected_side"]) if x.get("selected_side") else None,
            selected_rank=x.get("selected_rank"),
        )
        for x in json.loads(result.histogram_json)
    )
    return InstrumentAnalysis(
        instrument=Instrument(result.symbol, result.instrument_name, InstrumentType(result.instrument_type)),
        session_date=result.scan.target_trading_date,
        expiry=result.expiry,
        previous_open_price=result.previous_open_price,
        atm_strike=result.atm_strike,
        upper_levels=upper,
        lower_levels=lower,
        histogram=histogram,
    )


@router.get("/instruments/pine-script-code")
async def pine_script_code() -> dict[str, str]:
    return {"language": "pine", "version": "5", "code": PINE_SCRIPT}


@router.get("/instruments/{symbol}/analysis", response_model=AnalysisDTO)
async def instrument_analysis(symbol: str, levels: int = Query(default=3, ge=1, le=5), session: AsyncSession = Depends(get_session)):
    result = await ScanRepository(session).find_result(symbol)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No scan result for {symbol.upper()}")
    analysis = _analysis(result, levels)
    return AnalysisDTO(
        symbol=analysis.instrument.symbol,
        name=analysis.instrument.name,
        instrument_type=analysis.instrument.instrument_type.value,
        session_date=analysis.session_date,
        expiry=analysis.expiry,
        previous_open_price=analysis.previous_open_price,
        atm_strike=analysis.atm_strike,
        max_point_gap=analysis.max_point_gap,
        macro_spread=analysis.macro_spread,
        upper_levels=[LevelDTO.model_validate(x) for x in analysis.upper_levels],
        lower_levels=[LevelDTO.model_validate(x) for x in analysis.lower_levels],
        histogram=[HistogramDTO.model_validate(x) for x in analysis.histogram],
    )


@router.get("/instruments/{symbol}/pine-data", response_model=PineDataDTO)
async def pine_data(symbol: str, levels: int = Query(default=3, ge=1, le=5), session: AsyncSession = Depends(get_session)):
    result = await ScanRepository(session).find_result(symbol)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No scan result for {symbol.upper()}")
    analysis = _analysis(result, levels)
    return PineDataDTO(symbol=analysis.instrument.symbol, value=format_pine_data(analysis))
