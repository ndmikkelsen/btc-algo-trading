@backtesting
Feature: Directional Backtesting Simulator
  As a quantitative trader
  I want to backtest mean reversion strategies on historical OHLCV data
  So that I can evaluate strategy performance before risking capital

  # --- Full Backtest ---

  Scenario: Backtest runs on OHLCV data and produces equity curve
    Given a MeanReversionBB model and DirectionalSimulator
    And 300 candles of ranging OHLCV data
    When I run the backtest
    Then the result should contain an equity curve with 300 entries
    And the result should contain a trade log
    And the result should contain total return percentage

  # --- Stop Loss ---

  Scenario: Stop loss triggers correctly for long positions
    Given a DirectionalSimulator with a long position
    And an entry price of 50000 and stop loss at 49000
    When a candle arrives with low 48900
    Then the position should be closed
    And the exit reason should be "stop_loss"
    And the trade PnL should be negative

  Scenario: Stop loss triggers correctly for short positions
    Given a DirectionalSimulator with a short position
    And an entry price of 50000 and stop loss at 51000
    When a candle arrives with high 51100
    Then the position should be closed
    And the exit reason should be "stop_loss"
    And the trade PnL should be negative

  # --- Target ---

  Scenario: Target exit triggers for long positions
    Given a DirectionalSimulator with a long position
    And an entry price of 50000 and target at 50500
    When a candle arrives with high 50600
    Then the position should be closed
    And the exit reason should be "target"
    And the trade PnL should be positive

  # --- Partial Exit ---

  Scenario: Partial exit reduces position at inner band
    Given a DirectionalSimulator with a long position of size 0.1
    And an entry price of 50000 and partial target at 50200
    When a candle arrives with high 50300 but below the full target
    Then the position should still be open
    And the position size should be approximately 0.05
    And the partial exit flag should be set

  # --- End of Data ---

  Scenario: Force close at end of data
    Given a MeanReversionBB model and DirectionalSimulator
    And OHLCV data that triggers a long entry
    When I run the backtest
    Then the trade log should not be empty
    And the last trade exit reason should be "end_of_backtest" or "stop_loss" or "target"

  # --- Metrics Compatibility ---

  Scenario: Backtest results are compatible with metrics calculation
    Given a MeanReversionBB model and DirectionalSimulator
    And 300 candles of ranging OHLCV data
    When I run the backtest
    Then the result should have key "equity_curve" as a list
    And the result should have key "trade_log" as a list
    And the result should have key "total_trades" as an integer
    And the result should have key "final_equity" as a number
    And the result should have key "total_return_pct" as a number
