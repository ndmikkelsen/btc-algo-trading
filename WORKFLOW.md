# WORKFLOW.md — Strategy Development Pipeline

> How we research, validate, and deploy trading strategies.
> This is the operating system for all strategy development.

**Last Updated**: 2026-02-22

---

## Pipeline Overview

Every strategy flows through five phases. No phase can be skipped.

```
Phase 1: Research & Alpha Discovery
    ↓  (go/no-go: Is there a testable hypothesis?)
Phase 2: Implementation & Backtesting
    ↓  (go/no-go: Statistical significance + survives fees?)
Phase 3: Incubation (Paper Trading)
    ↓  (go/no-go: Live matches backtest within tolerance?)
Phase 4: Live Deployment
    ↓  (continuous: Performance within bounds?)
Phase 5: Analysis & Iteration
    ↓  (loop back to Phase 1 or 2)
```

### Phase Durations (Typical)

| Phase | Duration | Can Shortcut? |
|-------|----------|---------------|
| Research | 1-5 days | No |
| Backtesting | 2-7 days | No |
| Incubation | 1-4 weeks | No |
| Live Deployment | Ongoing | N/A |
| Analysis | 1-2 days per cycle | No |

---

## Phase 1: Research & Alpha Discovery

**Goal**: Identify a testable trading hypothesis with theoretical backing.

### Prerequisites

- Access to academic papers and strategy references
- Understanding of current market structure
- Review of [strategies catalog](.rules/reference/strategies-catalog.md)

### Process

1. **Survey the landscape** — Check the strategies catalog for candidates by priority and BTC applicability
2. **Literature review** — Read 2-3 papers or references for the strategy class
3. **Hypothesis formation** — Write a clear, testable statement:
   - "BTC funding rates mean-revert within 8h, creating a 15bps+ edge after fees"
   - "Order flow imbalance predicts 5s BTC price direction with >55% accuracy"
4. **Feasibility check** — Verify data availability, execution requirements, and infrastructure gaps
5. **Create beads** — Epic for the strategy, tasks for implementation phases

### Tools

- Web search and paper repositories (arXiv, SSRN)
- `/query` for internal knowledge search
- Strategy catalog: `.rules/reference/strategies-catalog.md`
- Library reference: `.rules/reference/libraries-reference.md`

### Outputs

- Written hypothesis in beads epic description
- List of required data sources and libraries
- Rough implementation plan

### Go/No-Go Gate

| Criterion | Requirement |
|-----------|-------------|
| Testable hypothesis | Clear entry/exit logic that can be backtested |
| Data available | OHLCV, order book, or on-chain data accessible |
| Fee-aware | Hypothesis accounts for realistic trading costs |
| Not duplicate | Doesn't replicate a validated NO-GO strategy |
| BTC applicability | Medium or High rating in catalog |

### Beads/GSD Commands

```bash
bd create --title="Research: <Strategy Name>" --type=epic --priority=2
bd create --title="Literature review for <strategy>" --type=task --priority=2
bd create --title="Feasibility check for <strategy>" --type=task --priority=2
```

---

## Phase 2: Implementation & Backtesting

**Goal**: Implement the strategy and validate statistically against historical data.

### Prerequisites

- Phase 1 complete with go decision
- Historical data available (minimum 2 years, ideally 5+)
- Strategy hypothesis documented

### Process

1. **Scaffold strategy** — Create directory under `strategies/<name>/`
2. **Implement core model** — `model.py`, `config.py`, `__init__.py`
3. **Write simulator** — `simulator.py` for backtest execution
4. **Run initial backtest** — Full dataset, default parameters
5. **Parameter optimization** — Sweep key parameters (use Optuna if >3 dimensions)
6. **Statistical validation**:
   - Significance test (p < 0.05)
   - Walk-forward analysis (out-of-sample validation)
   - Combinatorial purged cross-validation (CPCV) if sufficient data
   - Monte Carlo simulation for confidence intervals
7. **Fee analysis** — Apply realistic fees (maker + taker) to all results
8. **Regime analysis** — Test across market regimes (trending, ranging, volatile)
9. **Document results** — Write validation results to `.rules/patterns/`

### Tools

- Backtesting: Freqtrade or custom simulator
- Optimization: Optuna, scipy.optimize
- Statistics: statsmodels, scipy.stats
- Visualization: plotly, mplfinance
- See [libraries reference](.rules/reference/libraries-reference.md)

### Outputs

- Strategy code in `strategies/<name>/`
- Backtest results in `backtests/`
- Validation document in `.rules/patterns/<name>-validation-results.md`
- Go/no-go decision with evidence

### Go/No-Go Gate

| Criterion | Requirement |
|-----------|-------------|
| Sharpe ratio | > 1.0 (after fees) |
| Max drawdown | < 25% |
| Statistical significance | p < 0.05 |
| Walk-forward | Positive OOS performance |
| Fee survival | Profitable NET of realistic fees |
| Regime robustness | Profitable in >1 regime or with regime filter |
| Profit factor | > 1.3 |

**If NO-GO**: Document evidence, update catalog status, close beads. Strategy knowledge is preserved for future reference (see MRBB example in `.rules/patterns/mrbb-validation-results.md`).

### Beads/GSD Commands

```bash
bd update <epic-id> --status=in_progress
bd create --title="Implement <strategy> model" --type=task --priority=1
bd create --title="Backtest <strategy> against historical data" --type=task --priority=1
bd create --title="Statistical validation for <strategy>" --type=task --priority=1
# On completion:
bd close <task-ids> --reason="Validated — GO" # or "Validated — NO-GO"
```

---

## Phase 3: Incubation (Paper Trading)

**Goal**: Validate that live market behavior matches backtest expectations.

### Prerequisites

- Phase 2 complete with go decision
- Paper trading infrastructure ready (`/run-test`)
- Exchange API credentials configured

### Process

1. **Configure paper trader** — Set parameters matching best backtest config
2. **Run minimum 1 week** — Capture fills, spreads, latency, slippage
3. **Daily monitoring** — Check P&L, fill rates, inventory levels
4. **Compare to backtest** — Track deviation from expected performance:
   - Fill rate within 20% of backtest expectation
   - Spread capture within 30% of backtest
   - Drawdown within 1.5x backtest maximum
5. **Identify execution issues** — Latency, WebSocket disconnects, order rejections
6. **Run 2+ weeks for market making** — Need sufficient trades for significance

### Tools

```bash
/run-test                             # Default paper trading
/run-test --gamma 0.001 --interval 3  # Custom parameters
/stop                                 # Graceful shutdown
```

- PostgreSQL instance tracking for session persistence
- Log files in `logs/`

### Outputs

- Paper trading session logs
- Performance comparison: backtest vs paper
- List of execution issues discovered
- Go/no-go for live deployment

### Go/No-Go Gate

| Criterion | Requirement |
|-----------|-------------|
| Minimum duration | 1 week (2+ for market making) |
| P&L direction | Positive or within expected variance |
| Fill rate | Within 20% of backtest expectation |
| Max drawdown | < 1.5x backtest maximum |
| System stability | No crashes, <1% dropped WebSocket messages |
| Execution quality | Slippage < 50% of spread capture |

### Beads/GSD Commands

```bash
bd create --title="Paper trade <strategy> for 2 weeks" --type=task --priority=1
bd update <task-id> --status=in_progress
# Daily check-ins as comments or sub-tasks
bd close <task-id> --reason="Paper validated — ready for live"
```

---

## Phase 4: Live Deployment

**Goal**: Generate real returns with managed risk.

### Prerequisites

- Phase 3 complete with go decision
- Exchange API keys for live trading
- Risk limits configured
- Kill switch tested

### Process

1. **Start conservative** — 25% of target position size
2. **Monitor closely** — First 48h require manual oversight
3. **Scale up** — If performing within bounds:
   - Day 1-3: 25% size
   - Week 1: 50% size
   - Week 2+: 100% size (if metrics hold)
4. **Set alerts** — Drawdown, position limits, system health
5. **Weekly review** — Compare live vs paper vs backtest

### Tools

```bash
/run-live                    # Live trading (requires confirmation)
/run-live --dry-run          # Override to paper mode
/stop                        # Graceful shutdown (cancels open orders)
```

### Outputs

- Live trading session logs
- Weekly performance reports
- Risk event documentation

### Continuous Monitoring Gates

| Criterion | Action if Breached |
|-----------|-------------------|
| Daily drawdown > 5% | Reduce position size 50% |
| Weekly drawdown > 10% | Pause trading, investigate |
| Monthly drawdown > 20% | Stop strategy, full review |
| Sharpe < 0.5 (rolling 30d) | Flag for review |
| System downtime > 1h | Alert, investigate root cause |

### Beads/GSD Commands

```bash
bd create --title="Deploy <strategy> live — conservative" --type=task --priority=1
bd create --title="Scale <strategy> to full size" --type=task --priority=2
```

---

## Phase 5: Analysis & Iteration

**Goal**: Continuously improve strategy performance and identify new opportunities.

### Prerequisites

- Strategy running in Phase 3 or 4
- Sufficient data for meaningful analysis (2+ weeks)

### Process

1. **Performance review** — Weekly metrics: Sharpe, drawdown, fill rate, P&L
2. **Regime analysis** — How did the strategy perform in different market conditions?
3. **Parameter drift** — Are optimal parameters shifting? Is re-optimization needed?
4. **Edge decay** — Is the alpha signal weakening over time?
5. **New hypothesis** — Did the analysis reveal new opportunities? Loop to Phase 1.
6. **Document learnings** — Update `.rules/patterns/` with findings

### Tools

- Performance analytics: pyfolio, empyrical
- Statistical tests: scipy.stats
- Visualization: plotly
- Knowledge base: `/query`

### Outputs

- Performance report document
- Parameter update recommendations
- New strategy hypotheses (loop to Phase 1)
- Updated `.rules/` documentation

### Loop Triggers

| Finding | Action |
|---------|--------|
| Parameter drift detected | Re-optimize (back to Phase 2, step 5) |
| Edge decay >50% | Full re-evaluation (Phase 2) |
| New alpha signal | New research cycle (Phase 1) |
| Strategy failure | NO-GO, shelve, document (Phase 2 gate) |
| Execution improvement | Update code, test (Phase 3) |

### Beads/GSD Commands

```bash
bd create --title="Monthly review: <strategy>" --type=task --priority=2
bd create --title="Research: <new hypothesis from analysis>" --type=epic --priority=3
```

---

## Strategy File Structure

Every strategy follows this layout:

```
strategies/<name>/
├── __init__.py          # Package init
├── model.py             # Core strategy logic
├── config.py            # Parameters and defaults
├── simulator.py         # Backtesting engine
├── live_trader.py       # Live/paper execution (if applicable)
└── README.md            # Strategy-specific notes (optional)
```

Additional files as needed: `regime.py`, `risk_manager.py`, `order_manager.py`, etc.

---

## Integration with Project Systems

### Beads (What)

- **Epics** = strategy research/implementation initiatives
- **Tasks** = individual pipeline steps (backtest, paper trade, etc.)
- **Dependencies** = enforce phase ordering

### GSD (How)

- Use `/gsd:plan-phase` for complex implementation steps
- Use `/gsd:execute-phase` for parallel task execution
- Use `/gsd:verify-work` after each phase gate

### Cognee (Knowledge)

- `/query` before Phase 1 to check existing knowledge
- Document all findings in `.rules/` for future retrieval
- Session capture via `/land` preserves context

---

## Quick Reference

| I want to... | Start here |
|--------------|-----------|
| Find a new strategy to research | [Strategy Catalog](.rules/reference/strategies-catalog.md) |
| Check what libraries I need | [Libraries Reference](.rules/reference/libraries-reference.md) |
| Start a new strategy project | Phase 1 above, then `bd create --type=epic` |
| Validate a backtest result | Phase 2 Go/No-Go Gate |
| Deploy to paper trading | Phase 3, then `/run-test` |
| Go live | Phase 4, then `/run-live` |
| Review strategy performance | Phase 5 process |

---

## Related Documents

- [CONSTITUTION.md](./CONSTITUTION.md) — Core values (survive first, data over intuition)
- [VISION.md](./VISION.md) — Long-term direction
- [PLAN.md](./PLAN.md) — Current working milestones
- [Strategy Catalog](.rules/reference/strategies-catalog.md) — All known strategies
- [Libraries Reference](.rules/reference/libraries-reference.md) — Python tooling

---

**Remember**: Every strategy must earn its way through the pipeline. No shortcuts.
