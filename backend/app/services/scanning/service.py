from __future__ import annotations

import asyncio
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.models.domain import InstrumentAnalysis, OptionContract
from app.repositories.scans import ScanRepository
from app.services.calendar.service import MarketCalendar
from app.services.market_data.base import MarketDataProvider
from app.services.oi_analysis.engine import OISelectionPolicy, rank_analyses


class ScannerService:
    def __init__(self, repository: ScanRepository, provider: MarketDataProvider, calendar: MarketCalendar | None = None) -> None:
        self.repository = repository
        self.provider = provider
        self.calendar = calendar or MarketCalendar()
        self._lock = asyncio.Lock()

    async def run(self, target_trading_date: date | None = None, levels: int = 3) -> int:
        async with self._lock:
            if self.provider.live and not await self.provider.authenticate():
                raise RuntimeError("Live provider is not configured; set NSE_ANGEL_* credentials in .env")
            today = target_trading_date or datetime.now(ZoneInfo("Asia/Kolkata")).date()
            if not self.calendar.is_trading_day(today):
                raise ValueError(f"{today.isoformat()} is not an NSE trading day")
            anchor_date = self.calendar.previous_trading_day(today)
            instruments = await self.provider.get_fno_instruments()
            run = await self.repository.create_run(today, len(instruments))
            analyses: list[InstrumentAnalysis] = []
            try:
                for instrument in instruments:
                    previous_open = await self.provider.get_underlying_open_price(instrument.symbol, anchor_date)
                    expiry = min(await self.provider.get_available_expiries(instrument.symbol))
                    contracts = await self.provider.get_option_contracts(instrument.symbol, expiry)
                    contracts = self._atm_window(contracts, previous_open, radius=6)
                    contracts = await self.provider.get_current_oi(contracts)
                    analyses.append(
                        OISelectionPolicy(window_radius=6, levels=levels).analyze(
                            instrument, anchor_date, previous_open, contracts, expiry
                        )
                    )
                ranked = rank_analyses(analyses)
                await self.repository.save_results(run, ranked)
                return run.scan_id
            except Exception:
                run.status = "FAILED"
                await self.repository.session.commit()
                raise

    @staticmethod
    def _atm_window(contracts: list[OptionContract], anchor: Decimal, radius: int) -> list[OptionContract]:
        ordered = sorted(contracts, key=lambda contract: contract.strike)
        if not ordered:
            return []
        atm_index = min(range(len(ordered)), key=lambda index: (abs(ordered[index].strike - anchor), ordered[index].strike))
        return ordered[max(0, atm_index - radius) : min(len(ordered), atm_index + radius + 1)]
