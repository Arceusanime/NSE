from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.models.domain import Instrument, InstrumentType, OptionContract
from .base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    name = "simulated"
    live = False

    _specs = {
        "NIFTY": ("NIFTY 50", InstrumentType.INDEX, Decimal("24450"), Decimal("50")),
        "BANKNIFTY": ("NIFTY BANK", InstrumentType.INDEX, Decimal("52200"), Decimal("100")),
        "RELIANCE": ("Reliance Industries", InstrumentType.EQUITY, Decimal("1200"), Decimal("20")),
    }

    async def authenticate(self) -> bool:
        return True

    async def get_status(self) -> str:
        return "simulated"

    async def get_fno_instruments(self) -> list[Instrument]:
        return [Instrument(symbol=symbol, name=spec[0], instrument_type=spec[1]) for symbol, spec in self._specs.items()]

    async def get_underlying_open_price(self, symbol: str, trading_date: date) -> Decimal:
        try:
            return self._specs[symbol.upper()][2]
        except KeyError as exc:
            raise LookupError(f"Unknown instrument: {symbol}") from exc

    async def get_available_expiries(self, symbol: str) -> list[date]:
        # A stable future fixture keeps offline scans independent of today's date.
        return [date(2099, 1, 30)]

    async def get_option_contracts(self, symbol: str, expiry: date) -> list[OptionContract]:
        symbol = symbol.upper()
        _, _, anchor, step = self._specs[symbol]
        contracts: list[OptionContract] = []
        for offset in range(-15, 16):
            strike = anchor + step * offset
            distance = abs(offset)
            # Deterministic concentration around ATM with asymmetric wings.
            call_oi = 100_000 + (15 - distance) * 8_000 + max(offset, 0) * 2_000
            put_oi = 95_000 + (15 - distance) * 7_000 + max(-offset, 0) * 2_500
            contracts.append(
                OptionContract(
                    symbol=symbol,
                    strike=strike,
                    expiry=expiry,
                    call_oi=call_oi,
                    put_oi=put_oi,
                    call_oi_change=(offset + 15) * 100,
                    put_oi_change=(15 - offset) * 100,
                )
            )
        return contracts
