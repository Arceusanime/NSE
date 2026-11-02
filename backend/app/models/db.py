from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScanRun(Base):
    __tablename__ = "scan_runs"

    scan_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_trading_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    total_instruments: Mapped[int] = mapped_column(Integer, default=0)
    successful_instruments: Mapped[int] = mapped_column(Integer, default=0)
    expiry_used: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    results: Mapped[list[ScanResult]] = relationship(back_populates="scan", cascade="all, delete-orphan")


class ScanResult(Base):
    __tablename__ = "scan_results"

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scan_runs.scan_id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    symbol: Mapped[str] = mapped_column(String(30), index=True)
    instrument_name: Mapped[str] = mapped_column(String(100))
    instrument_type: Mapped[str] = mapped_column(String(20))
    previous_open_price: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    max_overall_point_gap: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    max_gap_strike: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    max_gap_side: Mapped[str | None] = mapped_column(String(10), nullable=True)
    macro_spread: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    expiry: Mapped[date] = mapped_column(Date)
    atm_strike: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    histogram_json: Mapped[str] = mapped_column(Text, default="[]")
    scan: Mapped[ScanRun] = relationship(back_populates="results")
    levels: Mapped[list[SelectedLevel]] = relationship(back_populates="result", cascade="all, delete-orphan")


class SelectedLevel(Base):
    __tablename__ = "selected_levels"

    level_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("scan_results.result_id"), index=True)
    strike_price: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    oi: Mapped[int] = mapped_column(Integer)
    oi_change: Mapped[int] = mapped_column(Integer)
    side: Mapped[str] = mapped_column(String(10))
    point_gap: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    percentage_gap: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    rank_within_side: Mapped[int] = mapped_column(Integer)
    call_oi: Mapped[int] = mapped_column(Integer)
    put_oi: Mapped[int] = mapped_column(Integer)
    result: Mapped[ScanResult] = relationship(back_populates="levels")
