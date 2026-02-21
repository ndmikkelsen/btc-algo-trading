# MRBB Parameter Research — Literature Findings

> Evidence-based parameter recommendations for Bollinger Band mean reversion on crypto.
>
> **Status: SHELVED** -- Strategy failed validation (Feb 2026). See `mrbb-validation-results.md` for full evidence.

## Sources

- [Efe Arda (2025) "Bollinger Bands under Varying Market Regimes" (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5775962)
- [ETH Zurich Master Thesis — Backtesting Trading Strategies for Bitcoin](https://ethz.ch/content/dam/ethz/special-interest/mtec/chair-of-entrepreneurial-risks-dam/documents/dissertation/master%20thesis/Master_Thesis_Gl%C3%BCcksmann_13June2019.pdf)
- [QuantifiedStrategies — Bollinger Bands Backtesting (360 years of data)](https://www.quantifiedstrategies.com/bollinger-bands-trading-strategy/)
- [Alpaca — Algo Trading Bitcoin with BB + RSI](https://alpaca.markets/learn/algo-trading-bitcoin-using-bollinger-bands-and-rsi)
- [Taylor & Francis — RL for Bitcoin Technical Strategies (2025)](https://www.tandfonline.com/doi/full/10.1080/23322039.2025.2594873)

## Parameter Recommendations

| Parameter | Our Default | Literature Range | Recommendation |
|-----------|-------------|------------------|----------------|
| BB Period | 20 | 15-30 | 20 (standard, most validated) |
| BB Std Dev | 2.0 | 1.5-3.0 | 2.0-2.5 (wider for crypto fat tails) |
| BB Inner Std | 1.0 | — | Keep 1.0 (partial exit target) |
| MA Type | SMA | SMA, EMA | SMA (most backtested) |
| RSI Period | 14 | 2-14 | 14 (standard; 2 for Connors RSI variant) |
| RSI Oversold | 30 | 20-30 | 30 (consider 20 for fewer/higher-quality signals) |
| RSI Overbought | 70 | 70-80 | 70 (consider 80 for fewer/higher-quality signals) |
| Timeframe | 5m | 15m-4h | 1h-4h recommended by research; 5m is more noise |
| Stop Loss | 1.5x ATR | 1.0-2.0x ATR | 1.5x ATR (research warns stops hurt MR strategies) |
| Target | 80% to center | Middle band | Middle band (80% is reasonable partial target) |

## Key Findings

### 1. Regime Dependence is Critical
Efe Arda (2025) found BB strategies exhibit **regime-dependent behavior**:
- **Ranging/accumulation**: Mean reversion profitable
- **Trending/breakout**: Mean reversion FAILS; breakout strategies outperform
- **Bear markets (2018)**: MR signals failed amid sustained declines
- Implication: ADX filter or regime detection is essential (we have none currently)

### 2. Standard Deviation for Crypto
- Standard 2.0σ captures ~95% of price action
- Crypto has **fatter tails** than equities — 2.5σ may reduce false signals
- QuantifiedStrategies found SMA 20 + 2σ on 60-min was optimal (47% win rate)
- Multi-timeframe strategy used **1.5σ** for more frequent but noisier signals

### 3. RSI Confirmation Reduces False Entries
- Combined BB + RSI is the most recommended approach across literature
- Standard 14/30/70 is widely validated for crypto
- Some crypto practitioners use 80/20 thresholds for higher conviction
- 2-period RSI (Connors) is more responsive but untested for crypto

### 4. Timeframe Matters
- 1H-4H: Best signal quality for crypto MR
- 5m: More noise, more false signals; need tighter filters
- 1D: Good for swing; standard params work well

### 5. Stop-Loss Trade-off
- Research consistently warns stops HURT mean reversion
- BUT without stops, drawdowns can be severe in trending markets
- Compromise: wider stops (2.0-2.5x ATR) or regime-based exit only

## Gaps in Research (Need Backtesting)

1. **VWAP confirmation**: No strong evidence for/against in crypto MR
2. **Keltner Channel squeeze**: TTM Squeeze (Carter) popular but no crypto-specific research
3. **Holding period**: No literature guidance on optimal max hold for crypto MR
4. **5m timeframe**: Very little research at this granularity for crypto
5. **Inner band partial exit**: No academic evidence on partial profit-taking

## Optimization Priorities (from research)

Based on the literature, our parameter optimization should focus on:
1. **BB_STD_DEV**: Test 1.5, 2.0, 2.5 (biggest impact per research)
2. **RSI thresholds**: Test 20/80 vs 25/75 vs 30/70 (signal quality vs frequency)
3. **Timeframe**: Compare 5m vs 15m vs 1h performance
4. **Regime filter**: Add ADX-based filter (most consistent finding in research)
5. **Stop-loss**: Test no stop vs 1.5x ATR vs 2.5x ATR (contentious in literature)
