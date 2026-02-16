@trading
Feature: MEXC Exchange Client
  As a market maker
  I want to connect to MEXC exchange
  So that I can trade with 0% maker fees

  Scenario: Place a maker-only order
    Given a MEXC client configured for BTCUSDT
    When I place a LIMIT_MAKER buy order at 99000 for 0.001 BTC
    Then the order type should be LIMIT_MAKER
    And the order should be accepted

  Scenario: Dry-run simulates fill on price cross
    Given a dry-run client with 1000 USDT
    When I place a buy order at 99000 for 0.001 BTC
    And the price drops to 98999
    Then the order should be filled
    And my BTC balance should increase by 0.001

  Scenario: Dry-run rejects crossing maker order
    Given a dry-run client with current price at 100000
    When I place a LIMIT_MAKER buy order at 100001
    Then the order should be rejected

  Scenario: Market poller feeds order book collector
    Given a market poller connected to MEXC
    When I poll for market data
    Then the collector should have snapshots
    And the collector should have trades
