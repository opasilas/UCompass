import os
import sys
from pytest_bdd import scenarios, when, then, parsers

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app

app = create_app()
client = app.test_client()
response = None

scenarios("../features/log_work.feature")


@when(parsers.parse("I add a deadline called {title} with a deadline of {deadline}"))
def add_deadline(title, deadline):
    global response
    response = client.post(
        "/create_task",
        data={
            "title": title,
            "description": "Test deadline description",
            "deadline": deadline,
            "student_email": "student@example.com"
        },
        follow_redirects=True
    )


@then("the response should be successful")
def check_response_success():
    assert response.status_code == 200


@when(parsers.parse("I add a resource called {title} in {category}"))
def add_resource(title, category):
    global response
    response = client.post(
        "/manage_resources",
        data={
            "title": title,
            "category": category,
            "content": "Test resource content"
        },
        follow_redirects=True
    )


@then("the resource response should be successful")
def check_resource_response_success():
    assert response.status_code == 200
