# PLAN.md - BTC Algo Trading

> Working memory for the algorithmic trading project.

## Current Focus

**Phase 1: Environment & Data Acquisition**

## Milestones

### M1: Development Environment (Not Started)
- [ ] Install Freqtrade
- [ ] Configure exchange API (Binance paper trading)
- [ ] Set up project structure
- [ ] Verify backtesting works with sample data

### M2: Historical Data (Not Started)
- [ ] Download Binance BTC/USDT (2017-present)
- [ ] Download Bitstamp data (2012-2017) for extended history
- [ ] Validate data quality (no gaps, OHLC integrity)
- [ ] Merge datasets into unified format

### M3: Strategy Implementation (Not Started)
- [ ] Implement simple momentum strategy (25-day lookback)
- [ ] Implement mean reversion strategy (Bollinger Bands)
- [ ] Implement hybrid 50/50 portfolio
- [ ] Unit tests for each strategy

### M4: Backtesting & Analysis (Not Started)
- [ ] Backtest all strategies against full history (2012-present)
- [ ] Analyze performance by market regime
- [ ] Compare: Sharpe ratio, max drawdown, win rate
- [ ] Document findings

### M5: Paper Trading (Not Started)
- [ ] Deploy best strategy to paper trading
- [ ] Run for 1-3 months
- [ ] Compare live results to backtest expectations
- [ ] Refine if needed

### M6: Live Trading (Not Started)
- [ ] Start with minimal position sizing
- [ ] Gradual scale-up based on performance
- [ ] Monitoring and alerting

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-30 | Start with Freqtrade | Best Python framework, ML support, active community |
| 2026-01-30 | Target 2012+ data | Covers all major market regimes |
| 2026-01-30 | Test momentum + mean reversion + hybrid | Research shows hybrid outperforms single strategies |
| 2026-02-01 | Implement Cognee knowledge base | AI memory layer for semantic search over strategies, backtests, and session history |

## Recent Milestones

### Cognee Integration (2026-02-01) ✅

Implemented isolated Cognee stack for btc-algo-trading knowledge base:
- Unique ports (8001, 5434, 6381, 7475, 7688) - runs alongside second-brain
- Datasets: btc-knowledge-garden, btc-patterns, btc-constitution, btc-strategies, btc-backtests
- Semantic search over trading strategies and documentation
- Session capture for queryable history

## Open Questions

- Which exchange for live trading? (Binance, Kraken, Coinbase)
- Position sizing strategy?
- Risk management rules (max drawdown, stop-loss)?

## Resources

- [Algorithmic Trading Strategies Research](../second-brain/personal/trading/crypto/algorithmic-trading-strategies.md)
- [Freqtrade Documentation](https://www.freqtrade.io/en/stable/)
- [CCXT Library](https://github.com/ccxt/ccxt)
