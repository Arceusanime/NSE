from datetime import date
from decimal import Decimal

from app.models.domain import Instrument, InstrumentType, LevelSide, OptionContract
from app.services.oi_analysis.engine import OISelectionPolicy, rank_analyses


EXPIRY = date(2026, 11, 26)


def instrument(symbol: str) -> Instrument:
    return Instrument(symbol, symbol, InstrumentType.INDEX)


def contract(strike: str, call: int, put: int) -> OptionContract:
    return OptionContract("NIFTY", Decimal(strike), EXPIRY, call, put)


def test_atm_window_partition_score_and_decimal_gaps() -> None:
    contracts = [contract(strike, 100 + i * 10, 200 - i * 5) for i, strike in enumerate(("9900", "9950", "10000", "10050", "10100", "10150", "10200"))]
    analysis = OISelectionPolicy(window_radius=2, levels=2).analyze(
        instrument("NIFTY"), date(2026, 11, 25), Decimal("10025"), contracts, EXPIRY
    )
    assert analysis.atm_strike == Decimal("10000")
    assert len(analysis.histogram) == 5
    assert [level.strike_price for level in analysis.upper_levels] == [Decimal("10050"), Decimal("10100")]
    assert [level.strike_price for level in analysis.lower_levels] == [Decimal("10000"), Decimal("9950")]
    assert all(level.side is LevelSide.UPPER for level in analysis.upper_levels)
    assert analysis.upper_levels[1].point_gap == Decimal("75")


def test_ties_use_price_direction_deterministically() -> None:
    contracts = [contract(strike, 500, 500) for strike in ("9900", "9950", "10000", "10050", "10100")]
    analysis = OISelectionPolicy(window_radius=2, levels=2).analyze(
        instrument("NIFTY"), date(2026, 11, 25), Decimal("10000"), contracts, EXPIRY
    )
    assert [x.strike_price for x in analysis.upper_levels] == [Decimal("10000"), Decimal("10050")]
    assert [x.strike_price for x in analysis.lower_levels] == [Decimal("9950"), Decimal("9900")]


def test_instrument_ranking_gap_then_oi_then_symbol() -> None:
    def make(symbol: str, strike: str, oi: int):
        rows = [contract("10000", oi, 0), contract(strike, oi, 0)]
        return OISelectionPolicy(window_radius=1, levels=1).analyze(
            instrument(symbol), date(2026, 11, 25), Decimal("10000"), rows, EXPIRY
        )

    ranked = rank_analyses([make("ZETA", "10100", 100), make("ALPHA", "10100", 100)])
    assert [x.analysis.instrument.symbol for x in ranked] == ["ALPHA", "ZETA"]
