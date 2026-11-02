from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db import ScanResult, ScanRun, SelectedLevel
from app.models.domain import HistogramStrike, InstrumentAnalysis, RankedResult


class ScanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, target_date, total: int) -> ScanRun:
        run = ScanRun(target_trading_date=target_date, total_instruments=total, status="RUNNING")
        self.session.add(run)
        await self.session.flush()
        return run

    async def save_results(self, run: ScanRun, ranked: list[RankedResult]) -> None:
        run.successful_instruments = len(ranked)
        run.status = "COMPLETED"
        if ranked:
            run.expiry_used = ranked[0].analysis.expiry.isoformat()
        for ranked_result in ranked:
            analysis = ranked_result.analysis
            result = ScanResult(
                scan=run,
                rank=ranked_result.rank,
                symbol=analysis.instrument.symbol,
                instrument_name=analysis.instrument.name,
                instrument_type=analysis.instrument.instrument_type.value,
                previous_open_price=analysis.previous_open_price,
                max_overall_point_gap=analysis.max_point_gap,
                max_gap_strike=analysis.max_gap_level.strike_price if analysis.max_gap_level else None,
                max_gap_side=analysis.max_gap_level.side.value if analysis.max_gap_level else None,
                macro_spread=analysis.macro_spread,
                expiry=analysis.expiry,
                atm_strike=analysis.atm_strike,
                histogram_json=json.dumps([
                    {"strike_price": str(x.strike_price), "call_oi": x.call_oi, "put_oi": x.put_oi,
                     "selected_side": x.selected_side.value if x.selected_side else None, "selected_rank": x.selected_rank}
                    for x in analysis.histogram
                ]),
            )
            result.levels = [SelectedLevel(
                    result=result,
                    strike_price=level.strike_price,
                    oi=level.oi,
                    oi_change=level.oi_change,
                    side=level.side.value,
                    point_gap=level.point_gap,
                    percentage_gap=level.percentage_gap,
                    rank_within_side=level.rank_within_side,
                    call_oi=level.call_oi,
                    put_oi=level.put_oi,
                )
                for level in (*analysis.upper_levels, *analysis.lower_levels)
            ]
            self.session.add(result)
        await self.session.commit()

    async def latest_run(self) -> ScanRun | None:
        result = await self.session.execute(
            select(ScanRun).options(selectinload(ScanRun.results).selectinload(ScanResult.levels)).order_by(desc(ScanRun.scan_id)).limit(1)
        )
        return result.scalar_one_or_none()

    async def find_result(self, symbol: str) -> ScanResult | None:
        result = await self.session.execute(
            select(ScanResult)
            .join(ScanRun)
            .options(selectinload(ScanResult.levels), selectinload(ScanResult.scan))
            .where(ScanResult.symbol == symbol.upper(), ScanRun.status == "COMPLETED")
            .order_by(desc(ScanResult.scan_id))
            .limit(1)
        )
        return result.scalar_one_or_none()
