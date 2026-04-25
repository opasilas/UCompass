Feature: Structured planning

  Scenario: Student has a busy week
    When I create 5 tasks in one week
    Then the dashboard should show a busy week
