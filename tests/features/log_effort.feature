Feature: Add effort hours

  Scenario: Log effort on a task
    Given the app is initialised
    And I am logged in as a student with email "student@example.com"
    And I have an existing task
    When I log "2.0" hours of effort on my task
    Then the logged effort should be "2.0"
