import os
import sys
from pytest_bdd import scenarios, when, then

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app

app = create_app()
client = app.test_client()
response = None

scenarios("../features/ec_highlighting.feature")


def login_as_student():
    with client.session_transaction() as sess:
        sess["user_email"] = "student@example.com"
        sess["user_role"] = "student"


@when("I create 5 tasks in one week and add an EC resource")
def create_busy_week_and_ec_resource():
    global response
    login_as_student()

    for i in range(5):
        client.post(
            "/create_task",
            data={
                "title": f"EC Busy Task {i+1}",
                "description": "Busy week task",
                "deadline": f"2026-05-0{i+1}",
                "student_email": "student@example.com"
            },
            follow_redirects=True
        )

    response = client.post(
        "/manage_resources",
        data={
            "title": "Extenuating Circumstances",
            "category": "Support",
            "content": "EC guidance and support"
        },
        follow_redirects=True
    )


@then("the dashboard should show the EC resource")
def check_ec_resource():
    login_as_student()

    dashboard_response = client.get("/student_dashboard", follow_redirects=True)

    # Debug: prints the page HTML so we can see the exact wording
    print(dashboard_response.data.decode())

    assert dashboard_response.status_code == 200

    assert b"extenuating circumstances" in dashboard_response.data.lower()
        
