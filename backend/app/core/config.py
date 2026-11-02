from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NSE F&O Opening-Price OI Scanner"
    database_url: str = "sqlite+aiosqlite:///./nse_scanner.db"
    angel_api_key: str | None = None
    angel_client_code: str | None = None
    angel_password: str | None = None
    angel_totp_secret: str | None = None
    angel_mac_address: str = "auto"
    angel_local_ip: str = "auto"
    angel_public_ip: str = "auto"
    angel_instrument_master_url: str = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    fno_symbols: str = "NIFTY,BANKNIFTY,FINNIFTY,RELIANCE,TCS,INFY"
    live_data_enabled: bool = True
    default_levels: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_prefix="NSE_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
