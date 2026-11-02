from __future__ import annotations

import asyncio
import re
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pyotp

from app.core.config import Settings
from app.models.domain import Instrument, InstrumentType, OptionContract, decimalize
from .base import MarketDataProvider


IST = ZoneInfo("Asia/Kolkata")
MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"


@dataclass(frozen=True, slots=True)
class _MasterRow:
    token: str
    symbol: str
    name: str
    expiry: date | None
    strike: Decimal | None
    instrument_type: str
    exchange: str


class AngelOneProvider(MarketDataProvider):
    """Live Angel One SmartAPI provider.

    The SmartAPI SDK is synchronous, so all broker calls are executed in worker
    threads. The instrument master is downloaded once per provider instance and
    is used for token, expiry, strike, and CE/PE resolution.
    """

    name = "angel_one"
    live = True
    _quote_batch_size = 50
    _historical_delay_seconds = 1.2

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Any = None
        self._authenticated = False
        self._master: list[_MasterRow] | None = None
        self._master_lock = asyncio.Lock()
        self._historical_lock = asyncio.Lock()
        self._last_historical_request = 0.0

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.live_data_enabled
            and self.settings.angel_api_key
            and self.settings.angel_client_code
            and self.settings.angel_password
            and self.settings.angel_totp_secret
        )

    async def authenticate(self) -> bool:
        if not self.configured:
            return False

        identity = await self._connection_identity()

        def login() -> Any:
            from SmartApi import SmartConnect  # type: ignore[import-not-found]

            client = SmartConnect(api_key=self.settings.angel_api_key)
            # smartapi-python 1.5.x currently initializes these from class
            # defaults, so explicitly apply the deployment's compliance values.
            client.clientMacAddress = identity["mac"]
            client.clientLocalIp = identity["local_ip"]
            client.clientPublicIP = identity["public_ip"]
            client.accept = "application/json"
            client.userType = "USER"
            client.sourceID = "WEB"
            response = client.generateSession(
                self.settings.angel_client_code,
                self.settings.angel_password,
                pyotp.TOTP(self.settings.angel_totp_secret).now(),
            )
            return response, client

        response, client = await asyncio.to_thread(login)
        self._client = client
        self._authenticated = bool(response and response.get("status"))
        if not self._authenticated:
            message = response.get("message", "SmartAPI login failed") if isinstance(response, dict) else "SmartAPI login failed"
            raise RuntimeError(message)
        return True

    async def _connection_identity(self) -> dict[str, str]:
        mac = self.settings.angel_mac_address
        if not mac or mac.lower() == "auto" or mac == "00:00:00:00:00:00":
            mac = ":".join(re.findall("..", f"{uuid.getnode():012x}"))

        local_ip = self.settings.angel_local_ip
        if not local_ip or local_ip.lower() == "auto" or local_ip == "127.0.0.1":
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
            except OSError:
                local_ip = "127.0.0.1"

        public_ip = self.settings.angel_public_ip
        if not public_ip or public_ip.lower() == "auto" or public_ip == "127.0.0.1":
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get("https://api.ipify.org")
                response.raise_for_status()
                public_ip = response.text.strip()

        return {"mac": mac, "local_ip": local_ip, "public_ip": public_ip}

    async def get_status(self) -> str:
        if self._authenticated:
            return "connected"
        return "configured" if self.configured else "credentials_missing"

    async def _master_rows(self) -> list[_MasterRow]:
        if self._master is not None:
            return self._master
        async with self._master_lock:
            if self._master is not None:
                return self._master
            url = self.settings.angel_instrument_master_url or MASTER_URL
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url)
                response.raise_for_status()
                raw_rows = response.json()
            self._master = [self._parse_master_row(row) for row in raw_rows]
            return self._master

    @staticmethod
    def _parse_master_row(row: dict[str, Any]) -> _MasterRow:
        expiry = None
        if row.get("expiry"):
            for pattern in ("%d%b%Y", "%d%b%y"):
                try:
                    expiry = datetime.strptime(str(row["expiry"]).upper(), pattern).date()
                    break
                except ValueError:
                    continue
        strike = None
        raw_strike = row.get("strike")
        if raw_strike not in (None, "", "-1.000000", -1):
            try:
                # Angel's NFO master stores strikes in paise.
                strike = Decimal(str(raw_strike)) / Decimal("100")
            except (InvalidOperation, ValueError):
                strike = None
        return _MasterRow(
            token=str(row.get("token", "")),
            symbol=str(row.get("symbol", "")),
            name=str(row.get("name", "")),
            expiry=expiry,
            strike=strike,
            instrument_type=str(row.get("instrumenttype", "")),
            exchange=str(row.get("exch_seg", "")),
        )

    async def get_fno_instruments(self) -> list[Instrument]:
        rows = await self._master_rows()
        requested = [symbol.strip().upper() for symbol in self.settings.fno_symbols.split(",") if symbol.strip()]
        available = {
            row.name.upper()
            for row in rows
            if row.exchange == "NFO" and row.instrument_type in {"OPTIDX", "OPTSTK"} and row.name
        }
        instruments: list[Instrument] = []
        for symbol in requested:
            if symbol not in available:
                continue
            instrument_type = InstrumentType.INDEX if any(
                row.name.upper() == symbol and row.instrument_type == "OPTIDX" for row in rows
            ) else InstrumentType.EQUITY
            instruments.append(Instrument(symbol=symbol, name=symbol, instrument_type=instrument_type))
        if not instruments:
            raise RuntimeError("No configured symbols were found in the Angel One instrument master")
        return instruments

    async def _underlying_token(self, symbol: str) -> str:
        rows = await self._master_rows()
        candidates = [
            row for row in rows
            if row.exchange == "NSE"
            and (row.symbol.upper() in {symbol.upper(), f"{symbol.upper()}-EQ"} or row.name.upper() == symbol.upper())
        ]
        if not candidates:
            raise LookupError(f"No NSE cash/index token found for {symbol}")
        # The master contains both legacy index rows (e.g. 26000) and the
        # AMXIDX rows used by the historical index feed (e.g. 99926000).
        index_candidates = [row for row in candidates if row.instrument_type == "AMXIDX"]
        return (index_candidates or candidates)[0].token

    async def _historical_call(self, method: str, params: dict[str, Any]) -> Any:
        if self._client is None or not self._authenticated:
            raise RuntimeError("Angel One provider is not authenticated")
        async with self._historical_lock:
            elapsed = time.monotonic() - self._last_historical_request
            if elapsed < self._historical_delay_seconds:
                await asyncio.sleep(self._historical_delay_seconds - elapsed)
            response = await asyncio.to_thread(getattr(self._client, method), params)
            self._last_historical_request = time.monotonic()
        if not isinstance(response, dict) or not response.get("status"):
            raise RuntimeError(f"Angel One {method} failed: {response}")
        return response.get("data") or []

    async def get_underlying_open_price(self, symbol: str, trading_date: date) -> Decimal:
        token = await self._underlying_token(symbol)
        data = await self._historical_call(
            "getCandleData",
            {
                "exchange": "NSE",
                "symboltoken": token,
                "interval": "ONE_MINUTE",
                "fromdate": f"{trading_date.isoformat()} 09:15",
                "todate": f"{trading_date.isoformat()} 09:16",
            },
        )
        if not data:
            raise LookupError(f"No 09:15 candle returned for {symbol} on {trading_date}")
        candle = data[0]
        return decimalize(candle[1])

    async def get_available_expiries(self, symbol: str) -> list[date]:
        rows = await self._master_rows()
        today = datetime.now(IST).date()
        expiries = {
            row.expiry
            for row in rows
            if row.exchange == "NFO" and row.name.upper() == symbol.upper() and row.expiry and row.expiry >= today
        }
        return sorted(expiry for expiry in expiries if expiry is not None)

    async def get_option_contracts(self, symbol: str, expiry: date) -> list[OptionContract]:
        rows = await self._master_rows()
        grouped: dict[Decimal, dict[str, _MasterRow]] = {}
        for row in rows:
            if row.exchange != "NFO" or row.name.upper() != symbol.upper() or row.expiry != expiry or row.strike is None:
                continue
            suffix = row.symbol.upper()[-2:]
            if suffix in {"CE", "PE"}:
                grouped.setdefault(row.strike, {})[suffix] = row
        contracts: list[OptionContract] = []
        for strike in sorted(grouped):
            pair = grouped[strike]
            call = pair.get("CE")
            put = pair.get("PE")
            if call is None or put is None:
                continue
            contracts.append(
                OptionContract(
                    symbol=symbol.upper(),
                    strike=strike,
                    expiry=expiry,
                    call_oi=0,
                    put_oi=0,
                    call_token=call.token,
                    put_token=put.token,
                    call_trading_symbol=call.symbol,
                    put_trading_symbol=put.symbol,
                )
            )
        if not contracts:
            raise LookupError(f"No CE/PE option pairs found for {symbol} {expiry}")
        return contracts

    async def get_current_oi(self, contracts: list[OptionContract]) -> list[OptionContract]:
        if self._client is None or not self._authenticated:
            raise RuntimeError("Angel One provider is not authenticated")
        token_to_side: dict[str, tuple[OptionContract, str]] = {}
        for contract in contracts:
            if contract.call_token:
                token_to_side[contract.call_token] = (contract, "call")
            if contract.put_token:
                token_to_side[contract.put_token] = (contract, "put")
        tokens = list(token_to_side)
        oi_by_strike: dict[Decimal, list[int]] = {contract.strike: [0, 0] for contract in contracts}
        for start in range(0, len(tokens), self._quote_batch_size):
            batch = tokens[start : start + self._quote_batch_size]
            response = await asyncio.to_thread(self._client.getMarketData, "FULL", {"NFO": batch})
            if not isinstance(response, dict) or not response.get("status"):
                raise RuntimeError(f"Angel One market quote failed: {response}")
            fetched = (response.get("data") or {}).get("fetched", [])
            for quote in fetched:
                token = str(quote.get("symbolToken", quote.get("symboltoken", "")))
                mapping = token_to_side.get(token)
                if mapping is None:
                    continue
                contract, side = mapping
                raw_oi = quote.get("opnInterest", quote.get("openInterest", quote.get("oi", 0)))
                oi = int(Decimal(str(raw_oi or 0)))
                oi_by_strike[contract.strike][0 if side == "call" else 1] = oi
            # Market quote API is limited to one request per second.
            if start + self._quote_batch_size < len(tokens):
                await asyncio.sleep(1.05)
        return [
            OptionContract(
                symbol=contract.symbol,
                strike=contract.strike,
                expiry=contract.expiry,
                call_oi=oi_by_strike[contract.strike][0],
                put_oi=oi_by_strike[contract.strike][1],
                call_oi_change=contract.call_oi_change,
                put_oi_change=contract.put_oi_change,
                call_token=contract.call_token,
                put_token=contract.put_token,
                call_trading_symbol=contract.call_trading_symbol,
                put_trading_symbol=contract.put_trading_symbol,
            )
            for contract in contracts
        ]

    async def historical_request(self, *args: Any, **kwargs: Any) -> Any:
        if self._client is None:
            raise RuntimeError("Angel One provider is not authenticated")
        await asyncio.sleep(self._historical_delay_seconds)
        return await asyncio.to_thread(self._client.getCandleData, *args, **kwargs)
