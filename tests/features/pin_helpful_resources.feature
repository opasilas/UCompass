Feature: Pin resources

  Scenario: Pin resources on dashboard
    Given the app is initialised
    And I am logged in as a student with email "student@example.com"
    And there are resources in the system
    When I pin the resources on a student dashboard
    Then the resources should be highlighted and pinned
