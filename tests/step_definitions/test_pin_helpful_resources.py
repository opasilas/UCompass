import os
os.chdir("/Users/saffronforde/PycharmProjects/Student help/UCompass")

from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers
from app import create_app, load_data, save_data

scenarios(Path(__file__).parent.parent / "features" / "pin_helpful_resources.feature")

app = create_app()
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
client = None
response = None
resource_id = None

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
    with client.session_transaction() as session:
        session['user_role'] = 'student'
        session['user_email'] = email

@given("there are resources in the system")
def resources_in_system():
    global resource_id
    with app.app_context():
        if not app.resources_data:
            new_resource = {
                'id': 1,
                'title': 'Test Resource',
                'category': 'Wellbeing',
                'content': 'Some content',
                'created_by': 'officer@example.com',
                'pinned': False
            }
            app.resources_data.append(new_resource)
            save_data('resources.json', app.resources_data)
        resource_id = app.resources_data[0]['id']

@when("I pin the resource")
def pin_resource():
    global response
    with client.session_transaction() as session:
        session['user_role'] = 'student'
        session['user_email'] = 'student@example.com'
    response = client.post(f'/pin_resource/{resource_id}', data={
        "next": ""
    })

@then("the resources should be pinned")
def resource_should_be_pinned():
    assert response.status_code == 302
    resources = load_data('resources.json')
    resource = next((r for r in resources if r['id'] == resource_id), None)
    assert resource is not None
    assert resource['pinned'] == True