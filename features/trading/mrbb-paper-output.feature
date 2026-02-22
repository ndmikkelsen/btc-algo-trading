@trading
Feature: MRBB Paper Trader Status Output
  As a paper trader
  I want detailed colored status output showing why a trade would or wouldn't fire
  So that I can understand the model's decision-making in real time

  Background:
    Given a DirectionalTrader with a default MeanReversionBB model

  # --- No Signal ---

  Scenario: No entry conditions met shows all conditions as FAIL
    Given a signal with BB%=0.50, RSI=50.0, VWAP_dev=0.05, ADX=30.0, and regime=TREND
    When I format the status line
    Then the output should contain "FAIL" for BB condition
    And the output should contain "FAIL" for RSI condition
    And the output should contain "FAIL" for VWAP condition
    And the output should contain "FAIL" for ADX condition
    And the output should not contain "ENTRY SIGNAL"

  # --- Partial Signal ---

  Scenario: Partial conditions met shows mixed PASS and FAIL
    Given a signal with BB%=0.02, RSI=55.0, VWAP_dev=0.01, ADX=15.0, and regime=RANGE
    When I format the status line
    Then the output should contain "PASS" for BB condition
    And the output should contain "FAIL" for RSI condition
    And the output should contain "PASS" for VWAP condition
    And the output should contain "PASS" for ADX condition
    And the output should not contain "ENTRY SIGNAL"

  # --- Full Long Signal ---

  Scenario: All long entry conditions met shows ENTRY SIGNAL LONG
    Given a signal with BB%=0.02, RSI=25.0, VWAP_dev=0.01, ADX=18.0, and regime=RANGE
    And the signal is "long" with stop=94000.0 and target=97000.0
    When I format the status line
    Then the output should contain "ENTRY SIGNAL"
    And the output should contain "LONG"
    And the output should contain the stop price
    And the output should contain the target price

  # --- Full Short Signal ---

  Scenario: All short entry conditions met shows ENTRY SIGNAL SHORT
    Given a signal with BB%=0.98, RSI=75.0, VWAP_dev=0.01, ADX=18.0, and regime=RANGE
    And the signal is "short" with stop=106000.0 and target=103000.0
    When I format the status line
    Then the output should contain "ENTRY SIGNAL"
    And the output should contain "SHORT"
    And the output should contain the stop price
    And the output should contain the target price

  # --- Position Held ---

  Scenario: Position held shows unrealized P&L and bars held
    Given a signal with BB%=0.40, RSI=45.0, VWAP_dev=0.03, ADX=20.0, and regime=RANGE
    And a long position entered at 95000.0 with current price 96000.0
    And the position has been held for 5 bars
    When I format the status line with the position
    Then the output should contain unrealized P&L
    And the output should contain "5/50"
