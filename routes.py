from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/student_dashboard')
def student_dashboard():
    return render_template('student_dashboard.html')

@main_bp.route('/teacher_dashboard')
def teacher_dashboard():
    return render_template('teacher_dashboard.html')
