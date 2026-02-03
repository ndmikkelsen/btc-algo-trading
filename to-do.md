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

- [ ] Document backtesting findings #p2
- [ ] Analyze performance by market regime #p2
- [ ] Merge datasets into unified format #p2
- [ ] Validate data quality #p2
- [ ] Download Bitstamp data (2012-2017) #p2
- [ ] Optimize BTCMomentumScalper strategy parameters #p2

## Medium Priority - #p1

- [ ] Backtesting Pipeline Setup #p1

## High Priority - #p0



## In Progress



## Done

- [x] Backtest BTCMomentumScalper strategy #p1
- [x] Download Binance BTC/USDT data (2017-present) #p1
- [x] Verify backtesting works with sample data #p1
- [x] Configure exchange API for paper trading #p1
- [x] Install Freqtrade #p1
- [x] Configure Cognee knowledge base for btc-algo-trading #p1
  > Set up isolated Cognee stack with unique ports, update all scripts and documentation to use btc-specific datasets and configuration.

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
