Feature: EC highlighting

  Scenario: EC resource is highlighted during a busy week
    When I create 5 tasks in one week and add an EC resource
    Then the dashboard should show the EC resource
