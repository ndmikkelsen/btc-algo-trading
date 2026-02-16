@trading
Feature: GLFT Market Making Model
  As a market maker
  I want to use the GLFT infinite-horizon model
  So that I can quote optimally in 24/7 crypto markets without session boundaries

  Background:
    Given a BTC mid price of 100000
    And a default GLFT model

  # --- Optimal Spread ---

  Scenario: Optimal spread is positive
    Given a GLFT volatility of 0.005
    When I calculate the GLFT optimal spread
    Then the GLFT spread should be positive

  Scenario: Spread does not depend on time remaining
    Given a GLFT volatility of 0.005
    When I calculate the GLFT spread with time remaining 0.1
    And I calculate the GLFT spread with time remaining 0.9
    Then both GLFT spreads should be equal

  Scenario: Higher volatility produces wider spread
    Given a GLFT model with uncapped spread
    And a GLFT volatility of 0.002
    When I calculate the GLFT spread at low volatility
    And I recalculate the GLFT spread at volatility 0.01
    Then the second GLFT spread should be wider

  # --- Inventory Skew ---

  Scenario: Zero inventory produces symmetric quotes
    Given a GLFT volatility of 0.005
    And a GLFT inventory of 0
    When I calculate the GLFT quotes
    Then the GLFT bid and ask should be symmetric around mid

  Scenario: Long inventory shifts GLFT quotes downward
    Given a GLFT volatility of 0.005
    When I calculate GLFT quotes with inventory 0
    And I calculate GLFT quotes with inventory 5
    Then the long-inventory GLFT bid should be lower
    And the long-inventory GLFT ask should be lower

  Scenario: Short inventory shifts GLFT quotes upward
    Given a GLFT volatility of 0.005
    When I calculate GLFT quotes with inventory 0
    And I calculate GLFT quotes with inventory -5
    Then the short-inventory GLFT bid should be higher
    And the short-inventory GLFT ask should be higher

  # --- Fill Rate ---

  Scenario: Fill rate decreases with depth
    When I calculate the GLFT fill rate at depth 10
    And I calculate the GLFT fill rate at depth 100
    Then the deeper fill rate should be lower

  # --- Spread Bounds ---

  Scenario: Spread respects minimum dollar bound
    Given a GLFT volatility of 0.0001
    And a GLFT inventory of 0
    When I calculate the GLFT quotes
    Then the GLFT dollar spread should be at least the minimum

  Scenario: Spread respects maximum dollar bound
    Given a GLFT model with tight max spread
    And a GLFT volatility of 1.0
    And a GLFT inventory of 0
    When I calculate the GLFT quotes
    Then the GLFT dollar spread should be at most the maximum
