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


def login_as_student():
    with client.session_transaction() as sess:
        sess["user_email"] = "student@example.com"
        sess["user_role"] = "student"


@when("I create a task due in 7 days")
def create_task_due_soon():
    global response
    login_as_student()

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
    login_as_student()

    dashboard_response = client.get("/student_dashboard", follow_redirects=True)

    # Debug: will print what the test sees
    print(dashboard_response.data.decode())

    assert dashboard_response.status_code == 200

    assert (
        b"upcoming deadlines" in dashboard_response.data.lower()
        and b"due in" in dashboard_response.data.lower()
    )
