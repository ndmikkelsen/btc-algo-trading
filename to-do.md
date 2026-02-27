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

- [ ] Epic: Troubleshoot A-S model profitability #p2
  > A-S market making strategy was not profitable in live trading and wiped the account. Deprioritized — revisit after establishing profitability with other strategies. Original focus: troubleshoot spread calculation and inventory management.
- [ ] Complete stat_arb model implementation #p2
  > Multiple TODO stubs found in strategies/stat_arb/model.py: rolling correlation calculation, OLS regression for hedge ratio, Augmented Dickey-Fuller test for cointegration, spread calculation. Branch: algo-imp
- [ ] Statistical Arbitrage Research #p2
  > Cross-exchange arb, funding rate arb, pairs/cointegration trading. High crypto relevance — scaffolded code exists in strategies/stat_arb/.
- [ ] Market Making Extensions #p2
  > Extend existing A-S/GLFT market making: adaptive spreads, multi-level quoting, VPIN adverse selection defense. Builds on production infrastructure.
- [ ] Event-Driven / Funding Rate Research #p2
  > Funding rate arbitrage, liquidation cascade detection, halving cycle trading. High crypto-native relevance.
- [ ] Tune quote update threshold for low-volatility markets #p2
  > During live trading, the bot only updated quotes once in 5+ minutes because the should_update threshold (0.1% change) is too tight for the 5-second polling interval. Branch: fix/position-reduce
- [ ] Track per-entry timestamps for round-trip hold_time_seconds #p2
  > The round-trip DB record currently writes hold_time_seconds=0.0 because we don't track when each entry fill occurred. Need to store fill timestamp per position entry. Branch: test/paper-test, found in strategies/avellaneda_stoikov/live_trader.py
- [ ] Momentum Strategies Research #p2
  > Time-series momentum, adaptive momentum, breakout/channel strategies. Scaffolded in strategies/momentum_adaptive/.

## Medium Priority - #p1

## High Priority - #p0

## In Progress

## Done

- [x] beads+cognee migration smoke test #p2

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
