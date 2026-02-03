# Skill: Log Backtest

Log backtest results to the knowledge base for future querying via Cognee.

## Trigger

Use when:
- User runs a backtest and wants to save the findings
- User says "log this backtest", "save these results", "record this"
- After completing a significant backtest analysis

## Process

### 1. Run the Backtest (if not already done)

```bash
python3 -m freqtrade backtesting -c config/config.json --strategy STRATEGY_NAME --datadir user_data/data
```

### 2. Generate the Finding Report

Use the log_backtest.py script:

```bash
python3 scripts/log_backtest.py \
  --strategy STRATEGY_NAME \
  --no-run \
  --notes "Your analysis notes here"
```

Options:
- `--strategy, -s`: Strategy name (required)
- `--notes, -n`: Notes about the backtest findings
- `--tags`: Comma-separated tags (e.g., "optimization,4h,btc")
- `--no-run`: Use latest results instead of running new backtest
- `--timerange, -t`: Specific time range (e.g., 20250601-20260101)
- `--sync`: Auto-sync to Cognee after saving

### 3. Edit the Finding (Optional)

The report is saved to `backtests/findings/YYYY-MM-DD_HHMM_strategy.md`

Add:
- Lessons learned
- Next steps
- Additional analysis

### 4. Sync to Cognee

```bash
.claude/scripts/sync-to-cognee.sh backtests
```

Or sync all:
```bash
.claude/scripts/sync-to-cognee.sh
```

## Finding Report Structure

Each finding includes:

1. **Summary Table**: Key metrics (trades, win rate, profit, drawdown)
2. **Automated Analysis**: Pattern detection based on metrics
3. **Notes**: User-provided context
4. **Configuration Snapshot**: Strategy parameters at time of test
5. **Lessons Learned**: What was discovered
6. **Next Steps**: Action items based on findings

## Example Workflow

```bash
# Run backtest
python3 -m freqtrade backtesting -c config/config.json --strategy MACDBB

# Log the results with notes
python3 scripts/log_backtest.py \
  --strategy MACDBB \
  --no-run \
  --notes "Tested with 5-candle lookback. Win rate improved but profit factor still low. Need to investigate exit timing."

# Sync to Cognee
.claude/scripts/sync-to-cognee.sh backtests
```

## Querying Past Results

After syncing, query findings with:

```
/query "What were the best performing backtest configurations?"
/query "What lessons did we learn from MACDBB testing?"
/query "Which backtests had win rates above 60%?"
```

## Tips

- Always add meaningful notes explaining WHY results are good/bad
- Tag findings for easier filtering (e.g., "optimization", "baseline", "experiment")
- Record lessons learned while fresh - they're valuable for future decisions
- Include next steps so you remember what to try
