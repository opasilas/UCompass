Scenario: Add a new task
    When I add a task called "Revise Machine Learning" on "05-01-2026"
    Then the system should add this task
    And the event name should be named "Revise Machine Learning"