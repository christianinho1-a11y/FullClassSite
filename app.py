from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "portal.db"

db = SQLAlchemy()
login_manager = LoginManager()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    grades = db.relationship("Grade", back_populates="student", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class ClassRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    color = db.Column(db.String(20), default="#4f46e5")

    enrollments = db.relationship("Enrollment", back_populates="classroom", cascade="all, delete-orphan")
    announcements = db.relationship("Announcement", back_populates="classroom", cascade="all, delete-orphan")
    assignments = db.relationship("Assignment", back_populates="classroom", cascade="all, delete-orphan")
    resources = db.relationship("Resource", back_populates="classroom", cascade="all, delete-orphan")


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), nullable=False)

    student = db.relationship("User", back_populates="enrollments")
    classroom = db.relationship("ClassRoom", back_populates="enrollments")

    __table_args__ = (db.UniqueConstraint("student_id", "class_id", name="uq_student_class"),)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    classroom = db.relationship("ClassRoom", back_populates="announcements")


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default="Active")
    resource_link = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    classroom = db.relationship("ClassRoom", back_populates="assignments")
    grades = db.relationship("Grade", back_populates="assignment", cascade="all, delete-orphan")


class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignment.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    max_score = db.Column(db.Float, nullable=False, default=100)
    feedback = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignment = db.relationship("Assignment", back_populates="grades")
    student = db.relationship("User", back_populates="grades")

    __table_args__ = (db.UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student"),)


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    classroom = db.relationship("ClassRoom", back_populates="resources")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-me-in-production"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow()}

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("teacher_dashboard" if current_user.role == "teacher" else "student_dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash("Welcome back!", "success")
                return redirect(url_for("teacher_dashboard" if user.role == "teacher" else "student_dashboard"))
            flash("Invalid username or password.", "danger")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/student")
    @login_required
    @role_required("student")
    def student_dashboard():
        enrolled_classes = [en.classroom for en in current_user.enrollments]
        class_ids = [c.id for c in enrolled_classes]
        announcements = (
            Announcement.query.filter(Announcement.class_id.in_(class_ids))
            .order_by(Announcement.created_at.desc())
            .limit(6)
            .all()
            if class_ids
            else []
        )
        upcoming = (
            Assignment.query.filter(Assignment.class_id.in_(class_ids), Assignment.due_date >= date.today())
            .order_by(Assignment.due_date.asc())
            .limit(8)
            .all()
            if class_ids
            else []
        )
        grade_summary = student_average(current_user)
        return render_template(
            "student_dashboard.html",
            classes=enrolled_classes,
            announcements=announcements,
            upcoming=upcoming,
            grade_summary=grade_summary,
        )

    @app.route("/teacher")
    @login_required
    @role_required("teacher")
    def teacher_dashboard():
        classes = ClassRoom.query.order_by(ClassRoom.name).all()
        activity = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
        pending = Assignment.query.filter(Assignment.due_date >= date.today()).order_by(Assignment.due_date.asc()).limit(8).all()
        roster_counts = {c.id: len(c.enrollments) for c in classes}
        return render_template(
            "teacher_dashboard.html",
            classes=classes,
            activity=activity,
            pending=pending,
            roster_counts=roster_counts,
        )

    @app.route("/class/<slug>")
    @login_required
    def class_portal(slug: str):
        classroom = ClassRoom.query.filter_by(slug=slug).first_or_404()
        if current_user.role == "student" and not is_enrolled(current_user.id, classroom.id):
            flash("You are not enrolled in this class.", "danger")
            return redirect(url_for("student_dashboard"))

        announcements = Announcement.query.filter_by(class_id=classroom.id).order_by(Announcement.created_at.desc()).all()
        assignments = Assignment.query.filter_by(class_id=classroom.id).order_by(Assignment.due_date.asc()).all()
        resources = Resource.query.filter_by(class_id=classroom.id).order_by(Resource.created_at.desc()).all()

        grade_rows = []
        if current_user.role == "student":
            for assignment in assignments:
                grade = Grade.query.filter_by(assignment_id=assignment.id, student_id=current_user.id).first()
                grade_rows.append((assignment, grade))
        else:
            for assignment in assignments:
                grade_rows.append((assignment, Grade.query.filter_by(assignment_id=assignment.id).all()))

        return render_template(
            "class_portal.html",
            classroom=classroom,
            announcements=announcements,
            assignments=assignments,
            resources=resources,
            grade_rows=grade_rows,
        )

    @app.route("/class/<slug>/announcement", methods=["POST"])
    @login_required
    @role_required("teacher")
    def add_announcement(slug: str):
        classroom = ClassRoom.query.filter_by(slug=slug).first_or_404()
        ann = Announcement(
            class_id=classroom.id,
            teacher_id=current_user.id,
            title=request.form.get("title", "Announcement").strip()[:150],
            message=request.form.get("message", "").strip(),
        )
        db.session.add(ann)
        db.session.commit()
        flash("Announcement posted.", "success")
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/assignment", methods=["POST"])
    @login_required
    @role_required("teacher")
    def add_assignment(slug: str):
        classroom = ClassRoom.query.filter_by(slug=slug).first_or_404()
        due = request.form.get("due_date", "")
        due_date = datetime.strptime(due, "%Y-%m-%d").date() if due else date.today() + timedelta(days=7)
        assignment = Assignment(
            class_id=classroom.id,
            title=request.form.get("title", "New Assignment").strip()[:150],
            description=request.form.get("description", "").strip(),
            due_date=due_date,
            status=request.form.get("status", "Active"),
            resource_link=request.form.get("resource_link", "").strip() or None,
        )
        db.session.add(assignment)
        db.session.commit()
        flash("Assignment created.", "success")
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/resource", methods=["POST"])
    @login_required
    @role_required("teacher")
    def add_resource(slug: str):
        classroom = ClassRoom.query.filter_by(slug=slug).first_or_404()
        resource = Resource(
            class_id=classroom.id,
            title=request.form.get("title", "").strip()[:150],
            link=request.form.get("link", "").strip(),
        )
        db.session.add(resource)
        db.session.commit()
        flash("Resource uploaded.", "success")
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/grade", methods=["POST"])
    @login_required
    @role_required("teacher")
    def set_grade(slug: str):
        assignment_id = int(request.form.get("assignment_id"))
        student_id = int(request.form.get("student_id"))
        score = float(request.form.get("score", 0))
        max_score = float(request.form.get("max_score", 100))
        feedback = request.form.get("feedback", "")

        grade = Grade.query.filter_by(assignment_id=assignment_id, student_id=student_id).first()
        if grade:
            grade.score = score
            grade.max_score = max_score
            grade.feedback = feedback
        else:
            db.session.add(
                Grade(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    score=score,
                    max_score=max_score,
                    feedback=feedback,
                )
            )
        db.session.commit()
        flash("Grade saved.", "success")
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/admin/classes", methods=["GET", "POST"])
    @login_required
    @role_required("teacher")
    def manage_classes():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            slug = request.form.get("slug", "").strip().lower()
            if name and slug and not ClassRoom.query.filter((ClassRoom.name == name) | (ClassRoom.slug == slug)).first():
                db.session.add(
                    ClassRoom(
                        name=name,
                        slug=slug,
                        description=request.form.get("description", "Class portal"),
                        color=request.form.get("color", "#4f46e5"),
                    )
                )
                db.session.commit()
                flash("Class added.", "success")
        return render_template("manage_classes.html", classes=ClassRoom.query.order_by(ClassRoom.name).all())

    @app.route("/admin/students", methods=["GET", "POST"])
    @login_required
    @role_required("teacher")
    def manage_students():
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            if username and not User.query.filter_by(username=username).first():
                student = User(username=username, full_name=request.form.get("full_name", "Student"), role="student")
                student.set_password(request.form.get("password", "password123"))
                db.session.add(student)
                db.session.commit()
                flash("Student added.", "success")

        students = User.query.filter_by(role="student").order_by(User.full_name).all()
        classes = ClassRoom.query.order_by(ClassRoom.name).all()
        return render_template("manage_students.html", students=students, classes=classes)

    @app.route("/admin/students/<int:student_id>/enroll", methods=["POST"])
    @login_required
    @role_required("teacher")
    def enroll_student(student_id: int):
        student = User.query.get_or_404(student_id)
        class_id = int(request.form.get("class_id"))
        if not Enrollment.query.filter_by(student_id=student.id, class_id=class_id).first():
            db.session.add(Enrollment(student_id=student.id, class_id=class_id))
            db.session.commit()
            flash("Student enrolled.", "success")
        return redirect(url_for("manage_students"))

    return app


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


def role_required(role: str):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                flash("You do not have permission to access this area.", "danger")
                return redirect(url_for("index"))
            return func(*args, **kwargs)

        return wrapped

    return decorator


def is_enrolled(student_id: int, class_id: int) -> bool:
    return Enrollment.query.filter_by(student_id=student_id, class_id=class_id).first() is not None


def student_average(student: User) -> float:
    if not student.grades:
        return 0.0
    percentages = [(grade.score / grade.max_score) * 100 for grade in student.grades if grade.max_score > 0]
    return round(sum(percentages) / len(percentages), 2) if percentages else 0.0


def seed_data(app: Flask) -> None:
    with app.app_context():
        db.create_all()

        if User.query.count() > 0:
            return

        teacher = User(username="teacher", full_name="Ms. Carter", role="teacher")
        teacher.set_password("TeachSecure!2026")
        db.session.add(teacher)

        class_specs = [
            ("Intro to Networking and Cybersecurity", "networking-cyber", "#2563eb"),
            ("IT 1", "it-1", "#10b981"),
            ("IT 2", "it-2", "#f59e0b"),
            ("Data Science", "data-science", "#a855f7"),
            ("Intro to Computer Science", "intro-cs", "#ef4444"),
        ]
        classes = []
        for name, slug, color in class_specs:
            classroom = ClassRoom(name=name, slug=slug, color=color, description=f"Welcome to {name}.")
            classes.append(classroom)
            db.session.add(classroom)

        students = [
            ("alex.j", "Alex Johnson"),
            ("maria.p", "Maria Patel"),
            ("noah.r", "Noah Rivera"),
            ("sophia.k", "Sophia Kim"),
        ]
        student_objs = []
        for username, full_name in students:
            student = User(username=username, full_name=full_name, role="student")
            student.set_password("StudentPass!123")
            student_objs.append(student)
            db.session.add(student)

        db.session.commit()

        for idx, student in enumerate(student_objs):
            for classroom in classes:
                if (idx + classroom.id) % 2 == 0:
                    db.session.add(Enrollment(student_id=student.id, class_id=classroom.id))

        db.session.commit()

        for classroom in classes:
            db.session.add(
                Announcement(
                    class_id=classroom.id,
                    teacher_id=teacher.id,
                    title=f"Welcome to {classroom.name}",
                    message="Please review syllabus, class policies, and safety expectations.",
                )
            )
            assignment = Assignment(
                class_id=classroom.id,
                title="Week 1 Kickoff Assignment",
                description="Complete the introductory activity and submit your reflection.",
                due_date=date.today() + timedelta(days=5),
                status="Active",
                resource_link="https://example.com/week1-guide",
            )
            db.session.add(assignment)
            db.session.add(
                Resource(
                    class_id=classroom.id,
                    title="Course Syllabus",
                    link="https://example.com/syllabus",
                )
            )

        db.session.commit()

        assignments = Assignment.query.all()
        for assignment in assignments:
            enrolled = Enrollment.query.filter_by(class_id=assignment.class_id).all()
            for en in enrolled:
                db.session.add(
                    Grade(
                        assignment_id=assignment.id,
                        student_id=en.student_id,
                        score=85 + (en.student_id % 10),
                        max_score=100,
                        feedback="Strong start. Keep practicing.",
                    )
                )
        db.session.commit()


if __name__ == "__main__":
    app = create_app()
    seed_data(app)
    app.run(host="0.0.0.0", port=5000, debug=True)
