import os
import sys
from datetime import date, timedelta
from pytest_bdd import scenarios, when, then

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app

app = create_app()
client = app.test_client()
response = None

scenarios("../features/reminders.feature")


@when("I create a task due in 7 days")
def create_task_due_soon():
    global response
    deadline = (date.today() + timedelta(days=7)).isoformat()
    response = client.post(
        "/create_task",
        data={
            "title": "Reminder Task",
            "description": "Deadline approaching",
            "deadline": deadline,
            "student_email": "student@example.com"
        },
        follow_redirects=True
    )


@then("the dashboard should show a reminder or countdown")
def check_reminder_exists():
    dashboard_response = client.get("/student_dashboard", follow_redirects=True)
    assert dashboard_response.status_code == 200

    assert (
        b"reminder" in dashboard_response.data.lower()
        or b"countdown" in dashboard_response.data.lower()
        or b"deadline" in dashboard_response.data.lower()
    )
