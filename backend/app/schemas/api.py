from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LevelDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strike_price: Decimal
    oi: int
    oi_change: int
    side: str
    point_gap: Decimal
    percentage_gap: Decimal
    rank_within_side: int
    call_oi: int
    put_oi: int


class HistogramDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strike_price: Decimal
    call_oi: int
    put_oi: int
    selected_side: str | None = None
    selected_rank: int | None = None


class AnalysisDTO(BaseModel):
    symbol: str
    name: str
    instrument_type: str
    session_date: date
    expiry: date
    previous_open_price: Decimal
    atm_strike: Decimal
    max_point_gap: Decimal
    macro_spread: Decimal
    upper_levels: list[LevelDTO]
    lower_levels: list[LevelDTO]
    histogram: list[HistogramDTO]


class ScanResultDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    symbol: str
    name: str = Field(validation_alias="instrument_name")
    instrument_type: str
    previous_open_price: Decimal
    max_overall_point_gap: Decimal
    max_gap_strike: Decimal | None
    max_gap_side: str | None
    macro_spread: Decimal
    expiry: date


class ScanListDTO(BaseModel):
    scan_id: int
    target_trading_date: date | None
    status: str
    total_instruments: int
    successful_instruments: int
    created_at: datetime | None
    items: list[ScanResultDTO]
    total: int


class ScanRequest(BaseModel):
    target_trading_date: date | None = None
    levels: int = Field(default=3, ge=1, le=5)


class PineDataDTO(BaseModel):
    symbol: str
    value: str


class HealthDTO(BaseModel):
    status: str
    database: str
    market_session: str
    provider: str
    provider_status: str
