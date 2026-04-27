import os
os.chdir("/Users/saffronforde/PycharmProjects/Student help/UCompass")

from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers
from app import create_app, load_data, save_data

scenarios(Path(__file__).parent.parent / "features" / "log_effort.feature")

app = create_app()
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
client = None
response = None
task_id = None

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

@given("I have an existing task")
def existing_task():
    global task_id
    with app.app_context():
        new_id = max([t['id'] for t in app.tasks_data]) + 1 if app.tasks_data else 1
        new_task = {
            'id': new_id,
            'title': 'Test Task',
            'description': '',
            'deadline': '2026-01-05',
            'student_email': 'student@ucompass.com',
            'logged_effort': 0.0,
            'notes': ''
        }
        app.tasks_data.append(new_task)
        save_data('tasks.json', app.tasks_data)
        task_id = new_id

@when(parsers.parse('I log "{hours}" hours of effort on my task'))
def log_effort(hours):
    global response
    response = client.post(f'/update_task/{task_id}', data={
        "effort_logged": hours,
        "notes_added": ""
    })

@then(parsers.parse('the logged effort should be "{hours}"'))
def check_logged_effort(hours):
    assert response.status_code == 302
    tasks = load_data('tasks.json')
    task = next((t for t in tasks if t['id'] == task_id), None)
    assert task is not None
    assert task['logged_effort'] == float(hours)