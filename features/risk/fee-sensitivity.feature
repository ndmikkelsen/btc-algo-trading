@risk
Feature: Fee Sensitivity and Break-Even Analysis
  As a market maker
  I want to understand the impact of fees on profitability
  So that I can determine which fee tiers make tight-spread strategies viable

  # --- Minimum Profitable Spread ---

  Scenario: Base tier minimum profitable spread
    Given the Regular fee tier at 100000 BTC price
    When I calculate the minimum profitable spread
    Then the minimum spread should be 0.04 percent
    And the minimum spread in dollars should be 40.0

  Scenario: VIP1 tier reduces minimum spread
    Given the VIP1 fee tier at 100000 BTC price
    When I calculate the minimum profitable spread
    Then the minimum spread should be 0.036 percent
    And the minimum spread in dollars should be 36.0

  Scenario: VIP2 tier further reduces minimum spread
    Given the VIP2 fee tier at 100000 BTC price
    When I calculate the minimum profitable spread
    Then the minimum spread should be 0.032 percent
    And the minimum spread in dollars should be 32.0

  # --- Market Maker Program ---

  Scenario: Market Maker Program makes tight spreads viable
    Given the Market Maker fee tier at 100000 BTC price
    When I calculate the minimum profitable spread
    Then the minimum spread in dollars should be -10.0
    And the strategy should be viable at typical BBO

  # --- Break-Even at Typical BBO ---

  Scenario: Base tier is not viable at typical BBO
    Given the Regular fee tier at 100000 BTC price
    When I generate an economics report with BBO of 0.20 dollars
    Then the strategy should not be viable at typical BBO
    And the spread gap should be 39.80 dollars

  Scenario: Market Maker Program is viable at typical BBO
    Given the Market Maker fee tier at 100000 BTC price
    When I generate an economics report with BBO of 0.20 dollars
    Then the strategy should be viable at typical BBO
