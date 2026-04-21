Scenario: Log effort
    When I edit a task and add the amount of hours "2.0"
    Then the system should add the amount of hours to the Logged Effort column
    And the logged effort should be named "2.0"