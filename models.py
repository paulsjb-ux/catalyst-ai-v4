from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class ScanResult:
    ticker: str
    signal: str
    score: int
    close: float
    change_1d_pct: float
    change_20d_pct: float
    rsi_14: float
    sma_20: float
    sma_50: float
    sma_200: float
    volume_ratio: float
    trend: str
    reason: str
    def to_dict(self) -> dict:
        return asdict(self)
