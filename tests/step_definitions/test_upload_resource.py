import os
os.chdir("/Users/saffronforde/PycharmProjects/Student help/UCompass")

from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers
from app import create_app, load_data

scenarios(Path(__file__).parent.parent / "features" / "upload_resource.feature")

app = create_app()
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
client = app.test_client()
response = None

@given("the app is initialised")
def initialise_app():
    global client
    with app.app_context():
        app.tasks_data = load_data('tasks.json')
        app.resources_data = load_data('resources.json')
        app.users_data = load_data('users.json')
    client = app.test_client()

@given(parsers.parse('I am logged in as a wellbeing officer with email "{email}"'))
def logged_in_as_wellbeing(email):
    global client
    client = app.test_client()
    with client.session_transaction() as session:
        session['user_role'] = 'wellbeing_officer'
        session['user_email'] = email

@when(parsers.parse('I add a resource called "{title}" with category "{category}"'))
def add_resource(title, category):
    global response
    response = client.post('/manage_resources', data={
        "title": title,
        "category": category,
    })

@then(parsers.parse('the resource "{title}" should exist in the system'))
def resource_should_exist(title):
    resources = load_data('resources.json')
    assert any(r["title"] == title for r in resources)