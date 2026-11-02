from app.core.config import Settings, get_settings
from .angel_one import AngelOneProvider
from .base import MarketDataProvider
from .mock import MockMarketDataProvider


def provider_factory(settings: Settings | None = None) -> MarketDataProvider:
    settings = settings or get_settings()
    configured = settings.live_data_enabled and all(
        (settings.angel_api_key, settings.angel_client_code, settings.angel_password, settings.angel_totp_secret)
    )
    return AngelOneProvider(settings) if configured else MockMarketDataProvider()
