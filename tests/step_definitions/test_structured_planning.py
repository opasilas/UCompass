import os
import sys
from pytest_bdd import scenarios, when, then

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app

app = create_app()
client = app.test_client()
response = None

scenarios("../features/structured_planning.feature")


@when("I create 5 tasks in one week")
def create_busy_week_tasks():
    global response
    for i in range(5):
        response = client.post(
            "/create_task",
            data={
                "title": f"Task {i+1}",
                "description": "Busy week task",
                "deadline": f"2026-05-0{i+1}",
                "student_email": "student@example.com"
            },
            follow_redirects=True
        )


@then("the dashboard should show a busy week")
def check_busy_week():
    dashboard_response = client.get("/student_dashboard", follow_redirects=True)
    assert dashboard_response.status_code == 200
    assert b"busy" in dashboard_response.data.lower()
