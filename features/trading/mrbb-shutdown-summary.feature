@trading
Feature: MRBB Shutdown Summary
  As a directional trader
  I want a comprehensive session summary at shutdown
  So that I can review trade history, signal counts, runtime, and performance metrics

  Background:
    Given a running MRBB paper trader

  # --- No Trades ---

  Scenario: Shutdown with no trades
    Given the trader has been running for 30 minutes
    And no positions were entered
    When the trader shuts down
    Then the summary should show runtime in HH:MM:SS format
    And the summary should show signal counts
    And the summary should show "No trades taken"

  # --- Profitable Session ---

  Scenario: Shutdown after profitable session
    Given the trader completed 3 winning long trades
    When the trader shuts down
    Then the summary should show positive total P&L
    And the summary should show per-trade P&L breakdown
    And the summary should show win rate of 100%

  # --- Losing Session ---

  Scenario: Shutdown after losing session
    Given the trader completed 2 losing short trades
    When the trader shuts down
    Then the summary should show negative total P&L
    And the summary should show max drawdown

  # --- Mixed Trades ---

  Scenario: Shutdown with mixed trades
    Given the trader completed 2 winning and 1 losing trades
    When the trader shuts down
    Then the summary should show complete trade breakdown
    And the summary should show best trade P&L
    And the summary should show worst trade P&L
    And the summary should show profit factor
