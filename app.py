from flask import Flask
import os
import json
from datetime import datetime, timedelta


def load_data(filename):
    filepath = os.path.join(os.getcwd(), 'data', filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return [] 

def save_data(filename, data):
    filepath = os.path.join(os.getcwd(), 'data', filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'a_very_secret_key_for_flask_sessions_change_this_in_prod'
    app.config['STATIC_FOLDER'] = 'static'

    # Attached to app object so routes can see them via current_app
    app.users_data = []
    app.resources_data = []
    app.tasks_data = []
    app.teacher_deadlines_data = []

    from routes import main_bp
    app.register_blueprint(main_bp)

    @app.before_request
    def load_synthetic_data():
        # Now these call the top-level functions
        if not app.users_data:
            app.users_data = load_data('users.json')
        if not app.resources_data:
            app.resources_data = load_data('resources.json')
        if not app.tasks_data:
            app.tasks_data = load_data('tasks.json')
        if not getattr(app, 'teacher_deadlines_data', None):
            app.teacher_deadlines_data = load_data('teacher_deadlines.json')

    return app

if __name__ == '__main__':

    app = create_app()
    # Ensure a 'data' directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # Initialize empty JSON files if they don't exist
    for filename in ['users.json', 'resources.json', 'tasks.json', 'teacher_deadlines.json']:
        filepath = os.path.join('data', filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                json.dump([], f) # Start with an empty list

    # with app.app_context():
    #     print(app.url_map)
    app.run(debug=True, port=8000)
