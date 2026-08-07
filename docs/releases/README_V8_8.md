# Catalyst AI v8.8.0 — Historical Backtesting

## Delivered

- Historical strategy backtesting page
- Reuses the existing Catalyst indicators and score rules
- Signals calculated at the close with entry on the next trading day's open
- One open position per ticker
- Fixed holding-period exits
- Optional ATR target and stop exits
- Conservative stop-first assumption when a daily bar crosses both levels
- Configurable round-trip transaction cost
- Win rate, average and median trade return
- Compounded trade return
- Maximum drawdown
- Profit factor and average holding period
- Downloadable trade ledger and equity curve
- Clear assumptions and data-error reporting

## Important

This is a research backtest, not a forecast. It does not model taxes,
portfolio-capital limits, partial fills, or detailed intraday slippage.
