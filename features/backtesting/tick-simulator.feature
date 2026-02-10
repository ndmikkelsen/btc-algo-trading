@backtesting
Feature: Tick-level Market Making Simulator
  As a quantitative trader
  I want to backtest market making strategies using tick-level data
  So that I can eliminate one-fill-per-candle bias and model queue position

  # --- Tick Data Generation ---

  Scenario: OHLCV candle converts to synthetic ticks
    Given a bullish candle with open 99000 high 101000 low 98500 close 100500
    When I convert it to 100 synthetic ticks
    Then I should get 100 ticks
    And the first tick price should be approximately 99000
    And the last tick price should be approximately 100500
    And all tick prices should be between 98500 and 101000

  Scenario: Tick volume sums to candle volume
    Given a candle with volume 5.0
    When I convert it to synthetic ticks
    Then the total tick volume should approximately equal 5.0

  # --- Fill Mechanics ---

  Scenario: Buy order fills when price drops to bid level
    Given a tick simulator with queue depth 0
    And a buy order at 99500
    When a tick arrives at price 99400
    Then the buy order should be filled

  Scenario: Sell order fills when price rises to ask level
    Given a tick simulator with queue depth 0
    And a sell order at 100500
    When a tick arrives at price 100600
    Then the sell order should be filled

  Scenario: Queue position delays fills
    Given a tick simulator with queue depth 1.0
    And a buy order at 99500
    When a tick arrives at price 99400 with volume 0.5
    Then the buy order should NOT be filled
    When another tick arrives at price 99300 with volume 0.6
    Then the buy order should be filled

  # --- Multiple Fills ---

  Scenario: Both sides can fill across separate ticks
    Given a tick simulator with queue depth 0
    And a buy order at 99500 and a sell order at 100500
    When a tick arrives at price 99400 then a tick at 100600
    Then both orders should be filled

  # --- Backtest ---

  Scenario: Tick backtest produces results
    Given a GLFT model and order manager
    And a series of 500 synthetic ticks around 100000
    When I run a tick-level backtest
    Then the result should contain an equity curve
    And the result should contain a trade count
    And the result should contain final PnL
