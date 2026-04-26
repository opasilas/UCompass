Feature: View resources

  Scenario: View resources on student dashboard
    Given the app is initialised
    And I am logged in as a student with email "student@ucompass.com"
    And there are resources in the system
    When I visit the student dashboard
    Then I should be able to view the resources