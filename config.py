from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    app_name: str = "Catalyst AI"
    tagline: str = "Professional Trading Intelligence"
    engine_name: str = "PJB Trading Engine"
    page_icon: str = "🚀"
    layout: str = "wide"
    max_default_tickers: int = 650
    holdings_enabled: bool = False

CONFIG = AppConfig()
