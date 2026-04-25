Feature: Academic reminders

  Scenario: Student sees a reminder for an upcoming deadline
    When I create a task due in 7 days
    Then the dashboard should show a reminder or countdown
