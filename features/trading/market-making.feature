@trading
Feature: Avellaneda-Stoikov Market Making
  As a market maker
  I want to calculate optimal bid and ask quotes
  So that I can profit from the spread while managing inventory risk

  Background:
    Given a BTC mid price of 50000
    And a default Avellaneda-Stoikov model

  # --- Reservation Price ---

  Scenario: Reservation price equals mid price with zero inventory
    Given an inventory of 0
    And a volatility of 0.02
    And a time remaining of 0.5
    When I calculate the reservation price
    Then the reservation price should equal the mid price

  Scenario: Reservation price is below mid price with long inventory
    Given an inventory of 5
    And a volatility of 0.02
    And a time remaining of 0.5
    When I calculate the reservation price
    Then the reservation price should be below the mid price

  Scenario: Reservation price is above mid price with short inventory
    Given an inventory of -5
    And a volatility of 0.02
    And a time remaining of 0.5
    When I calculate the reservation price
    Then the reservation price should be above the mid price

  # --- Optimal Spread ---

  Scenario: Spread widens with higher volatility
    Given a model with high risk aversion and liquidity
    And a volatility of 0.005
    And a time remaining of 0.5
    When I calculate the optimal spread at this volatility
    And I recalculate with a volatility of 0.02
    Then the second spread should be wider than the first

  Scenario: Spread respects minimum dollar bound
    Given a volatility of 0.0001
    And a time remaining of 0.01
    When I calculate the quotes
    Then the dollar spread should be at least the minimum dollar spread

  Scenario: Spread respects maximum dollar bound
    Given a volatility of 1.0
    And a time remaining of 1.0
    When I calculate the quotes
    Then the dollar spread should be at most the maximum dollar spread

  # --- Quote Calculation ---

  Scenario: Bid is below ask
    Given an inventory of 0
    And a volatility of 0.02
    And a time remaining of 0.5
    When I calculate the quotes
    Then the bid should be below the ask

  Scenario: Quotes straddle the reservation price
    Given an inventory of 0
    And a volatility of 0.02
    And a time remaining of 0.5
    When I calculate the quotes
    Then the bid should be below the reservation price
    And the ask should be above the reservation price

  # --- Inventory Management ---

  Scenario: Long inventory shifts quotes downward
    Given a volatility of 0.02
    And a time remaining of 0.5
    When I calculate quotes with inventory 0
    And I calculate quotes with inventory 5
    Then the long-inventory bid should be lower than the neutral bid
    And the long-inventory ask should be lower than the neutral ask

  Scenario: Short inventory shifts quotes upward
    Given a volatility of 0.02
    And a time remaining of 0.5
    When I calculate quotes with inventory 0
    And I calculate quotes with inventory -5
    Then the short-inventory bid should be higher than the neutral bid
    And the short-inventory ask should be higher than the neutral ask

  # --- Volatility Estimation ---

  Scenario: Volatility calculated from price series
    Given a series of 100 BTC prices
    When I calculate the volatility
    Then the volatility should be a positive number

  Scenario: Default volatility for insufficient data
    Given a series of 2 BTC prices
    When I calculate the volatility
    Then the volatility should be the default 0.02
