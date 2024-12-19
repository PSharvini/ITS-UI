from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from owlready2 import get_ontology, onto_path

# Flask app setup
app = Flask(__name__)
app.secret_key = 'aX8$hjF*809'

# Load the ontology
ontology_path = "ontology/ontology.owx"
onto = get_ontology(ontology_path).load()

# Ontology classes
Student = onto.Student
Teacher = onto.Teacher
Lesson = onto.LearningResource
Problem = onto.Problem
Solution = onto.Solution

# In-memory session to store logged-in users
logged_in_user = {}

def login_required(f):
    """Decorator to require login for specific routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('name'):
            flash("You need to be logged in to access this page.", "warning")
            return redirect(url_for('sign_in'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    """Homepage."""
    return render_template("index.html")

# --------------------------
# Sign-Up Functionality
# --------------------------
@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    """Sign up for students and teachers."""
    if session.get('name'):
        flash("You are already logged in.", "info")
        if session.get('user_type') == 'student':
            return redirect(url_for('student_dashboard', name=session.get('name')))
        elif session.get('user_type') == 'teacher':
            return redirect(url_for('teacher_dashboard'))
            
    if request.method == "POST":
        user_type = request.form["user_type"]
        name = request.form["name"]
        password = request.form["password"]

        # Check if the user already exists in the ontology
        existing_user = (
            next((user for user in onto.Student.instances() if user.hasName == name), None)
            if user_type == "student"
            else next((user for user in onto.Teacher.instances() if user.hasName == name), None)
        )
        if existing_user:
            flash(f"{user_type.capitalize()} with this name already exists.", "danger")
            return redirect(url_for("sign_up"))

        # Add the user to the ontology
        if user_type == "student":
            new_user = Student(name)
        else:  # Teacher
            new_user = Teacher(name)

        new_user.hasName = name
        new_user.hasPassword = password
        onto.save(file=ontology_path)  # Save to ontology

        flash(f"{user_type.capitalize()} account created successfully!", "success")
        return redirect(url_for("sign_in"))

    return render_template("sign_up.html")


# --------------------------
# Sign-In Functionality
# --------------------------
@app.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    """Sign in for students and teachers."""
    if session.get('name'):
        flash("You are already logged in.", "info")
        if session.get('user_type') == 'student':
            return redirect(url_for('student_dashboard', name=session.get('name')))
        elif session.get('user_type') == 'teacher':
            return redirect(url_for('teacher_dashboard'))
    
    if request.method == "POST":
        user_type = request.form["user_type"]
        name = request.form["name"]
        password = request.form["password"]

        # Authenticate the user
        user = (
            next((user for user in onto.Student.instances() if user.hasName == name and user.hasPassword == password), None)
            if user_type == "student"
            else next((user for user in onto.Teacher.instances() if user.hasName == name and user.hasPassword == password), None)
        )
        if not user:
            flash("Invalid credentials. Please try again.", "danger")
            return redirect(url_for("sign_in"))

        # Log the user in
        session["user_type"] = user_type
        session["name"] = name
        flash(f"Welcome, {name}!", "success")
        if user_type == "student":
            return redirect(url_for("student_dashboard", name=name))
        else:
            return redirect(url_for("teacher_dashboard"))

    return render_template("sign_in.html")


# --------------------------
# Student Dashboard
# --------------------------
# @app.route("/student_dashboard/<name>")
# @login_required
# def student_dashboard(name):
#     """Student dashboard."""
#     student = next((s for s in onto.Student.instances() if s.hasName == name), None)
#     if not student:
#         flash("Student not found!", "danger")
#         return redirect(url_for("index"))

#     lessons = list(onto.LearningResource.instances())
#     problems = list(onto.Problem.instances())
#     return render_template("student_dashboard.html", student=student, lessons=lessons, problems=problems)

@app.route("/student_dashboard/<name>")
@login_required
def student_dashboard(name):
    """Student dashboard."""
    # Retrieve the student
    student = next((s for s in onto.Student.instances() if name in s.hasName), None)
    if not student:
        flash("Student not found!", "danger")
        return redirect(url_for("index"))

    # Retrieve all lessons
    all_lessons = list(onto.Lesson.instances())
    problems = list(onto.Problem.instances())

    # Find the highest completed complexity level
    completed_lessons = student.hasCompletedLesson if hasattr(student, 'hasCompletedLesson') else []
    completed_levels = {lesson.hasComplexity[0] for lesson in completed_lessons if lesson.hasComplexity}
    complexity_order = ["Beginner", "Intermediate", "Advanced"]

    # Determine the next complexity level to unlock
    for level in complexity_order:
        if level not in completed_levels:
            next_level = level
            break

    # Filter lessons for the next complexity level
    available_lessons = [lesson for lesson in all_lessons if lesson.hasComplexity and lesson.hasComplexity[0] == next_level]

    # Pass lessons and progress to the template
    return render_template(
        "student_dashboard.html",
        student=student,
        available_lessons=available_lessons,
        completed_lessons=completed_lessons,
        next_level=next_level,
        problems=problems
    )

@app.route("/take_lesson/<name>/<lesson_name>")
@login_required
def take_lesson(name, lesson_name):
    """Simulate a student taking a lesson."""
    # Retrieve the student from the ontology
    student = next((s for s in onto.Student.instances() if name in s.hasName), None)
    if not student:
        flash("Student not found!", "danger")
        return redirect(url_for("index"))

    # Retrieve the lesson from the ontology
    lesson = next((l for l in onto.LearningResource.instances() if l.name == lesson_name), None)
    if not lesson:
        flash("Lesson not found!", "danger")
        return redirect(url_for("student_dashboard", name=name))

    # Check if the lesson has already been completed
    if lesson in student.hasCompletedLesson:
        flash(f"You have already completed the lesson '{lesson_name}'.", "warning")
        return redirect(url_for("student_dashboard", name=name))

    # Add the lesson to the student's completed lessons
    student.hasCompletedLesson.append(lesson)

    # Increment progress (or implement your own logic)
    if hasattr(student, 'hasProgress'):
        student.hasProgress[0] += 10.0  # Increment progress by 10%
    else:
        student.hasProgress = [10.0]  # Initialize progress if not set

    # Save updates to the ontology
    onto.save(file=ontology_path)

    flash(f"Lesson '{lesson_name}' completed! Progress updated.", "success")
    return redirect(url_for("student_dashboard", name=name))

@app.route("/submit_solution/<name>/<problem_name>", methods=["POST"])
@login_required
def submit_solution(name, problem_name):
    """Submit a solution for a problem."""
    solution_text = request.form["solution"]
    student = next((s for s in onto.Student.instances() if s.hasName == name), None)
    problem = next((p for p in onto.Problem.instances() if p.name == problem_name), None)

    if not student or not problem:
        flash("Invalid submission.", "danger")
        return redirect(url_for("student_dashboard", name=name))

    # Store the solution in the ontology
    solution_instance = onto.Solution(f"{name}_{problem_name}_Solution")
    solution_instance.isSolutionFor = [problem]
    solution_instance.hasDetailedExplanation = solution_text
    solution_instance.createdBy = [student]
    onto.save(file=ontology_path)

    flash("Solution submitted successfully!", "success")
    return redirect(url_for("student_dashboard", name=name))


# --------------------------
# Teacher Dashboard
# --------------------------
@app.route("/teacher_dashboard")
@login_required
def teacher_dashboard():
    """Teacher dashboard."""
    teachers = list(onto.Teacher.instances())
    students = list(onto.Student.instances())
    problems = list(onto.Problem.instances())

    # Separate Learning Resources into Examples and Lessons
    all_resources = list(onto.LearningResource.instances())

    # examples = [res for res in all_resources if getattr(res, 'hasType', None) == 'Example']
    # lessons = [res for res in all_resources if getattr(res, 'hasType', None) == 'Lesson']

    return render_template(
        "teacher_dashboard.html",
        teachers=teachers,
        students=students,
        problems=problems,
        resources=all_resources,
    )

    return render_template("teacher_dashboard.html", teachers=teachers, students=students, problems=problems)


@app.route("/view_student_solutions/<student_name>")
@login_required
def view_student_solutions(student_name):
    """View a student's solutions."""
    student = next((s for s in onto.Student.instances() if s.hasName == student_name), None)
    if not student:
        flash("Student not found!", "danger")
        return redirect(url_for("teacher_dashboard"))

    solutions = [
        sol
        for sol in onto.Solution.instances()
        if student in sol.createdBy
    ]
    return render_template("student_solutions.html", student=student, solutions=solutions)

@app.route("/logout")
def logout():
    """Logout the current user."""
    session.clear()  # Clear all session data
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)