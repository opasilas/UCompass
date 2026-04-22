Feature: Log work

  Scenario: Teacher adds an academic deadline
    When I add a deadline called Essay Deadline with a deadline of 2026-05-10
    Then the response should be successful

  Scenario: Teacher adds a supporting resource
    When I add a resource called Study Skills Guide in Academic Support
    Then the resource response should be successful
