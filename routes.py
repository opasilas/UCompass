from __future__ import annotations
from datetime import timedelta, datetime,date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from app import save_data, load_data

main_bp = Blueprint('main', __name__)

class DashboardController:
    """Implements the logic defined in the DashboardController class diagram."""
    
    def __init__(self, tasks, resources):
        self.tasks = tasks
        self.resources = resources
        self.threshold = 5

    def calculate_weekly_load(self, student_email: str) -> dict:
        """Sequence Diagram S7: logic for determining busy weeks."""
        weekly_counts = {}
        student_tasks = [t for t in self.tasks if t.get('student_email') == student_email]
        
        for task in student_tasks:
            # Skip tasks without a valid deadline string
            deadline_val = task.get('deadline')
            if not deadline_val or not isinstance(deadline_val, str):
                continue
            try:
                date_obj = datetime.strptime(deadline_val, '%Y-%m-%d')
            except (ValueError, TypeError):
                # ignore malformed or non-string deadline values
                continue
            # Use (year, week) tuple as key to avoid collisions across years
            iso = date_obj.isocalendar()
            key = (iso[0], iso[1])
            weekly_counts[key] = weekly_counts.get(key, 0) + 1
        return weekly_counts

    def get_priority_resources(self, is_busy_week: bool):
        """Sequence Diagram S8: Fetches 'EC' support if busy, or generic if not."""
        if is_busy_week:
            # Filter for Wellbeing/Emergency categories
            return [r for r in self.resources if r.get('category') == 'Wellbeing']
        return self.resources

@main_bp.route('/')
def index():
    if 'user_email' in session:
        user_role = session.get('user_role')
        if user_role == 'student':
            return redirect(url_for('main.student_dashboard'))
        elif user_role == 'teacher':
            return redirect(url_for('main.teacher_dashboard'))
        elif user_role == 'wellbeing_officer':
            return redirect(url_for('main.wellbeing_dashboard')) # New dashboard for wellbeing
    return render_template('login.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        users_data = current_app.users_data
        # Synthetic authentication
        user_found = False
        for user in users_data:
            if user['email'] == email and user['password'] == password: # In real app, hash passwords!
                session['user_email'] = user['email']
                session['user_role'] = user['role']
                user_found = True
                flash(f"Welcome, {user['name']}!", 'success')
                if user['role'] == 'student':
                    return redirect(url_for('main.student_dashboard'))
                elif user['role'] == 'teacher':
                    return redirect(url_for('main.teacher_dashboard'))
                elif user['role'] == 'wellbeing_officer':
                    return redirect(url_for('main.wellbeing_dashboard'))
        
        if not user_found:
            flash('Invalid email or password.', 'danger')
            return render_template('login.html', email=email)
    
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    session.pop('user_email', None)
    session.pop('user_role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@main_bp.route('/student_dashboard')
def student_dashboard():
    if 'user_role' not in session or session['user_role'] != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))

    controller = DashboardController(current_app.tasks_data, current_app.resources_data)
    email = session['user_email']

    # Weekly load using controller (keys from controller may be week identifiers)
    weekly_load = controller.calculate_weekly_load(email)

    # Use controller.threshold and >= as requested
    is_busy_week = any(count >= controller.threshold for count in weekly_load.values())

    # Toggle for fetching priority resources
    toggle_on = request.args.get('busy_toggle') == 'on'
    display_resources = controller.get_priority_resources(is_busy_week and toggle_on)

    # Student tasks for calendar and lists
    student_tasks = [t for t in current_app.tasks_data if t.get('student_email') == email]

    # Busiest-week alert (use >= controller.threshold)
    busiest_week_alert = False
    if request.args.get('show_busiest_week_alert') == 'true':
        busiest_week_alert = any(count >= controller.threshold for count in weekly_load.values())

    # Calendar View Data Generation
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())
    calendar_weeks = []
    for i in range(-2, 3):
        week_start = current_week_start + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)

        # Determine week identifier and use controller's weekly load (preserve existing logic)
        iso = week_start.isocalendar()
        week_key = (iso[0], iso[1])
        week_count = weekly_load.get(week_key, 0)

        # Build per-day data for display only (days show tasks but busy state stays at week level)
        days = []
        for d in range(7):
            day_date = week_start + timedelta(days=d)
            tasks_on_day = [
                task for task in student_tasks
                if task.get('deadline') and datetime.strptime(task['deadline'], '%Y-%m-%d').date() == day_date
            ]
            days.append({
                'date': day_date.isoformat(),
                'has_tasks': len(tasks_on_day) > 0,
                'tasks': tasks_on_day,
                'deadlines_count': len(tasks_on_day)
            })

        # Keep busy logic at week level using controller.threshold
        is_week_busy = week_count >= controller.threshold

        week_info = {
            'start_date': week_start.isoformat(),
            'end_date': week_end.isoformat(),
            'is_busy': is_week_busy,
            'deadlines_count': sum(day['deadlines_count'] for day in days),
            'days': days
        }
        calendar_weeks.append(week_info)

    # Accept optional month/year query parameters for navigation
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    today = datetime.now().date()
    if not month or not year:
        month = today.month
        year = today.year
    first_of_month = date(year, month, 1)

    # Find the first Sunday on or before the first of month
    start_offset = (first_of_month.weekday() + 1) % 7  # weekday(): Mon=0..Sun=6 -> convert to Sun=0..Sat=6
    grid_start = first_of_month - timedelta(days=start_offset)

    # Last day of month
    if first_of_month.month == 12:
        next_month_first = first_of_month.replace(year=first_of_month.year + 1, month=1, day=1)
    else:
        next_month_first = first_of_month.replace(month=first_of_month.month + 1, day=1)
    last_of_month = next_month_first - timedelta(days=1)

    # Build weeks until we've covered the month
    calendar_month = {
        'month': first_of_month.strftime('%B'),
        'year': first_of_month.year,
        'weeks': []
    }

    cursor = grid_start
    while cursor <= last_of_month or len(calendar_month['weeks']) < 6:
        week_days = []
        for d in range(7):
            day_date = cursor + timedelta(days=d)
            tasks_on_day = [
                task for task in student_tasks
                if task.get('deadline') and datetime.strptime(task['deadline'], '%Y-%m-%d').date() == day_date
            ]
            # ISO week tuple for week-level busy check
            iso = day_date.isocalendar()
            iso_week_key = (iso[0], iso[1])
            week_days.append({
                'date': day_date,
                'in_month': day_date.month == first_of_month.month,
                'tasks': tasks_on_day,
                'deadlines_count': len(tasks_on_day),
                'iso_week_key': iso_week_key
            })

        # Determine canonical ISO week for this row (use the middle day) so the row maps
        # to a single ISO week and doesn't inherit the same ISO-week from adjacent rows.
        mid_day = cursor + timedelta(days=3)
        mid_iso = mid_day.isocalendar()
        mid_week_key = (mid_iso[0], mid_iso[1])
        week_busy = weekly_load.get(mid_week_key, 0) >= controller.threshold

        calendar_month['weeks'].append({
            'days': week_days,
            'is_busy': week_busy
        })

        cursor = cursor + timedelta(days=7)
        # Stop if we've added enough rows and the last row is completely after the month
        if cursor > last_of_month and len(calendar_month['weeks']) >= 4:
            break

    # Compute previous and next months for navigation
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    return render_template('student_dashboard.html',
                           student_email=session['user_email'],
                           student_tasks=student_tasks,
                           resources=display_resources,
                           is_busy=is_busy_week,
                           toggle_on=toggle_on,
                           busiest_week_alert=busiest_week_alert,
                           show_busiest_week_alert_toggle=request.args.get('show_busiest_week_alert'),
                           calendar_weeks=calendar_weeks,
                           calendar_month=calendar_month,
                           show_calendar_busy_highlight=request.args.get('show_busiest_week_alert') == 'true',
                           current_month=month,
                           current_year=year,
                           prev_month=prev_month,
                           prev_year=prev_year,
                           next_month=next_month,
                           next_year=next_year
                           )

@main_bp.route('/teacher_dashboard')
def teacher_dashboard():
    if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    # Placeholder for teacher-specific data
    return render_template('teacher_dashboard.html', 
                            user_role=session['user_role'],
                            all_resources=current_app.resources_data, # For Feature Two
                            all_tasks=current_app.tasks_data) # For Feature Two (adding deadlines)

@main_bp.route('/wellbeing_dashboard')
def wellbeing_dashboard():
    if 'user_role' not in session or session['user_role'] != 'wellbeing_officer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))
    
    # This dashboard will initially be similar to teacher_dashboard for resource management
    return render_template('wellbeing_dashboard.html', 
                            all_resources=current_app.resources_data,
                            all_tasks=current_app.tasks_data) # For Feature Two (adding deadlines)

# Placeholder for Feature Two: Add/Edit Resources
@main_bp.route('/manage_resources', methods=['GET', 'POST'])
def manage_resources():
    if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        resource_id = request.form.get('resource_id')
        title = request.form['title']
        category = request.form['category']
        content = request.form['content']
        
        if resource_id: # Update existing
            for i, res in enumerate(current_app.resources_data):
                if str(res['id']) == resource_id:
                    current_app.resources_data[i]['title'] = title
                    current_app.resources_data[i]['category'] = category
                    current_app.resources_data[i]['content'] = content
                    break
            flash('Resource updated successfully!', 'success')
        else: # Add new
            new_id = max([r['id'] for r in current_app.resources_data]) + 1 if current_app.resources_data else 1
            new_resource = {
                'id': new_id,
                'title': title,
                'category': category,
                'content': content,
                'created_by': session['user_email'] # Track who created it
            }
            current_app.resources_data.append(new_resource)
            flash('Resource added successfully!', 'success')
        save_data('resources.json', current_app.resources_data)
        return redirect(url_for('main.manage_resources'))
        
    return render_template('manage_resources.html', all_resources=current_app.resources_data)

# Placeholder for Feature Two: Add Deadlines to Tasks
@main_bp.route('/add_deadline/<int:task_id>', methods=['GET', 'POST'])
def add_deadline(task_id):
    if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))
    
    task = next((t for t in current_app.tasks_data if t['id'] == task_id), None)
    if not task:
        flash('Task not found.', 'danger')
        return redirect(url_for('main.teacher_dashboard'))
    
    if request.method == 'POST':
        deadline_str = request.form['deadline'] # YYYY-MM-DD
        task['deadline'] = deadline_str
        save_data('tasks.json', current_app.tasks_data)
        flash(f"Deadline added for task '{task['title']}'", 'success')
        return redirect(url_for('main.teacher_dashboard'))
    
    return render_template('add_deadline.html', task=task)


# Student: create a new task (can be pre-filled with ?deadline=YYYY-MM-DD)
@main_bp.route('/create_task', methods=['GET', 'POST'])
def create_task():
    if 'user_role' not in session or session['user_role'] != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))

    prefill_deadline = request.args.get('deadline')
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        deadline_str = request.form.get('deadline') or None

        if not title:
            flash('Title is required.', 'danger')
            return render_template('create_task.html', deadline=deadline_str, title=title, description=description)

        new_id = max([t['id'] for t in current_app.tasks_data]) + 1 if current_app.tasks_data else 1
        new_task = {
            'id': new_id,
            'title': title,
            'description': description,
            'deadline': deadline_str,
            'student_email': session['user_email'],
            'logged_effort': 0.0,
            'notes': ''
        }
        current_app.tasks_data.append(new_task)
        save_data('tasks.json', current_app.tasks_data)
        flash('Task created successfully!', 'success')
        return redirect(url_for('main.student_dashboard'))

    return render_template('create_task.html', deadline=prefill_deadline)

# Placeholder for Feature Three: Student Log Effort/Notes
@main_bp.route('/update_task/<int:task_id>', methods=['GET', 'POST'])
def update_task(task_id):
    if 'user_role' not in session or session['user_role'] != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))
    
    task = next((t for t in current_app.tasks_data if t['id'] == task_id and t['student_email'] == session['user_email']), None)
    if not task:
        flash('Task not found or unauthorized.', 'danger')
        return redirect(url_for('main.student_dashboard'))
    
    if request.method == 'POST':
        effort_logged = request.form.get('effort_logged', type=float)
        notes_added = request.form.get('notes_added', '')

        if effort_logged is not None:
            task['logged_effort'] = task.get('logged_effort', 0.0) + effort_logged
        if notes_added:
            task['notes'] = task.get('notes', '') + f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes_added}"
        
        save_data('tasks.json', current_app.tasks_data)
        flash(f"Task '{task['title']}' updated successfully!", 'success')
        return redirect(url_for('main.student_dashboard'))
        
    return render_template('update_task.html', task=task)

@main_bp.route('/delete_resource/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))
    
    # global current_app.resources_data
    resources_data = current_app.resources_data
    initial_len = len(resources_data)
    resources_data = [res for res in resources_data if res['id'] != resource_id]
    
    if len(resources_data) < initial_len:
        save_data('resources.json', resources_data)
        flash('Resource deleted successfully!', 'success')
    else:
        flash('Resource not found.', 'danger')
    
    return redirect(url_for('main.manage_resources'))
