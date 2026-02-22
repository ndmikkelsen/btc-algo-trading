@trading
Feature: MRBB Parameter Presets
  As a directional trader
  I want to load named parameter presets from YAML files
  So that I can quickly switch between tuned configurations

  Background:
    Given a PresetManager instance

  # --- Loading ---

  Scenario: Loading a named preset returns all parameters
    When I load the "default" preset
    Then the preset should contain all 18 tunable parameters

  Scenario: Loading a non-existent preset raises an error
    When I try to load the "nonexistent" preset
    Then it should raise a preset not found error

  # --- CLI Integration ---

  Scenario: CLI --preset flag loads preset params into model
    Given the "default" preset is available
    When I load the "default" preset
    And I construct a MeanReversionBB model from the preset
    Then the model should be valid

  Scenario: CLI args override preset params
    Given the "default" preset is available
    When I load the "default" preset with overrides bb_period=30
    Then the preset bb_period should be 30
    And all other parameters should match the default preset

  # --- Listing ---

  Scenario: Listing presets shows all available YAML files
    Given at least one preset YAML file exists
    When I list available presets
    Then the result should be a non-empty list of strings

  Scenario: Default preset appears in listing
    Given the "default" preset is available
    When I list available presets
    Then "default" should be in the list

  # --- Saving ---

  Scenario: Saving a preset creates a valid YAML file
    When I save a preset named "test-save" with default parameters
    Then a YAML file for "test-save" should exist
    And loading "test-save" should return the saved parameters
