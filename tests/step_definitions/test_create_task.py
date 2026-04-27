import os
os.chdir("/Users/saffronforde/PycharmProjects/Student help/UCompass")

from pathlib import Path
from pytest_bdd import scenarios, given, when, then, parsers
from app import create_app, load_data

scenarios(Path(__file__).parent.parent / "features" / "create_task.feature")

app = create_app()
app.config['TESTING'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
client = app.test_client()
response = None

@given("the app is initialised")
def initialise_app():
    with app.app_context():
        app.tasks_data = load_data('tasks.json')
        app.resources_data = load_data('resources.json')
        app.users_data = load_data('users.json')

@when(parsers.parse('I add a task called "{title}" with a "{deadline}"'))
def add_task(title, deadline):
    global response
    with app.test_client() as c:
        with c.session_transaction() as session:
            session['user_role'] = 'student'
            session['user_email'] = 'test@test.com'
        response = c.post('/create_task', data={
            "title": title,
            "deadline": deadline
        })

@then(parsers.parse('the task "{title}" with deadline "{deadline}" should be added'))
def task_should_be_added(title, deadline):
    tasks = load_data('tasks.json')
    print(tasks)
    assert any(t["title"] == title and t["deadline"] == deadline for t in tasks)



