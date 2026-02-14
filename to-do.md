---
id: to-do-list
aliases:
  - to-do
tags:
  - to-do
  - kanban
kanban-plugin: board
---

## Low Priority - #p2

- [ ] Tune A-S parameters from paper trading results #p2
  > Adjust Avellaneda-Stoikov parameters based on paper trading observations.
  > 
  > ## Parameters to Evaluate
  > - Risk aversion (γ) - currently 0.1
  > - Volatility window - currently 20 candles  
  > - MIN_SPREAD - currently 0.4% (optimized config)
  > - ADX threshold - currently 25 for regime filter
  > 
  > ## Goals
  > - Improve fill rate while maintaining profitability
  > - Reduce inventory risk exposure
  > - Optimize for Sharpe ratio in live conditions

## Medium Priority - #p1

- [ ] Prepare for live trading deployment #p1
  > Set up infrastructure for real money trading on Bybit mainnet.
  > 
  > ## Checklist
  > - [ ] Create Bybit mainnet API keys (read + trade permissions)
  > - [ ] Configure mainnet credentials securely (env vars, not in code)
  > - [ ] Set initial capital allocation (start small: $500-1000)
  > - [ ] Implement kill switch / emergency stop
  > - [ ] Set up monitoring and alerting
  > - [ ] Document risk limits and stop-loss rules
  > 
  > ## Risk Management
  > - Max position size limits
  > - Daily loss limits
  > - Automatic shutdown on anomalies

## High Priority - #p0



## In Progress

- [ ] Run A-S paper trading on Bybit testnet #p1
  > Validate Avellaneda-Stoikov strategy in live market conditions using Bybit testnet paper trading.
  > 
  > ## Acceptance Criteria
  > - Run paper trader for minimum 1 week
  > - Monitor fill rates, spread capture, and inventory management
  > - Track P&L vs backtest expectations
  > - Identify any issues with live execution (latency, WebSocket stability)
  > 
  > ## Resources
  > - scripts/run_paper_trader.py
  > - strategies/avellaneda_stoikov/live_trader.py
  > - config_hft.py settings

## Done

- [x] Backtest BTCMomentumScalper strategy #p1
- [x] Download Binance BTC/USDT data (2017-present) #p1
- [x] Verify backtesting works with sample data #p1
- [x] Configure exchange API for paper trading #p1
- [x] Install Freqtrade #p1
- [x] Backtesting Pipeline Setup #p1
- [x] Configure Cognee knowledge base for btc-algo-trading #p1
  > Set up isolated Cognee stack with unique ports, update all scripts and documentation to use btc-specific datasets and configuration.
- [x] Document backtesting findings #p2
- [x] Analyze performance by market regime #p2
- [x] Merge datasets into unified format #p2
- [x] Validate data quality #p2
- [x] Download Bitstamp data (2012-2017) #p2
- [x] Optimize BTCMomentumScalper strategy parameters #p2
- [x] Update PLAN.md with completed A-S milestones #p2
  > PLAN.md still shows M1-M4 milestones as unchecked, but all are implemented.
  > 
  > ## Updates Needed
  > - Mark M1 (Core Model) as complete
  > - Mark M2 (Order Management) as complete  
  > - Mark M3 (Backtesting Framework) as complete
  > - Mark M4 (Parameter Optimization) as complete
  > - Add M5: Paper Trading Validation
  > - Add M6: Live Trading Deployment
  > - Update Open Questions section

%% kanban:settings

```json
{
  "kanban-plugin": "board",
  "list-collapse": [false, false, false, false, true],
  "show-checkboxes": true,
  "show-card-footer": true,
  "tag-sort-order": ["p0", "p1", "p2"],
  "date-format": "YYYY-MM-DD"
}
```

%%
