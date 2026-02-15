@trading
Feature: Mean Reversion Bollinger Band Signals
  As a directional trader
  I want to generate mean reversion signals from Bollinger Bands, RSI, and VWAP
  So that I can enter high-probability counter-trend trades

  Background:
    Given a default MeanReversionBB model

  # --- Long Signals ---

  Scenario: Price at lower BB with oversold RSI generates long signal
    Given OHLCV data where price drops to the lower Bollinger Band
    And the RSI is oversold
    And the market is not in a squeeze
    When I calculate signals
    Then the signal should be "long"
    And the RSI should be below 30
    And the BB position should be below 0.1

  Scenario: Price at lower BB with neutral RSI generates no signal
    Given OHLCV data where price drops to the lower Bollinger Band
    But the RSI is neutral
    When I calculate signals
    Then the signal should be "none"

  # --- Short Signals ---

  Scenario: Price at upper BB with overbought RSI generates short signal
    Given OHLCV data where price rises to the upper Bollinger Band
    And the RSI is overbought
    And the market is not in a squeeze
    When I calculate signals
    Then the signal should be "short"
    And the RSI should be above 70
    And the BB position should be above 0.9

  Scenario: Price at upper BB with neutral RSI generates no signal
    Given OHLCV data where price rises to the upper Bollinger Band
    But the RSI is neutral
    When I calculate signals
    Then the signal should be "none"

  # --- Squeeze Behavior ---

  Scenario: No signal during active squeeze
    Given OHLCV data with a volatility squeeze
    And the price is at the lower Bollinger Band
    And the RSI is oversold
    When I calculate signals
    Then the signal should be "none"
    And the squeeze flag should be true

  Scenario: Signal restored after squeeze ends
    Given OHLCV data where a squeeze ends with expansion
    And the price drops to the lower Bollinger Band
    And the RSI is oversold
    When I calculate signals
    Then the signal should be "long"
    And the squeeze flag should be false

  # --- Indicator Outputs ---

  Scenario: Bollinger Bands contain price action
    Given ranging OHLCV data with 200 candles
    When I calculate signals
    Then the BB position should be between 0 and 1

  Scenario: VWAP deviation is reported
    Given ranging OHLCV data with 200 candles
    When I calculate signals
    Then the VWAP deviation should be a non-negative number

  Scenario: Bandwidth percentile is reported
    Given ranging OHLCV data with 200 candles
    When I calculate signals
    Then the bandwidth percentile should be between 0 and 100

  # --- Order Generation ---

  Scenario: Long signal produces entry order with stop and target
    Given OHLCV data where price drops to the lower Bollinger Band
    And the RSI is oversold
    And the market is not in a squeeze
    When I calculate signals
    And I generate orders with equity 10000 and ATR 500
    Then an order should be generated
    And the order side should be "long"
    And the stop loss should be below the entry price
    And the target should be above the entry price

  Scenario: No orders generated for no signal
    Given ranging OHLCV data with 200 candles
    And the signal is "none"
    When I generate orders with equity 10000 and ATR 500
    Then no orders should be generated
