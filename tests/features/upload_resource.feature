
Feature: Upload resource

  Scenario: Add a new resource
    Given the app is initialised
    And I am logged in as a wellbeing officer with email "officer@example.com"
    When I add a resource called "10 ways to destress" with category "Wellbeing"
    Then the resource "10 ways to destress" should exist in the system

