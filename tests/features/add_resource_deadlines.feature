Scenario: Add deadlines to resources and opportunities
    When I add a deadline to a resource "21-01-2026"
    Then the system should add this deadline
    And the deadline date should show as "21-01-2026"