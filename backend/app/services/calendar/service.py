from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


class MarketCalendar:
    """Small holiday-aware session resolver; holidays can be extended without changing consumers."""

    def __init__(self, holidays: set[date] | None = None) -> None:
        self.holidays = holidays or set()

    def is_trading_day(self, value: date) -> bool:
        return value.weekday() < 5 and value not in self.holidays

    def previous_trading_day(self, value: date) -> date:
        candidate = value - timedelta(days=1)
        while not self.is_trading_day(candidate):
            candidate -= timedelta(days=1)
        return candidate

    def session_status(self, now: datetime | None = None) -> str:
        current = (now or datetime.now(IST)).astimezone(IST)
        if not self.is_trading_day(current.date()):
            return "MARKET CLOSED"
        current_time = current.time()
        if current_time < time(9, 15):
            return "PRE-MARKET"
        if current_time <= time(15, 30):
            return "NSE LIVE"
        return "MARKET CLOSED"
