# Trading Rules

Core risk management rules that apply to ALL strategies.

## Position Sizing

- **Risk per trade**: 5% of total capital maximum
- **Starting capital**: $1,000 USDT
- **Max open trades**: 2

## Risk-Reward Ratio

- **Minimum R:R**: 2:1 (reward:risk)
- **Meaning**: For every $1 risked, target at least $2 profit
- **Example**: 3% stop loss → minimum 6% take profit target

## Calculations

With $1,000 capital and max 2 trades:
- Capital per trade: $500
- Risk per trade (5%): $50
- With $500 position and 5% stop loss: actual risk = $25 (2.5% of capital)
- With 2:1 R:R: take profit at 10%

## Implementation (Current)

```python
# config.json
max_open_trades = 2
stake_amount = 500
dry_run_wallet = 1000

# strategy config
STOPLOSS = -0.05  # 5% stop loss
TAKE_PROFIT = 0.10  # 10% for 2:1 R:R
TRAILING_STOP_POSITIVE_OFFSET = 0.10  # Activate trailing at 2:1 R:R

# minimal_roi (profit targets)
minimal_roi = {
    "0": 0.15,    # 15% profit anytime (3:1 R:R)
    "72": 0.12,   # 12% after 72 hours (2.4:1 R:R)
    "144": 0.10,  # 10% after 144 hours - minimum 2:1 R:R
}
```

## Rules Checklist

- [ ] Never enter a trade without defined stop loss
- [ ] Never move stop loss against the trade
- [ ] Always calculate R:R before entry
- [ ] Never risk more than 5% of capital per trade
- [ ] Maximum 2 positions open simultaneously
