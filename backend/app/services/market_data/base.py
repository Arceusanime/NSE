from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.models.domain import Instrument, OptionContract


class MarketDataProvider(ABC):
    name = "unknown"
    live = False

    @abstractmethod
    async def authenticate(self) -> bool: ...

    @abstractmethod
    async def get_status(self) -> str: ...

    @abstractmethod
    async def get_fno_instruments(self) -> list[Instrument]: ...

    @abstractmethod
    async def get_underlying_open_price(self, symbol: str, trading_date: date) -> Decimal: ...

    @abstractmethod
    async def get_available_expiries(self, symbol: str) -> list[date]: ...

    @abstractmethod
    async def get_option_contracts(self, symbol: str, expiry: date) -> list[OptionContract]: ...

    async def get_current_oi(self, contracts: list[OptionContract]) -> list[OptionContract]:
        return contracts
