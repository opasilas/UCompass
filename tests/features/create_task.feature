Feature: Create new task

  Scenario: Add a new task
    When I add a task called "Revise Machine Learning" with a "2026-01-05"
    Then the task "Revise Machine Learning" with deadline "2026-01-05" should be added