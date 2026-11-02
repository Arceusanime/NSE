from datetime import date, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

from app.models.domain import Instrument, InstrumentAnalysis, InstrumentType, LevelSide, SelectedStrikeLevel
from app.services.calendar.service import MarketCalendar
from app.services.pine import PINE_SCRIPT, format_pine_data


def test_calendar_skips_weekend_and_session_status() -> None:
    calendar = MarketCalendar()
    assert calendar.previous_trading_day(date(2026, 11, 2)) == date(2026, 10, 30)
    ist = ZoneInfo("Asia/Kolkata")
    assert calendar.session_status(datetime(2026, 11, 2, 9, 20, tzinfo=ist)) == "NSE LIVE"
    assert calendar.session_status(datetime(2026, 11, 2, 16, 0, tzinfo=ist)) == "MARKET CLOSED"


def test_pine_script_contract_and_formatting() -> None:
    assert PINE_SCRIPT.startswith("//@version=5")
    assert "OI Data (Box 1)" in PINE_SCRIPT
    analysis = InstrumentAnalysis(
        instrument=Instrument("NIFTY", "NIFTY 50", InstrumentType.INDEX),
        session_date=date(2026, 10, 30), expiry=date(2026, 11, 26), previous_open_price=Decimal("24450"),
        atm_strike=Decimal("24450"),
        upper_levels=(SelectedStrikeLevel(Decimal("24500"), 1, 0, LevelSide.UPPER, Decimal("50"), Decimal("0.2"), 1),),
        lower_levels=(SelectedStrikeLevel(Decimal("24400"), 1, 0, LevelSide.LOWER, Decimal("50"), Decimal("0.2"), 1),),
        histogram=(),
    )
    assert format_pine_data(analysis) == "NIFTY | 24500 | 24400"
