from __future__ import annotations
from datetime import timedelta, datetime,date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from markupsafe import Markup
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
        today_date = datetime.now().date()

        for task in student_tasks:
            # Skip tasks without a valid deadline string
            deadline_val = task.get('deadline')
            if not deadline_val or not isinstance(deadline_val, str):
                continue
            try:
                date_obj = datetime.strptime(deadline_val, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                # ignore malformed or non-string deadline values
                continue
            # Ignore deadlines that have already passed
            if date_obj < today_date:
                continue
            # Use week starting on Sunday as the canonical week key
            days_since_sunday = (date_obj.weekday() + 1) % 7  # Mon=0 -> 1, Sun=6 -> 0
            week_start = date_obj - timedelta(days=days_since_sunday)
            key = week_start
            weekly_counts[key] = weekly_counts.get(key, 0) + 1
        return weekly_counts

    def get_deadline_reminders(self, student_email: str) -> list:
        """Story S6: logic for reminders 7 days before deadline."""
        reminders = []
        today = datetime.now()
        # Filter tasks for this specific student
        student_tasks = [t for t in self.tasks if t.get('student_email') == student_email]

        for task in student_tasks:
            deadline_val = task.get('deadline')
            if deadline_val and isinstance(deadline_val, str):
                try:
                    deadline_date = datetime.strptime(deadline_val, '%Y-%m-%d')
                    # Calculate difference in days
                    delta = (deadline_date - today).days + 1  # +1 to be inclusive of today

                    # If deadline is within the next 7 days and hasn't passed
                    if 0 <= delta <= 7:
                        task_with_countdown = task.copy()
                        task_with_countdown['days_remaining'] = delta
                        reminders.append(task_with_countdown)
                except ValueError:
                    continue
        return reminders

    def get_priority_resources(self, is_busy_week: bool):
        """Sequence Diagram S8: Fetches 'EC' support if busy, or generic if not."""
        # If caller wants priority resources (e.g., during a busy week), return wellbeing resources that have been pinned
        if is_busy_week:
            return [r for r in self.resources if r.get('pinned') and (r.get('category') == 'Wellbeing')]
        return list(self.resources)

    def fetch_all_resources(self) -> list:
        """Return all known resources (shallow copy)."""
        return list(self.resources)

    def check_threshold(self, count: int) -> bool:
        """Return True if the provided count meets or exceeds the controller threshold."""
        try:
            return int(count) >= self.threshold
        except (TypeError, ValueError):
            return False

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
                # default the busiest-week toggle to off on login
                if user['role'] == 'student':
                    session['show_busiest_week_alert'] = 'false'
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

    email = session['user_email']

    # Map teacher-posted deadlines into task-like items for this student so they appear
    # on the calendar and in reminders without being editable by the student.
    teacher_tasks_mapped = []
    for d in getattr(current_app, 'teacher_deadlines_data', []) or []:
        mapped = {
            'id': f"td-{d.get('id')}",
            'title': d.get('title'),
            'description': d.get('module', ''),
            'deadline': d.get('deadline'),
            'student_email': email,  # attach to current student for view-only display
            'notes': 'teacher generated deadline',
            'teacher_generated': True
        }
        teacher_tasks_mapped.append(mapped)

    # Create a merged task list used by the controller so weekly-load and reminders include teacher deadlines
    merged_tasks_for_controller = list(current_app.tasks_data) + teacher_tasks_mapped
    controller = DashboardController(merged_tasks_for_controller, current_app.resources_data)

    # Get countdown reminders
    deadline_reminders = controller.get_deadline_reminders(email)

    # Weekly load using controller (keys are ISO week tuples: (year, week_number))
    weekly_load = controller.calculate_weekly_load(email)

    # Precompute set of ISO week keys that are considered 'busy' (>= controller.threshold)
    busy_week_keys = {k for k, v in weekly_load.items() if controller.check_threshold(v)}

    # Determine if there are any busy weeks
    is_busy_week = bool(busy_week_keys)

    # Determine current week-start (Sunday) key and whether it's busy
    today_for_current = datetime.now().date()
    days_since_sunday_now = (today_for_current.weekday() + 1) % 7
    current_week_key = today_for_current - timedelta(days=days_since_sunday_now)
    is_current_week_busy = current_week_key in busy_week_keys

    # Persist show_busiest_week_alert in session so it survives month navigation
    arg_values = request.args.getlist('show_busiest_week_alert')
    if arg_values:
        session['show_busiest_week_alert'] = 'true' if 'true' in arg_values else 'false'
    # Final value used to drive calendar highlighting
    show_busiest_in_session = session.get('show_busiest_week_alert', 'false') == 'true'

    # Toggle for fetching priority resources (legacy param). When enabled, use current-week busy status.
    toggle_on = request.args.get('busy_toggle') == 'on'
    # Use controller helpers for resource access rather than reading current_app directly
    display_resources = controller.get_priority_resources(is_current_week_busy and show_busiest_in_session)

    # Recommended resources to show when busy-week highlighting is enabled and a busy week exists
    if show_busiest_in_session and is_current_week_busy:
        recommended_resources = [r for r in controller.fetch_all_resources() if r.get('pinned') and r.get('category') == 'Wellbeing']
    else:
        recommended_resources = []

    # Flash a RED ALERT only when the user has enabled the toggle and a busy week exists
    if show_busiest_in_session and is_busy_week:
        flash(Markup(
            'RED ALERT! You have more than 5 deadlines in a single week. Consider applying for <a href="#resources" class="alert-link">Extenuating Circumstances (EC)</a>.'),
              'danger')

    # Student tasks for calendar and lists (sorted by deadline, earliest first; tasks without deadline last)
    def _parse_deadline_or_max(task):
        d = task.get('deadline')
        if d and isinstance(d, str):
            try:
                return datetime.strptime(d, '%Y-%m-%d').date()
            except ValueError:
                return date.max
        return date.max

    # Build student-visible tasks by merging actual student tasks with teacher-generated tasks.
    student_tasks = [t for t in merged_tasks_for_controller if t.get('student_email') == email]
    # Add an explicit `editable` flag for template logic (students cannot edit teacher-generated entries)
    for t in student_tasks:
        t['editable'] = not bool(t.get('teacher_generated'))
    student_tasks = sorted(student_tasks, key=_parse_deadline_or_max)

    # Resource category filter (All / Academic / Wellbeing) using controller-provided resources
    resource_category = request.args.get('resource_category', 'all')
    all_resources = controller.fetch_all_resources()
    if resource_category and resource_category.lower() != 'all':
        filtered_resources = [r for r in all_resources if (r.get('category') or '').lower() == resource_category.lower()]
    else:
        filtered_resources = list(all_resources)
    # Pinned resources should always be computed from the full dataset and not affected by category filters
    pinned_resources = [r for r in all_resources if r.get('pinned')]

    # Busiest-week alert (true when any week meets/exceeds threshold)
    busiest_week_alert = is_busy_week

    # Calendar View Data Generation
    today = datetime.now().date()
    # Week starts on Sunday for calendar display
    days_since_sunday = (today.weekday() + 1) % 7
    current_week_start = today - timedelta(days=days_since_sunday)
    calendar_weeks = []
    for i in range(-2, 3):
        week_start = current_week_start + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)

        # Determine week identifier and use controller's weekly load (preserve existing logic)
        week_key = week_start
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
                'date': day_date,
                'has_tasks': len(tasks_on_day) > 0,
                'tasks': tasks_on_day,
                'deadlines_count': len(tasks_on_day),
                'is_past': day_date < today
            })

        # Keep busy logic at week level using the precomputed busy_week_keys
        is_week_busy = week_key in busy_week_keys

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
            # Week-start (Sunday) key for this day
            days_since_sunday_for_day = (day_date.weekday() + 1) % 7
            iso_week_key = (day_date - timedelta(days=days_since_sunday_for_day))
            week_days.append({
                'date': day_date,
                'in_month': day_date.month == first_of_month.month,
                'tasks': tasks_on_day,
                'deadlines_count': len(tasks_on_day),
                'is_past': day_date < today,
                'iso_week_key': iso_week_key
            })

        # Determine canonical week-start (use the row's week_start cursor) so the row maps
        # to a single Sunday-start week and doesn't inherit the same week from adjacent rows.
        week_start_for_row = cursor
        week_busy = week_start_for_row in busy_week_keys

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

    # Resolve student name for greeting
    student_name = None
    for u in current_app.users_data:
        if u.get('email') == email:
            student_name = u.get('name')
            break

    return render_template('student_dashboard.html',
                           student_email=session['user_email'],
                           student_tasks=student_tasks,
                           resources=display_resources,
                           all_resources=filtered_resources,
                           pinned_resources=pinned_resources,
                           selected_resource_category=resource_category,
                           is_busy=is_busy_week,
                           toggle_on=toggle_on,
                           busiest_week_alert=busiest_week_alert,
                           show_busiest_week_alert_toggle=session.get('show_busiest_week_alert', 'false'),
                           calendar_weeks=calendar_weeks,
                           calendar_month=calendar_month,
                           show_calendar_busy_highlight=show_busiest_in_session,
                           student_name=student_name,
                           current_month=month,
                           current_year=year,
                           prev_month=prev_month,
                           prev_year=prev_year,
                           next_month=next_month,
                           next_year=next_year,
                           deadline_reminders=deadline_reminders,
                           recommended_resources=recommended_resources,
                           is_current_week_busy=is_current_week_busy,
                           busy_week_keys=busy_week_keys)


@main_bp.route('/day/<date>')
def day_view(date):
    # Show tasks for a given date (student view)
    if 'user_role' not in session or session['user_role'] != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date.', 'danger')
        return redirect(url_for('main.student_dashboard'))

    # Filter tasks for this student on the given date, including teacher-posted deadlines mapped for this student
    tasks_for_day = [t for t in current_app.tasks_data if t.get('student_email') == session['user_email'] and t.get('deadline') == date]
    # include teacher deadlines that match this date
    for d in getattr(current_app, 'teacher_deadlines_data', []) or []:
        if d.get('deadline') == date:
            tasks_for_day.append({
                'id': f"td-{d.get('id')}",
                'title': d.get('title'),
                'description': d.get('module', ''),
                'deadline': d.get('deadline'),
                'student_email': session['user_email'],
                'notes': 'teacher generated deadline',
                'teacher_generated': True,
                'editable': False
            })

    return render_template('day_view.html', date=date_obj, tasks=tasks_for_day)

@main_bp.route('/teacher_dashboard')
def teacher_dashboard():
    if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))
    
    # Teacher-specific resources (those created by this user)
    teacher_email = session.get('user_email')
    controller = DashboardController(current_app.tasks_data, current_app.resources_data)
    teacher_resources = [r for r in controller.fetch_all_resources() if r.get('created_by') == teacher_email]

    # All posted deadlines created by teachers (central list)
    posted_deadlines = getattr(current_app, 'teacher_deadlines_data', []) or []

    return render_template('teacher_dashboard.html', 
                            user_role=session['user_role'],
                            teacher_resources=teacher_resources,
                            posted_deadlines=posted_deadlines,
                            all_tasks=current_app.tasks_data)

@main_bp.route('/wellbeing_dashboard')
def wellbeing_dashboard():
    if 'user_role' not in session or session['user_role'] != 'wellbeing_officer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))
    
    # This dashboard will initially be similar to teacher_dashboard for resource management
    # Prepare weekly logged hours per student for the last 4 weeks (week starts Sunday)
    today = datetime.now().date()
    days_since_sunday = (today.weekday() + 1) % 7
    current_week_start = today - timedelta(days=days_since_sunday)
    week_starts = [current_week_start - timedelta(weeks=i) for i in range(3, -1, -1)]  # oldest -> newest

    # collect students
    students = [u for u in current_app.users_data if u.get('role') == 'student']

    # build map student_email -> {week_start.isoformat(): total_hours}
    weekly_hours_by_student = {}
    for s in students:
        email = s.get('email')
        weekly_hours_by_student[email] = {ws.isoformat(): 0.0 for ws in week_starts}

    for t in current_app.tasks_data:
        student_email = t.get('student_email')
        if not student_email:
            continue
        deadline_val = t.get('deadline')
        if not deadline_val:
            continue
        try:
            d = datetime.strptime(deadline_val, '%Y-%m-%d').date()
        except Exception:
            continue
        # determine week-start (Sunday) for this deadline
        d_days_since_sunday = (d.weekday() + 1) % 7
        ws = (d - timedelta(days=d_days_since_sunday))
        if ws in week_starts:
            weekly_hours_by_student.setdefault(student_email, {ws.isoformat(): 0.0 for ws in week_starts})
            weekly_hours_by_student[student_email][ws.isoformat()] = weekly_hours_by_student[student_email].get(ws.isoformat(), 0.0) + float(t.get('logged_effort', 0.0))

    # Use controller for resource access consistency
    controller = DashboardController(current_app.tasks_data, current_app.resources_data)
    return render_template('wellbeing_dashboard.html', 
                            all_resources=controller.fetch_all_resources(),
                            all_tasks=current_app.tasks_data,
                            week_starts=week_starts,
                            students=students,
                            weekly_hours_by_student=weekly_hours_by_student)


@main_bp.route('/resources')
def resources_page():
    if 'user_email' not in session:
        flash('Please log in to view resources.', 'danger')
        return redirect(url_for('main.login'))

    # Show pinned and all resources to logged-in users (use controller for read access)
    controller = DashboardController(current_app.tasks_data, current_app.resources_data)
    all_resources = controller.fetch_all_resources()
    pinned = [r for r in all_resources if r.get('pinned')]
    others = [r for r in all_resources if not r.get('pinned')]
    return render_template('resources.html', pinned_resources=pinned, all_resources=others)

# Placeholder for Feature Two: Add/Edit Resources
@main_bp.route('/manage_resources', methods=['GET', 'POST'])
def manage_resources():
    if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))
    
    resource_to_edit = None
    # If a GET parameter resource_id is passed, attempt to load the resource for editing
    if request.method == 'GET' and request.args.get('resource_id'):
        rid = request.args.get('resource_id')
        resource_to_edit = next((r for r in current_app.resources_data if str(r.get('id')) == str(rid)), None)

    if request.method == 'POST':
        resource_id = request.form.get('resource_id')
        title = request.form['title']
        category = request.form.get('category')
        content = request.form['content']
        pinned_flag = request.form.get('pinned') == 'on'
        
        if resource_id: # Update existing
            for i, res in enumerate(current_app.resources_data):
                if str(res['id']) == resource_id:
                    current_app.resources_data[i]['title'] = title
                    current_app.resources_data[i]['category'] = category
                    current_app.resources_data[i]['content'] = content
                    # update pinned state when provided; record who pinned/unpinned
                    current_app.resources_data[i]['pinned'] = pinned_flag
                    if pinned_flag:
                        current_app.resources_data[i]['pinned_by_role'] = session.get('user_role')
                        current_app.resources_data[i]['pinned_by'] = session.get('user_email')
                    else:
                        current_app.resources_data[i].pop('pinned_by_role', None)
                        current_app.resources_data[i].pop('pinned_by', None)
                    break
            flash('Resource updated successfully!', 'success')
        else: # Add new
            new_id = max([r['id'] for r in current_app.resources_data]) + 1 if current_app.resources_data else 1
            # Default category by creator role if not provided
            if not category:
                if session.get('user_role') == 'teacher':
                    category = 'Academic'
                elif session.get('user_role') == 'wellbeing_officer':
                    category = 'Wellbeing'
                else:
                    category = 'General'
            new_resource = {
                'id': new_id,
                'title': title,
                'category': category,
                'content': content,
                'created_by': session['user_email'], # Track who created it
                'pinned': pinned_flag,
                'pinned_by_role': session.get('user_role') if pinned_flag else None,
                'pinned_by': session.get('user_email') if pinned_flag else None
            }
            current_app.resources_data.append(new_resource)
            flash('Resource added successfully!', 'success')
        save_data('resources.json', current_app.resources_data)
        return redirect(url_for('main.manage_resources'))
        
    return render_template('manage_resources.html', all_resources=current_app.resources_data, resource=resource_to_edit)

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


@main_bp.route('/teacher_deadlines/create', methods=['POST'])
def create_teacher_deadline():
    if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))

    title = request.form.get('title', '').strip()
    module = request.form.get('module', '').strip()
    deadline_str = request.form.get('deadline')
    if not title or not deadline_str:
        flash('Title and deadline are required.', 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    new_id = max([d['id'] for d in current_app.teacher_deadlines_data]) + 1 if current_app.teacher_deadlines_data else 1
    new_deadline = {
        'id': new_id,
        'title': title,
        'module': module,
        'deadline': deadline_str,
        'created_by': session['user_email']
    }
    current_app.teacher_deadlines_data.append(new_deadline)
    save_data('teacher_deadlines.json', current_app.teacher_deadlines_data)
    flash('Deadline posted successfully!', 'success')
    return redirect(url_for('main.teacher_dashboard'))


@main_bp.route('/teacher_deadlines/delete/<int:deadline_id>', methods=['POST'])
def delete_teacher_deadline(deadline_id):
    if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))

    initial = len(current_app.teacher_deadlines_data)
    current_app.teacher_deadlines_data = [d for d in current_app.teacher_deadlines_data if d.get('id') != deadline_id]
    if len(current_app.teacher_deadlines_data) < initial:
        save_data('teacher_deadlines.json', current_app.teacher_deadlines_data)
        flash('Deadline deleted.', 'success')
    else:
        flash('Deadline not found.', 'danger')
    return redirect(url_for('main.teacher_dashboard'))


@main_bp.route('/teacher_deadlines/edit/<int:deadline_id>', methods=['GET', 'POST'])
def edit_teacher_deadline(deadline_id):
    if 'user_role' not in session or session['user_role'] not in ['teacher', 'wellbeing_officer']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))

    deadline = next((d for d in current_app.teacher_deadlines_data if d.get('id') == deadline_id), None)
    if not deadline:
        flash('Deadline not found.', 'danger')
        return redirect(url_for('main.teacher_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        module = request.form.get('module', '').strip()
        deadline_str = request.form.get('deadline')
        if not title or not deadline_str:
            flash('Title and deadline are required.', 'danger')
            return redirect(url_for('main.edit_teacher_deadline', deadline_id=deadline_id))

        deadline['title'] = title
        deadline['module'] = module
        deadline['deadline'] = deadline_str
        save_data('teacher_deadlines.json', current_app.teacher_deadlines_data)
        flash('Deadline updated.', 'success')
        return redirect(url_for('main.teacher_dashboard'))

    return render_template('edit_teacher_deadline.html', deadline=deadline)


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
        # Accept updates for all editable fields
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        deadline_str = request.form.get('deadline') or None
        effort_logged = request.form.get('effort_logged', type=float)
        notes_added = request.form.get('notes_added', '').strip()

        # Update fields if provided (allow clearing by sending empty string)
        if title:
            task['title'] = title
        if description or description == '':
            task['description'] = description
        # Validate deadline format (YYYY-MM-DD) or allow clearing
        if deadline_str:
            try:
                # raises ValueError if invalid
                datetime.strptime(deadline_str, '%Y-%m-%d')
                task['deadline'] = deadline_str
            except ValueError:
                flash('Invalid deadline format. Use YYYY-MM-DD.', 'danger')
                return render_template('update_task.html', task=task)
        else:
            # allow clearing deadline
            task['deadline'] = None

        if effort_logged is not None:
            task['logged_effort'] = task.get('logged_effort', 0.0) + effort_logged

        if notes_added:
            # Append new note under existing notes with timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            existing = task.get('notes', '')
            appended = f"[{timestamp}] {notes_added}"
            task['notes'] = (existing + '\n' if existing else '') + appended
        
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


@main_bp.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if 'user_role' not in session:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))

    # locate task
    task = next((t for t in current_app.tasks_data if t['id'] == task_id), None)
    if not task:
        flash('Task not found.', 'danger')
        return redirect(url_for('main.student_dashboard'))

    # permission: students can delete their own tasks; teachers and wellbeing_officer can delete any
    user_role = session.get('user_role')
    if user_role == 'student' and task.get('student_email') != session.get('user_email'):
        flash('Unauthorized to delete this task.', 'danger')
        return redirect(url_for('main.student_dashboard'))

    # remove task in-place
    current_app.tasks_data[:] = [t for t in current_app.tasks_data if t['id'] != task_id]
    save_data('tasks.json', current_app.tasks_data)
    flash('Task deleted successfully.', 'danger')

    # support returning to a 'next' URL
    next_url = request.form.get('next') or url_for('main.student_dashboard')
    return redirect(next_url)


@main_bp.route('/pin_resource/<int:resource_id>', methods=['POST'])
def pin_resource(resource_id):
    if 'user_role' not in session:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.login'))

    # Toggle pinned flag on resource
    for res in current_app.resources_data:
        if res.get('id') == resource_id:
            new_state = not res.get('pinned', False)
            res['pinned'] = new_state
            if new_state:
                # record who pinned it
                res['pinned_by_role'] = session.get('user_role')
                res['pinned_by'] = session.get('user_email')
            else:
                res.pop('pinned_by_role', None)
                res.pop('pinned_by', None)
            save_data('resources.json', current_app.resources_data)
            break

    # Return back to 'next' if provided, else referrer, else student dashboard
    next_url = request.form.get('next') or request.referrer or url_for('main.student_dashboard')
    return redirect(next_url)
