Scenario: Add a new resource or opportunity
    When I add a resource or opportunity called "view algorithms and formulas" on "05-01-2026"
    Then the resource "view algorithms" should exist in the system
    And the resource should "view algorithms" should be on the student dashboard
    And the resource should "view algorithms" should be on the teacher dashboard
    And the resource name should be named "view algorithms"

