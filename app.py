from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
import random

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
from sqlalchemy import or_
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
    student_code = db.Column(db.String(20), unique=True, nullable=True)
    status = db.Column(db.String(30), default="active")
    avatar = db.Column(db.String(5), nullable=True)
    notes = db.Column(db.Text, default="")
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
    teacher_info = db.Column(db.String(150), default="Ms. Carter")
    archived = db.Column(db.Boolean, default=False)

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
    pinned = db.Column(db.Boolean, default=False)
    scheduled_for = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    classroom = db.relationship("ClassRoom", back_populates="announcements")


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, default="")
    assigned_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    points_possible = db.Column(db.Float, default=100)
    category = db.Column(db.String(40), default="classwork")
    status = db.Column(db.String(30), default="published")
    submission_type = db.Column(db.String(50), default="LMS upload")
    late_allowed = db.Column(db.Boolean, default=True)
    pinned = db.Column(db.Boolean, default=False)
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
    missing = db.Column(db.Boolean, default=False)
    late = db.Column(db.Boolean, default=False)
    excused = db.Column(db.Boolean, default=False)
    override = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignment = db.relationship("Assignment", back_populates="grades")
    student = db.relationship("User", back_populates="grades")

    __table_args__ = (db.UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student"),)


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    kind = db.Column(db.String(40), default="reference")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    classroom = db.relationship("ClassRoom", back_populates="resources")


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    day = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="present")


class TeacherNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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
        return render_template("landing.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("teacher_dashboard" if user.role == "teacher" else "student_dashboard"))
            flash("Invalid username or password.", "danger")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/student")
    @login_required
    @role_required("student")
    def student_dashboard():
        enrolled_classes = [en.classroom for en in current_user.enrollments if not en.classroom.archived]
        class_ids = [c.id for c in enrolled_classes]
        announcements = (
            Announcement.query.filter(Announcement.class_id.in_(class_ids))
            .order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
            .limit(8)
            .all()
            if class_ids
            else []
        )
        upcoming = (
            Assignment.query.filter(Assignment.class_id.in_(class_ids), Assignment.due_date >= date.today())
            .order_by(Assignment.due_date.asc())
            .limit(10)
            .all()
            if class_ids
            else []
        )
        return render_template(
            "student_dashboard.html",
            classes=enrolled_classes,
            announcements=announcements,
            upcoming=upcoming,
            grade_summary=student_average(current_user),
        )

    @app.route("/teacher")
    @login_required
    @role_required("teacher")
    def teacher_dashboard():
        classes = ClassRoom.query.order_by(ClassRoom.name).all()
        class_ids = [c.id for c in classes]
        assignments_due_week = Assignment.query.filter(
            Assignment.class_id.in_(class_ids),
            Assignment.due_date <= date.today() + timedelta(days=7),
            Assignment.due_date >= date.today(),
        ).count()
        students_missing = Grade.query.filter_by(missing=True).count()
        total_students = User.query.filter_by(role="student").count()
        averages = []
        for classroom in classes:
            class_grades = Grade.query.join(Assignment).filter(Assignment.class_id == classroom.id, Grade.excused.is_(False)).all()
            if class_grades:
                avg = sum((g.score / g.max_score) * 100 for g in class_grades if g.max_score) / len(class_grades)
                averages.append(round(avg, 1))
        overall_avg = round(sum(averages) / len(averages), 1) if averages else 0

        recent_submissions = Grade.query.order_by(Grade.updated_at.desc()).limit(8).all()
        activity = Announcement.query.order_by(Announcement.created_at.desc()).limit(8).all()
        upcoming = Assignment.query.filter(Assignment.due_date >= date.today()).order_by(Assignment.due_date.asc()).limit(8).all()

        return render_template(
            "teacher_dashboard.html",
            classes=classes,
            activity=activity,
            pending=upcoming,
            roster_counts={c.id: len(c.enrollments) for c in classes},
            total_students=total_students,
            assignments_due_week=assignments_due_week,
            students_missing=students_missing,
            overall_avg=overall_avg,
            recent_submissions=recent_submissions,
        )

    @app.route("/class/<slug>")
    @login_required
    def class_portal(slug: str):
        classroom = ClassRoom.query.filter_by(slug=slug).first_or_404()
        if current_user.role == "student" and not is_enrolled(current_user.id, classroom.id):
            flash("You are not enrolled in this class.", "danger")
            return redirect(url_for("student_dashboard"))

        announcements = Announcement.query.filter_by(class_id=classroom.id).order_by(Announcement.pinned.desc(), Announcement.created_at.desc()).all()
        assignments = Assignment.query.filter_by(class_id=classroom.id).order_by(Assignment.due_date.asc()).all()
        resources = Resource.query.filter_by(class_id=classroom.id).order_by(Resource.created_at.desc()).all()
        roster = (
            User.query.join(Enrollment)
            .filter(Enrollment.class_id == classroom.id, User.role == "student")
            .order_by(User.full_name)
            .all()
        )

        grade_rows = []
        if current_user.role == "student":
            for assignment in assignments:
                grade = Grade.query.filter_by(assignment_id=assignment.id, student_id=current_user.id).first()
                grade_rows.append((assignment, grade))
        else:
            for assignment in assignments:
                grade_rows.append((assignment, Grade.query.filter_by(assignment_id=assignment.id).all()))

        calendar = [
            (a.due_date, f"{a.title} due") for a in assignments if a.due_date >= date.today() - timedelta(days=1)
        ][:8]

        return render_template(
            "class_portal.html",
            classroom=classroom,
            announcements=announcements,
            assignments=assignments,
            resources=resources,
            grade_rows=grade_rows,
            roster=roster,
            calendar=calendar,
        )

    @app.route("/class/<slug>/announcement", methods=["POST"])
    @login_required
    @role_required("teacher")
    def add_announcement(slug: str):
        classroom = ClassRoom.query.filter_by(slug=slug).first_or_404()
        schedule_raw = request.form.get("scheduled_for", "")
        scheduled = datetime.strptime(schedule_raw, "%Y-%m-%dT%H:%M") if schedule_raw else None
        db.session.add(
            Announcement(
                class_id=classroom.id,
                teacher_id=current_user.id,
                title=request.form.get("title", "Announcement").strip()[:150],
                message=request.form.get("message", "").strip(),
                pinned=bool(request.form.get("pinned")),
                scheduled_for=scheduled,
                created_at=scheduled or datetime.utcnow(),
            )
        )
        db.session.commit()
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/assignment", methods=["POST"])
    @login_required
    @role_required("teacher")
    def add_assignment(slug: str):
        classroom = ClassRoom.query.filter_by(slug=slug).first_or_404()
        assigned_date = datetime.strptime(request.form.get("assigned_date"), "%Y-%m-%d").date()
        due_date = datetime.strptime(request.form.get("due_date"), "%Y-%m-%d").date()
        assignment = Assignment(
            class_id=classroom.id,
            title=request.form.get("title", "New Assignment").strip()[:150],
            description=request.form.get("description", "").strip(),
            instructions=request.form.get("instructions", "").strip(),
            assigned_date=assigned_date,
            due_date=due_date,
            points_possible=float(request.form.get("points_possible", 100)),
            category=request.form.get("category", "classwork"),
            status=request.form.get("status", "published"),
            submission_type=request.form.get("submission_type", "LMS upload"),
            late_allowed=bool(request.form.get("late_allowed")),
            resource_link=request.form.get("resource_link", "").strip() or None,
            pinned=bool(request.form.get("pinned")),
        )
        db.session.add(assignment)
        db.session.commit()
        if request.form.get("duplicate_to") == "all":
            other_classes = ClassRoom.query.filter(ClassRoom.id != classroom.id, ClassRoom.archived.is_(False)).all()
            for other in other_classes:
                db.session.add(
                    Assignment(
                        class_id=other.id,
                        title=f"{assignment.title} ({classroom.slug} shared)",
                        description=assignment.description,
                        instructions=assignment.instructions,
                        assigned_date=assignment.assigned_date,
                        due_date=assignment.due_date,
                        points_possible=assignment.points_possible,
                        category=assignment.category,
                        status=assignment.status,
                        submission_type=assignment.submission_type,
                        late_allowed=assignment.late_allowed,
                        resource_link=assignment.resource_link,
                    )
                )
            db.session.commit()
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/resource", methods=["POST"])
    @login_required
    @role_required("teacher")
    def add_resource(slug: str):
        classroom = ClassRoom.query.filter_by(slug=slug).first_or_404()
        db.session.add(
            Resource(
                class_id=classroom.id,
                title=request.form.get("title", "").strip()[:150],
                link=request.form.get("link", "").strip(),
                kind=request.form.get("kind", "reference"),
            )
        )
        db.session.commit()
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/grade", methods=["POST"])
    @login_required
    @role_required("teacher")
    def set_grade(slug: str):
        assignment_id = int(request.form.get("assignment_id"))
        student_id = int(request.form.get("student_id"))
        score = float(request.form.get("score", 0) or 0)
        max_score = float(request.form.get("max_score", 100) or 100)
        feedback = request.form.get("feedback", "")
        grade = Grade.query.filter_by(assignment_id=assignment_id, student_id=student_id).first()
        if not grade:
            grade = Grade(assignment_id=assignment_id, student_id=student_id, score=score, max_score=max_score)
            db.session.add(grade)
        grade.score = score
        grade.max_score = max_score
        grade.feedback = feedback
        grade.missing = bool(request.form.get("missing"))
        grade.late = bool(request.form.get("late"))
        grade.excused = bool(request.form.get("excused"))
        grade.override = bool(request.form.get("override"))
        db.session.commit()
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/admin/classes", methods=["GET", "POST"])
    @login_required
    @role_required("teacher")
    def manage_classes():
        if request.method == "POST":
            action = request.form.get("action", "create")
            if action == "create":
                name = request.form.get("name", "").strip()
                slug = request.form.get("slug", "").strip().lower()
                if name and slug and not ClassRoom.query.filter(or_(ClassRoom.name == name, ClassRoom.slug == slug)).first():
                    db.session.add(
                        ClassRoom(
                            name=name,
                            slug=slug,
                            description=request.form.get("description", "Class portal"),
                            color=request.form.get("color", "#4f46e5"),
                        )
                    )
            elif action == "archive":
                classroom = ClassRoom.query.get_or_404(int(request.form.get("class_id")))
                classroom.archived = True
            elif action == "duplicate":
                source = ClassRoom.query.get_or_404(int(request.form.get("class_id")))
                clone = ClassRoom(
                    name=f"{source.name} - Copy",
                    slug=f"{source.slug}-copy",
                    description=source.description,
                    color=source.color,
                )
                db.session.add(clone)
                db.session.flush()
                for resource in source.resources:
                    db.session.add(Resource(class_id=clone.id, title=resource.title, link=resource.link, kind=resource.kind))
            db.session.commit()

        classes = ClassRoom.query.order_by(ClassRoom.archived.asc(), ClassRoom.name).all()
        return render_template("manage_classes.html", classes=classes)

    @app.route("/admin/students", methods=["GET", "POST"])
    @login_required
    @role_required("teacher")
    def manage_students():
        if request.method == "POST":
            action = request.form.get("action", "add")
            if action == "add":
                username = request.form.get("username", "").strip().lower()
                if username and not User.query.filter_by(username=username).first():
                    student = User(
                        username=username,
                        full_name=request.form.get("full_name", "Student"),
                        role="student",
                        student_code=request.form.get("student_code", ""),
                        status=request.form.get("status", "active"),
                        avatar=initials(request.form.get("full_name", "Student")),
                    )
                    student.set_password(request.form.get("password", "password123"))
                    db.session.add(student)
                    db.session.commit()
            elif action == "bulk_import":
                lines = [ln.strip() for ln in request.form.get("bulk_data", "").splitlines() if ln.strip()]
                for line in lines:
                    # Full Name,username,status
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) < 2:
                        continue
                    full_name, username = parts[0], parts[1].lower()
                    status = parts[2] if len(parts) > 2 else "active"
                    if not User.query.filter_by(username=username).first():
                        student = User(
                            username=username,
                            full_name=full_name,
                            role="student",
                            student_code=f"S{random.randint(1200, 9999)}",
                            status=status,
                            avatar=initials(full_name),
                        )
                        student.set_password("StudentPass!123")
                        db.session.add(student)
                db.session.commit()
            elif action == "remove":
                student = User.query.get_or_404(int(request.form.get("student_id")))
                db.session.delete(student)
                db.session.commit()
            elif action == "note":
                db.session.add(TeacherNote(student_id=int(request.form.get("student_id")), note=request.form.get("note", "")))
                db.session.commit()

        search = request.args.get("q", "").strip()
        status_filter = request.args.get("status", "")
        query = User.query.filter_by(role="student")
        if search:
            query = query.filter(or_(User.full_name.ilike(f"%{search}%"), User.username.ilike(f"%{search}%"), User.student_code.ilike(f"%{search}%")))
        if status_filter:
            query = query.filter_by(status=status_filter)

        students = query.order_by(User.full_name).all()
        classes = ClassRoom.query.filter_by(archived=False).order_by(ClassRoom.name).all()
        notes = TeacherNote.query.order_by(TeacherNote.created_at.desc()).limit(10).all()
        return render_template("manage_students.html", students=students, classes=classes, notes=notes)

    @app.route("/admin/students/<int:student_id>/enroll", methods=["POST"])
    @login_required
    @role_required("teacher")
    def enroll_student(student_id: int):
        class_id = int(request.form.get("class_id"))
        if not Enrollment.query.filter_by(student_id=student_id, class_id=class_id).first():
            db.session.add(Enrollment(student_id=student_id, class_id=class_id))
            db.session.commit()
        return redirect(url_for("manage_students"))

    @app.route("/admin/students/<int:student_id>/move", methods=["POST"])
    @login_required
    @role_required("teacher")
    def move_student(student_id: int):
        from_class = int(request.form.get("from_class"))
        to_class = int(request.form.get("to_class"))
        current = Enrollment.query.filter_by(student_id=student_id, class_id=from_class).first()
        if current:
            db.session.delete(current)
        if not Enrollment.query.filter_by(student_id=student_id, class_id=to_class).first():
            db.session.add(Enrollment(student_id=student_id, class_id=to_class))
        db.session.commit()
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
                return redirect(url_for("index"))
            return func(*args, **kwargs)

        return wrapped

    return decorator


def is_enrolled(student_id: int, class_id: int) -> bool:
    return Enrollment.query.filter_by(student_id=student_id, class_id=class_id).first() is not None


def student_average(student: User) -> float:
    valid = [g for g in student.grades if g.max_score > 0 and not g.excused]
    if not valid:
        return 0.0
    percentages = [(grade.score / grade.max_score) * 100 for grade in valid]
    return round(sum(percentages) / len(percentages), 1)


def initials(name: str) -> str:
    parts = [p[0] for p in name.split() if p]
    return "".join(parts[:2]).upper() or "ST"


def seed_data(app: Flask) -> None:
    with app.app_context():
        db.drop_all()
        db.create_all()

        teacher = User(username="teacher", full_name="Ms. Carter", role="teacher", status="active", avatar="MC")
        teacher.set_password("TeachSecure!2026")
        db.session.add(teacher)

        class_specs = [
            ("Intro to Networking and Cybersecurity", "networking-cyber", "Explore network architecture, cyber hygiene, and packet-level thinking.", "#3b82f6"),
            ("IT 1", "it-1", "Hardware, software, digital citizenship, and practical troubleshooting workflows.", "#22c55e"),
            ("IT 2", "it-2", "Advanced troubleshooting, networking systems, and collaborative device projects.", "#f59e0b"),
            ("Data Science", "data-science", "Data collection, visualization, analysis, and ethics in real-world contexts.", "#a855f7"),
            ("Intro to Computer Science", "intro-cs", "Problem-solving with variables, conditionals, loops, and creative coding.", "#06b6d4"),
        ]
        classes = []
        for name, slug, description, color in class_specs:
            classroom = ClassRoom(name=name, slug=slug, description=description, color=color)
            db.session.add(classroom)
            classes.append(classroom)

        first_names = [
            "Aiden", "Maya", "Jordan", "Leah", "Ethan", "Nora", "Lucas", "Ava", "Daniel", "Zoe", "Isaac", "Jasmine",
            "Caleb", "Laila", "Owen", "Sofia", "Henry", "Mila", "Noah", "Elena", "Wyatt", "Aria", "Mateo", "Hazel",
            "Dylan", "Ivy", "Sebastian", "Naomi", "Adrian", "Riley", "Julian", "Brooklyn", "Leo", "Savannah", "Eli", "Camila",
            "Jaxon", "Isla", "Nathan", "Ruby", "Miles", "Piper", "Carson", "Violet", "Ezra", "Quinn", "Micah", "Reese",
        ]
        last_names = [
            "Nguyen", "Patel", "Johnson", "Martinez", "Reed", "Kim", "Lopez", "Rivera", "Cooper", "Diaz", "Shah", "Hernandez",
            "Brooks", "Flores", "Carter", "Russell", "Moore", "Simmons", "Hayes", "Ramos", "Price", "Bennett", "Griffin", "Ward",
        ]
        statuses = ["active", "active", "active", "missing work", "excused", "at risk"]

        students = []
        rng = random.Random(42)
        for idx in range(65):
            full_name = f"{first_names[idx % len(first_names)]} {last_names[(idx * 3) % len(last_names)]}"
            username = f"{full_name.split()[0].lower()}.{full_name.split()[1].lower()}{idx+1}"
            student = User(
                username=username,
                full_name=full_name,
                role="student",
                student_code=f"S{1200 + idx}",
                status=rng.choice(statuses),
                avatar=initials(full_name),
            )
            student.set_password("StudentPass!123")
            db.session.add(student)
            students.append(student)

        db.session.commit()

        for class_index, classroom in enumerate(classes):
            start = class_index * 10
            roster = students[start : start + 26]
            roster += students[(class_index + 2) * 3 : (class_index + 2) * 3 + 4]
            seen_ids = set()
            for student in roster:
                if student.id in seen_ids:
                    continue
                seen_ids.add(student.id)
                db.session.add(Enrollment(student_id=student.id, class_id=classroom.id))
                if len(seen_ids) >= 28:
                    break

        topics = {
            "networking-cyber": [
                "Network Topology Sketch", "IP Addressing Practice", "Password Security Reflection", "Packet Path Lab",
                "Firewall Rule Warm-Up", "Encryption Basics Quiz", "Cyber Hygiene Checklist", "Wireshark Observation Log",
            ],
            "it-1": [
                "Hardware ID Challenge", "File Management Drill", "Digital Citizenship Discussion", "Troubleshooting Flowchart",
                "Productivity Suite Lab", "Input/Output Devices Notes", "OS Navigation Check", "IT Help Desk Simulation",
            ],
            "it-2": [
                "System Utilities Scavenger Hunt", "Network Cable Standards", "Command Line Challenge", "Ticket Response Lab",
                "Collaborative Tech Project", "Security Concept Sprint", "Device Image Recovery", "Performance Monitoring Report",
            ],
            "data-science": [
                "Survey Data Collection", "Mean Median Mode Worksheet", "Spreadsheet Formula Lab", "Visualization Critique",
                "Data Ethics Reflection", "Mini Dataset Story", "Trendline Prediction Task", "Dashboard Build Sprint",
            ],
            "intro-cs": [
                "Variable Practice", "Conditional Branch Challenge", "Loop Logic Worksheet", "Pseudocode Rewrite",
                "Python Input/Output Lab", "Debugging Relay", "Mini Web Layout Build", "Creative Coding Reflection",
            ],
        }

        month_start = date.today() - timedelta(days=28)
        for classroom in classes:
            for week in range(4):
                post_day = month_start + timedelta(days=7 * week + 1)
                db.session.add(
                    Announcement(
                        class_id=classroom.id,
                        teacher_id=teacher.id,
                        title=f"Week {week + 1} Agenda + Lab Focus",
                        message=f"This week in {classroom.name}: lab day on Wednesday, checkpoint Friday, and support block Thursday after school.",
                        pinned=week == 3,
                        created_at=datetime.combine(post_day, datetime.min.time()) + timedelta(hours=8, minutes=20),
                    )
                )
                reminder_day = month_start + timedelta(days=7 * week + 3)
                db.session.add(
                    Announcement(
                        class_id=classroom.id,
                        teacher_id=teacher.id,
                        title=f"Quiz/Checkpoint Reminder - Week {week + 1}",
                        message="Bring your device charged, review posted slides, and complete missing warm-ups before the checkpoint.",
                        created_at=datetime.combine(reminder_day, datetime.min.time()) + timedelta(hours=14, minutes=5),
                    )
                )

            topic_list = topics[classroom.slug]
            for day_idx in range(20):
                assigned = month_start + timedelta(days=day_idx)
                due = assigned + timedelta(days=2 + (day_idx % 3))
                topic = topic_list[day_idx % len(topic_list)]
                category = ["bell ringer", "lab", "quiz", "project", "notes check", "discussion"][day_idx % 6]
                points = [10, 15, 20, 40, 25, 30][day_idx % 6]
                assignment = Assignment(
                    class_id=classroom.id,
                    title=f"{topic} #{day_idx + 1}",
                    description=f"{topic} connected to {classroom.name} unit goals.",
                    instructions="Complete the task, attach evidence in portal, and include one reflection sentence about your problem-solving process.",
                    assigned_date=assigned,
                    due_date=due,
                    points_possible=points,
                    category=category,
                    status="published",
                    submission_type="LMS upload" if day_idx % 2 == 0 else "in class demo",
                    late_allowed=day_idx % 5 != 0,
                    pinned=day_idx in [3, 11],
                    resource_link="https://example.com/resource-kit",
                )
                db.session.add(assignment)

            resources = [
                ("Course Syllabus", "https://example.com/syllabus.pdf", "syllabus"),
                ("Weekly Slide Deck", "https://example.com/slides", "slides"),
                ("Lab Instructions", "https://example.com/lab-guide", "lab"),
                ("Reference Sheet", "https://example.com/reference-sheet", "reference"),
                ("Project Rubric", "https://example.com/rubric", "rubric"),
                ("Office Hours Calendar", "https://example.com/calendar", "calendar"),
            ]
            for title, link, kind in resources:
                db.session.add(Resource(class_id=classroom.id, title=title, link=link, kind=kind))

        db.session.commit()

        assignments = Assignment.query.all()
        for assignment in assignments:
            enrolled = Enrollment.query.filter_by(class_id=assignment.class_id).all()
            for en in enrolled:
                percentile = rng.random()
                missing = percentile < 0.08
                excused = 0.08 <= percentile < 0.11
                late = 0.11 <= percentile < 0.22
                if missing:
                    score = 0
                elif excused:
                    score = assignment.points_possible
                elif percentile > 0.8:
                    score = assignment.points_possible * rng.uniform(0.9, 1.0)
                elif percentile > 0.35:
                    score = assignment.points_possible * rng.uniform(0.72, 0.89)
                else:
                    score = assignment.points_possible * rng.uniform(0.55, 0.7)

                db.session.add(
                    Grade(
                        assignment_id=assignment.id,
                        student_id=en.student_id,
                        score=round(score, 1),
                        max_score=assignment.points_possible,
                        feedback=rng.choice([
                            "Solid work—great troubleshooting notes.",
                            "Good progress. Revisit step 3 for accuracy.",
                            "Missing evidence section; please resubmit.",
                            "Strong analysis and clear technical writing.",
                        ]),
                        missing=missing,
                        late=late,
                        excused=excused,
                        override=False,
                    )
                )

                if rng.random() < 0.12:
                    db.session.add(
                        Attendance(
                            class_id=assignment.class_id,
                            student_id=en.student_id,
                            day=assignment.assigned_date,
                            status=rng.choice(["present", "present", "tardy", "excused"]),
                        )
                    )

        db.session.commit()


if __name__ == "__main__":
    app = create_app()
    seed_data(app)
    app.run(host="0.0.0.0", port=5000, debug=True)
