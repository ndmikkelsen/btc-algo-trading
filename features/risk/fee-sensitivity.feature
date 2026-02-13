@risk
Feature: Fee Sensitivity and Break-Even Analysis
  As a market maker on MEXC
  I want to understand the impact of fees on profitability
  So that I can verify that 0% maker fees make all spreads viable

  # --- Minimum Profitable Spread ---

  Scenario: Regular tier has zero minimum spread
    Given the Regular fee tier at 100000 BTC price
    When I calculate the minimum profitable spread
    Then the minimum spread should be 0.0 percent
    And the minimum spread in dollars should be 0.0

  Scenario: MX Deduction tier also has zero minimum spread
    Given the MX Deduction fee tier at 100000 BTC price
    When I calculate the minimum profitable spread
    Then the minimum spread should be 0.0 percent
    And the minimum spread in dollars should be 0.0

  # --- Break-Even at Typical BBO ---

  Scenario: Regular tier is viable at typical BBO
    Given the Regular fee tier at 100000 BTC price
    When I generate an economics report with BBO of 0.20 dollars
    Then the strategy should be viable at typical BBO

  Scenario: MX Deduction tier is viable at typical BBO
    Given the MX Deduction fee tier at 100000 BTC price
    When I generate an economics report with BBO of 0.20 dollars
    Then the strategy should be viable at typical BBO
