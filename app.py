from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import json
from datetime import datetime, timedelta

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'a_very_secret_key_for_flask_sessions_change_this_in_prod'
    app.config['STATIC_FOLDER'] = 'static' # Ensure static folder is recognized

    # Placeholder for user data (loaded from flat file later)
    users_data = {}
    resources_data = []
    tasks_data = []

    # --- Utility Functions (will be expanded for flat file operations) ---
    def load_data(filename):
        filepath = os.path.join(os.getcwd(), 'data', filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return [] # Return empty list if file not found

    def save_data(filename, data):
        filepath = os.path.join(os.getcwd(), 'data', filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    @app.before_request
    def load_synthetic_data():
        nonlocal users_data, resources_data, tasks_data
        # For simplicity, we'll re-load on each request if data is empty.
        # In a real app, this would be loaded once or managed more robustly.
        if not users_data:
            users_data = load_data('users.json')
        if not resources_data:
            resources_data = load_data('resources.json')
        if not tasks_data:
            tasks_data = load_data('tasks.json')


    # --- Routes ---
    @app.route('/')
    def index():
        if 'user_email' in session:
            user_role = session.get('user_role')
            if user_role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user_role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif user_role == 'wellbeing_officer':
                return redirect(url_for('wellbeing_dashboard')) # New dashboard for wellbeing
        return render_template('login.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']

            # Synthetic authentication
            user_found = False
            for user in users_data:
                if user['email'] == email and user['password'] == password: # In real app, hash passwords!
                    session['user_email'] = user['email']
                    session['user_role'] = user['role']
                    user_found = True
                    flash(f"Welcome, {user['name']}!", 'success')
                    if user['role'] == 'student':
                        return redirect(url_for('student_dashboard'))
                    elif user['role'] == 'teacher':
                        return redirect(url_for('teacher_dashboard'))
                    elif user['role'] == 'wellbeing_officer':
                        return redirect(url_for('wellbeing_dashboard'))
            
            if not user_found:
                flash('Invalid email or password.', 'danger')
                return render_template('login.html', email=email)
        
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.pop('user_email', None)
        session.pop('user_role', None)
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    @app.route('/student_dashboard')
    def student_dashboard():
        if 'user_role' not in session or session['user_role'] != 'student':
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('login'))
        
        # Placeholder for student-specific tasks and data
        student_tasks = [t for t in tasks_data if t['student_email'] == session['user_email']]
        
        # For Feature One (Busiest Week Toggle)
        # Assuming tasks have a 'deadline' field in YYYY-MM-DD format
        busiest_week_alert = False
        if request.args.get('show_busiest_week_alert') == 'true':
            # This is a very simplistic implementation, needs to be more robust
            # to handle different week starts and edge cases
            weekly_deadlines = {}
            for task in student_tasks:
                if 'deadline' in task:
                    deadline_date = datetime.strptime(task['deadline'], '%Y-%m-%d').date()
                    # Determine the start of the week for this deadline
                    # Assuming week starts on Monday
                    week_start = deadline_date - timedelta(days=deadline_date.weekday())
                    week_start_str = week_start.isoformat()
                    weekly_deadlines[week_start_str] = weekly_deadlines.get(week_start_str, 0) + 1
            
            for week_start_str, count in weekly_deadlines.items():
                if count > 5: # Example threshold for red alert (was 2)
                    busiest_week_alert = True
                    break

        
        # Calendar View Data Generation
        today = datetime.now().date()
        # Find the Monday of the current week
        current_week_start = today - timedelta(days=today.weekday())
        
        # Define the range for the calendar (e.g., 2 weeks before, current week, 2 weeks after)
        calendar_weeks = []
        for i in range(-2, 3): # -2, -1, 0, 1, 2 for 5 weeks total
            week_start = current_week_start + timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            
            deadlines_in_week = [
                task for task in student_tasks 
                if task.get('deadline') and 
                   week_start <= datetime.strptime(task['deadline'], '%Y-%m-%d').date() <= week_end
            ]
            
            is_busy_week = len(deadlines_in_week) > 5

            week_info = {
                'start_date': week_start.isoformat(),
                'end_date': week_end.isoformat(),
                'is_busy': is_busy_week,
                'deadlines_count': len(deadlines_in_week) # For debugging/display
            }
            calendar_weeks.append(week_info)


        return render_template('student_dashboard.html', 
                               student_email=session['user_email'], 
                               student_tasks=student_tasks,
                               busiest_week_alert=busiest_week_alert,
                               show_busiest_week_alert_toggle=request.args.get('show_busiest_week_alert'),
                               calendar_weeks=calendar_weeks,
                               show_calendar_busy_highlight=request.args.get('show_busiest_week_alert') == 'true')

    @app.route('/teacher_dashboard')
    def teacher_dashboard():
        if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('login'))
        
        # Placeholder for teacher-specific data
        return render_template('teacher_dashboard.html', 
                               user_role=session['user_role'],
                               all_resources=resources_data, # For Feature Two
                               all_tasks=tasks_data) # For Feature Two (adding deadlines)

    @app.route('/wellbeing_dashboard')
    def wellbeing_dashboard():
        if 'user_role' not in session or session['user_role'] != 'wellbeing_officer':
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('login'))
        
        # This dashboard will initially be similar to teacher_dashboard for resource management
        return render_template('wellbeing_dashboard.html', 
                               all_resources=resources_data,
                               all_tasks=tasks_data) # For Feature Two (adding deadlines)

    # Placeholder for Feature Two: Add/Edit Resources
    @app.route('/manage_resources', methods=['GET', 'POST'])
    def manage_resources():
        if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            resource_id = request.form.get('resource_id')
            title = request.form['title']
            category = request.form['category']
            content = request.form['content']
            
            if resource_id: # Update existing
                for i, res in enumerate(resources_data):
                    if str(res['id']) == resource_id:
                        resources_data[i]['title'] = title
                        resources_data[i]['category'] = category
                        resources_data[i]['content'] = content
                        break
                flash('Resource updated successfully!', 'success')
            else: # Add new
                new_id = max([r['id'] for r in resources_data]) + 1 if resources_data else 1
                new_resource = {
                    'id': new_id,
                    'title': title,
                    'category': category,
                    'content': content,
                    'created_by': session['user_email'] # Track who created it
                }
                resources_data.append(new_resource)
                flash('Resource added successfully!', 'success')
            save_data('resources.json', resources_data)
            return redirect(url_for('manage_resources'))
            
        return render_template('manage_resources.html', all_resources=resources_data)
    
    # Placeholder for Feature Two: Add Deadlines to Tasks
    @app.route('/add_deadline/<int:task_id>', methods=['GET', 'POST'])
    def add_deadline(task_id):
        if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('login'))
        
        task = next((t for t in tasks_data if t['id'] == task_id), None)
        if not task:
            flash('Task not found.', 'danger')
            return redirect(url_for('teacher_dashboard'))
        
        if request.method == 'POST':
            deadline_str = request.form['deadline'] # YYYY-MM-DD
            task['deadline'] = deadline_str
            save_data('tasks.json', tasks_data)
            flash(f"Deadline added for task '{task['title']}'", 'success')
            return redirect(url_for('teacher_dashboard'))
        
        return render_template('add_deadline.html', task=task)

    # Placeholder for Feature Three: Student Log Effort/Notes
    @app.route('/update_task/<int:task_id>', methods=['GET', 'POST'])
    def update_task(task_id):
        if 'user_role' not in session or session['user_role'] != 'student':
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('login'))
        
        task = next((t for t in tasks_data if t['id'] == task_id and t['student_email'] == session['user_email']), None)
        if not task:
            flash('Task not found or unauthorized.', 'danger')
            return redirect(url_for('student_dashboard'))
        
        if request.method == 'POST':
            effort_logged = request.form.get('effort_logged', type=float)
            notes_added = request.form.get('notes_added', '')

            if effort_logged is not None:
                task['logged_effort'] = task.get('logged_effort', 0.0) + effort_logged
            if notes_added:
                task['notes'] = task.get('notes', '') + f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes_added}"
            
            save_data('tasks.json', tasks_data)
            flash(f"Task '{task['title']}' updated successfully!", 'success')
            return redirect(url_for('student_dashboard'))
            
        return render_template('update_task.html', task=task)

    @app.route('/delete_resource/<int:resource_id>', methods=['POST'])
    def delete_resource(resource_id):
        if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('login'))
        
        global resources_data
        initial_len = len(resources_data)
        resources_data = [res for res in resources_data if res['id'] != resource_id]
        
        if len(resources_data) < initial_len:
            save_data('resources.json', resources_data)
            flash('Resource deleted successfully!', 'success')
        else:
            flash('Resource not found.', 'danger')
        
        return redirect(url_for('manage_resources'))

    return app

app = create_app()

if __name__ == '__main__':
    # Ensure a 'data' directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # Initialize empty JSON files if they don't exist
    for filename in ['users.json', 'resources.json', 'tasks.json']:
        filepath = os.path.join('data', filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                json.dump([], f) # Start with an empty list

    app.run(debug=True, port=8000)
