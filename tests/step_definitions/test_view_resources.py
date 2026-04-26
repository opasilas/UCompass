import os
os.chdir("/Users/saffronforde/PycharmProjects/Student help/UCompass")

from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers
from app import create_app, load_data, save_data

scenarios(Path(__file__).parent.parent / "features" / "view_resources.feature")

app = create_app()
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
client = None
response = None

@given("the app is initialised")
def initialise_app():
    global client
    with app.app_context():
        app.tasks_data = load_data('tasks.json')
        app.resources_data = load_data('resources.json')
        app.users_data = load_data('users.json')
    client = app.test_client()

@given(parsers.parse('I am logged in as a student with email "{email}"'))
def logged_in_as_student(email):
    global client
    with client.session_transaction() as session:
        session['user_role'] = 'student'
        session['user_email'] = email

@given("there are resources in the system")
def resources_in_system():
    with app.app_context():
        if not app.resources_data:
            new_resource = {
                'id': 1,
                'title': 'Test Resource',
                'category': 'Wellbeing',
                'content': 'Some content',
                'created_by': 'teacher@ucompass.com'
            }
            app.resources_data.append(new_resource)
            save_data('resources.json', app.resources_data)

@when("I visit the student dashboard")
def visit_student_dashboard():
    global response
    response = client.get('/student_dashboard')

@then("I should be able to view the resources")
def check_resources_visible():
    assert response.status_code == 200
    resources = load_data('resources.json')
    assert len(resources) > 0