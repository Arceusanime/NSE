from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.domain import (
    HistogramStrike,
    Instrument,
    InstrumentAnalysis,
    LevelSide,
    OptionContract,
    RankedResult,
    SelectedStrikeLevel,
    decimalize,
)


class OISelectionPolicy:
    """Select the liquid ATM ± window strikes and calculate exact Decimal gaps."""

    def __init__(self, window_radius: int = 6, levels: int = 3) -> None:
        if window_radius < 0:
            raise ValueError("window_radius must be non-negative")
        if levels not in range(1, 6):
            raise ValueError("levels must be between 1 and 5")
        self.window_radius = window_radius
        self.levels = levels

    def analyze(
        self,
        instrument: Instrument,
        session_date: date,
        previous_open: Decimal | int | str,
        contracts: list[OptionContract],
        expiry: date | None = None,
    ) -> InstrumentAnalysis:
        open_price = decimalize(previous_open)
        if not contracts:
            raise ValueError(f"No option contracts supplied for {instrument.symbol}")
        selected_expiry = expiry or min(c.expiry for c in contracts)
        same_expiry = [c for c in contracts if c.expiry == selected_expiry]
        if not same_expiry:
            raise ValueError(f"No contracts for expiry {selected_expiry}")

        by_strike: dict[Decimal, OptionContract] = {}
        for contract in same_expiry:
            # Providers may return CE/PE rows separately; merge them safely.
            prior = by_strike.get(contract.strike)
            if prior is None:
                by_strike[contract.strike] = contract
            else:
                by_strike[contract.strike] = OptionContract(
                    symbol=contract.symbol,
                    strike=contract.strike,
                    expiry=contract.expiry,
                    call_oi=prior.call_oi + contract.call_oi,
                    put_oi=prior.put_oi + contract.put_oi,
                    call_oi_change=prior.call_oi_change + contract.call_oi_change,
                    put_oi_change=prior.put_oi_change + contract.put_oi_change,
                )
        strikes = sorted(by_strike)
        atm_index = min(range(len(strikes)), key=lambda i: (abs(strikes[i] - open_price), strikes[i]))
        lower_index = max(0, atm_index - self.window_radius)
        upper_index = min(len(strikes), atm_index + self.window_radius + 1)
        window = [by_strike[strike] for strike in strikes[lower_index:upper_index]]

        upper_candidates = [x for x in window if x.strike >= open_price]
        lower_candidates = [x for x in window if x.strike < open_price]
        # Score first, then use price as a deterministic tie-breaker.
        upper_candidates.sort(key=lambda x: (-x.total_oi, x.strike))
        lower_candidates.sort(key=lambda x: (-x.total_oi, -x.strike))
        upper_selected = sorted(upper_candidates[: self.levels], key=lambda x: x.strike)
        lower_selected = sorted(lower_candidates[: self.levels], key=lambda x: x.strike, reverse=True)

        upper = tuple(self._level(x, open_price, LevelSide.UPPER, i + 1) for i, x in enumerate(upper_selected))
        lower = tuple(self._level(x, open_price, LevelSide.LOWER, i + 1) for i, x in enumerate(lower_selected))
        selected = {(x.strike_price, x.side): x for x in (*upper, *lower)}
        histogram = tuple(
            HistogramStrike(
                strike_price=x.strike,
                call_oi=x.call_oi,
                put_oi=x.put_oi,
                selected_side=next((side for strike, side in selected if strike == x.strike), None),
                selected_rank=next((level.rank_within_side for (strike, _), level in selected.items() if strike == x.strike), None),
            )
            for x in window
        )
        return InstrumentAnalysis(
            instrument=instrument,
            session_date=session_date,
            expiry=selected_expiry,
            previous_open_price=open_price,
            atm_strike=strikes[atm_index],
            upper_levels=upper,
            lower_levels=lower,
            histogram=histogram,
        )

    @staticmethod
    def _level(contract: OptionContract, open_price: Decimal, side: LevelSide, rank: int) -> SelectedStrikeLevel:
        point_gap = contract.strike - open_price if side is LevelSide.UPPER else open_price - contract.strike
        percentage_gap = (point_gap / open_price * Decimal("100")) if open_price else Decimal("0")
        return SelectedStrikeLevel(
            strike_price=contract.strike,
            oi=contract.total_oi,
            oi_change=contract.total_oi_change,
            side=side,
            point_gap=point_gap,
            percentage_gap=percentage_gap,
            rank_within_side=rank,
            call_oi=contract.call_oi,
            put_oi=contract.put_oi,
        )


def rank_analyses(analyses: list[InstrumentAnalysis]) -> list[RankedResult]:
    """Rank by max qualifying gap, then OI magnitude, then symbol."""
    ordered = sorted(
        analyses,
        key=lambda x: (-x.max_point_gap, -x.oi_magnitude, x.instrument.symbol.upper()),
    )
    return [RankedResult(rank=i + 1, analysis=analysis) for i, analysis in enumerate(ordered)]
