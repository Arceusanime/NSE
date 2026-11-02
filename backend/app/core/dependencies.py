from functools import lru_cache

from app.services.market_data.base import MarketDataProvider
from app.services.market_data.factory import provider_factory


@lru_cache
def get_provider() -> MarketDataProvider:
    return provider_factory()
