from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum


class InstrumentType(StrEnum):
    INDEX = "INDEX"
    EQUITY = "EQUITY"


class LevelSide(StrEnum):
    UPPER = "UPPER"
    LOWER = "LOWER"


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
    name: str
    instrument_type: InstrumentType
    exchange: str = "NFO"
    lot_size: int = 1


@dataclass(frozen=True, slots=True)
class OptionContract:
    symbol: str
    strike: Decimal
    expiry: date
    call_oi: int
    put_oi: int
    call_oi_change: int = 0
    put_oi_change: int = 0
    call_token: str = ""
    put_token: str = ""
    call_trading_symbol: str = ""
    put_trading_symbol: str = ""

    @property
    def total_oi(self) -> int:
        return self.call_oi + self.put_oi

    @property
    def total_oi_change(self) -> int:
        return self.call_oi_change + self.put_oi_change


@dataclass(frozen=True, slots=True)
class SelectedStrikeLevel:
    strike_price: Decimal
    oi: int
    oi_change: int
    side: LevelSide
    point_gap: Decimal
    percentage_gap: Decimal
    rank_within_side: int
    call_oi: int = 0
    put_oi: int = 0


@dataclass(frozen=True, slots=True)
class HistogramStrike:
    strike_price: Decimal
    call_oi: int
    put_oi: int
    selected_side: LevelSide | None = None
    selected_rank: int | None = None


@dataclass(frozen=True, slots=True)
class InstrumentAnalysis:
    instrument: Instrument
    session_date: date
    expiry: date
    previous_open_price: Decimal
    atm_strike: Decimal
    upper_levels: tuple[SelectedStrikeLevel, ...]
    lower_levels: tuple[SelectedStrikeLevel, ...]
    histogram: tuple[HistogramStrike, ...]

    @property
    def macro_spread(self) -> Decimal:
        if not self.upper_levels or not self.lower_levels:
            return Decimal("0")
        return max(x.strike_price for x in self.upper_levels) - min(
            x.strike_price for x in self.lower_levels
        )

    @property
    def max_point_gap(self) -> Decimal:
        gaps = [x.point_gap for x in (*self.upper_levels, *self.lower_levels)]
        return max(gaps, default=Decimal("0"))

    @property
    def max_gap_level(self) -> SelectedStrikeLevel | None:
        levels = [x for x in (*self.upper_levels, *self.lower_levels)]
        return max(levels, key=lambda x: (x.point_gap, x.oi, str(x.strike_price)), default=None)

    @property
    def oi_magnitude(self) -> int:
        return sum(x.oi for x in (*self.upper_levels, *self.lower_levels))


@dataclass(frozen=True, slots=True)
class RankedResult:
    rank: int
    analysis: InstrumentAnalysis


def decimalize(value: Decimal | int | float | str) -> Decimal:
    """Convert through text so callers never inherit binary float artifacts."""
    return value if isinstance(value, Decimal) else Decimal(str(value))
