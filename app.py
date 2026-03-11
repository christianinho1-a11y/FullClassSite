from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
import random

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, or_
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

    enrollments = db.relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    grades = db.relationship("Grade", back_populates="student", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class ClassRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(120), nullable=False)
    section_label = db.Column(db.String(40), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    color = db.Column(db.String(20), default="#707b86")
    archived = db.Column(db.Boolean, default=False)

    enrollments = db.relationship("Enrollment", back_populates="classroom", cascade="all, delete-orphan")
    announcements = db.relationship("Announcement", back_populates="classroom", cascade="all, delete-orphan")
    assignments = db.relationship("Assignment", back_populates="classroom", cascade="all, delete-orphan")
    resources = db.relationship("Resource", back_populates="classroom", cascade="all, delete-orphan")
    grading_setting = db.relationship("GradingSetting", back_populates="classroom", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (db.UniqueConstraint("course_name", "section_label", name="uq_course_section"),)


class GradingSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), unique=True, nullable=False)
    projects_weight = db.Column(db.Float, default=70.0)
    classwork_weight = db.Column(db.Float, default=30.0)
    term_label = db.Column(db.String(60), default="Marking Period 1")

    classroom = db.relationship("ClassRoom", back_populates="grading_setting")


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
    release_date = db.Column(db.Date, nullable=False, default=date.today)
    points_possible = db.Column(db.Float, default=100)
    category = db.Column(db.String(20), default="Classwork")
    status = db.Column(db.String(30), default="Published")
    submission_type = db.Column(db.String(50), default="LMS Upload")
    late_allowed = db.Column(db.Boolean, default=True)
    pinned = db.Column(db.Boolean, default=False)
    rubric_notes = db.Column(db.Text, default="")
    resource_link = db.Column(db.String(255), nullable=True)

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
    exempt = db.Column(db.Boolean, default=False)
    incomplete = db.Column(db.Boolean, default=False)
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
    kind = db.Column(db.String(40), default="notes")
    unit = db.Column(db.String(40), default="Unit 1")
    pinned = db.Column(db.Boolean, default=False)

    classroom = db.relationship("ClassRoom", back_populates="resources")


class TeacherNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def role_required(role: str):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                return redirect(url_for("index"))
            return func(*args, **kwargs)

        return wrapped

    return decorator


def initials(name: str) -> str:
    return "".join([part[0] for part in name.split()[:2]]).upper()


def weighted_breakdown(student_id: int, classroom: ClassRoom) -> dict[str, float]:
    setting = classroom.grading_setting or GradingSetting(projects_weight=70, classwork_weight=30)
    grades = (
        Grade.query.join(Assignment)
        .filter(Grade.student_id == student_id, Assignment.class_id == classroom.id)
        .all()
    )
    groups = {"Projects": [], "Classwork": []}
    for g in grades:
        if g.exempt:
            continue
        if g.max_score > 0:
            groups[g.assignment.category].append((g.score / g.max_score) * 100)
    p_avg = sum(groups["Projects"]) / len(groups["Projects"]) if groups["Projects"] else 0.0
    c_avg = sum(groups["Classwork"]) / len(groups["Classwork"]) if groups["Classwork"] else 0.0
    weighted = (p_avg * setting.projects_weight + c_avg * setting.classwork_weight) / 100
    return {"projects": round(p_avg, 1), "classwork": round(c_avg, 1), "weighted": round(weighted, 1)}


def is_enrolled(student_id: int, class_id: int) -> bool:
    return Enrollment.query.filter_by(student_id=student_id, class_id=class_id).first() is not None


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-me-in-production"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("teacher_dashboard" if current_user.role == "teacher" else "student_dashboard"))
        return render_template("landing.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(request.form.get("password", "")):
                login_user(user)
                return redirect(url_for("teacher_dashboard" if user.role == "teacher" else "student_dashboard"))
            flash("Invalid credentials", "danger")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/teacher")
    @login_required
    @role_required("teacher")
    def teacher_dashboard():
        classes = ClassRoom.query.order_by(ClassRoom.course_name, ClassRoom.section_label).all()
        total_students = User.query.filter_by(role="student").count()
        missing_count = Grade.query.filter(or_(Grade.missing.is_(True), Grade.incomplete.is_(True))).count()
        queue_to_grade = Assignment.query.filter(Assignment.due_date <= date.today(), Assignment.status == "Published").count()
        at_risk = User.query.filter(User.role == "student", User.status == "at risk").count()

        class_rows = []
        for c in classes:
            student_ids = [e.student_id for e in c.enrollments]
            avgs = [weighted_breakdown(sid, c)["weighted"] for sid in student_ids]
            class_rows.append({"classroom": c, "avg": round(sum(avgs) / len(avgs), 1) if avgs else 0})

        recent = Grade.query.order_by(Grade.updated_at.desc()).limit(10).all()
        upcoming = Assignment.query.filter(Assignment.due_date >= date.today(), Assignment.status == "Published").order_by(Assignment.due_date).limit(10).all()
        activity = Announcement.query.order_by(Announcement.created_at.desc()).limit(8).all()
        return render_template("teacher_dashboard.html", classes=classes, class_rows=class_rows, total_students=total_students, missing_count=missing_count, queue_to_grade=queue_to_grade, at_risk=at_risk, recent=recent, upcoming=upcoming, activity=activity)

    @app.route("/student")
    @login_required
    @role_required("student")
    def student_dashboard():
        classes = [en.classroom for en in current_user.enrollments if not en.classroom.archived]
        class_ids = [c.id for c in classes]
        announcements = Announcement.query.filter(Announcement.class_id.in_(class_ids)).order_by(Announcement.pinned.desc(), Announcement.created_at.desc()).limit(8).all() if class_ids else []
        upcoming = Assignment.query.filter(Assignment.class_id.in_(class_ids), Assignment.due_date >= date.today(), Assignment.status == "Published", Assignment.release_date <= date.today()).order_by(Assignment.due_date).limit(10).all() if class_ids else []
        missing = Grade.query.join(Assignment).filter(Grade.student_id == current_user.id, Grade.missing.is_(True), Assignment.class_id.in_(class_ids)).count() if class_ids else 0
        return render_template("student_dashboard.html", classes=classes, announcements=announcements, upcoming=upcoming, missing=missing)

    @app.route("/teacher/preview/<int:student_id>")
    @login_required
    @role_required("teacher")
    def start_preview(student_id: int):
        session["preview_student_id"] = student_id
        return redirect(url_for("student_preview"))

    @app.route("/teacher/preview/end")
    @login_required
    @role_required("teacher")
    def end_preview():
        session.pop("preview_student_id", None)
        return redirect(url_for("teacher_dashboard"))

    @app.route("/teacher/preview")
    @login_required
    @role_required("teacher")
    def student_preview():
        sid = session.get("preview_student_id")
        student = User.query.get_or_404(sid)
        classes = [en.classroom for en in student.enrollments if not en.classroom.archived]
        class_ids = [c.id for c in classes]
        announcements = Announcement.query.filter(Announcement.class_id.in_(class_ids)).order_by(Announcement.created_at.desc()).limit(6).all() if class_ids else []
        upcoming = Assignment.query.filter(Assignment.class_id.in_(class_ids), Assignment.due_date >= date.today(), Assignment.status == "Published", Assignment.release_date <= date.today()).order_by(Assignment.due_date).limit(8).all() if class_ids else []
        return render_template("student_dashboard.html", classes=classes, announcements=announcements, upcoming=upcoming, missing=0, preview_mode=True, preview_student=student)

    @app.route("/class/<slug>")
    @login_required
    def class_portal(slug: str):
        classroom = ClassRoom.query.filter_by(slug=slug).first_or_404()
        preview_student = None
        acting_student = current_user
        if current_user.role == "teacher" and session.get("preview_student_id"):
            preview_student = User.query.get(session["preview_student_id"])
            if preview_student and is_enrolled(preview_student.id, classroom.id):
                acting_student = preview_student

        if current_user.role == "student" and not is_enrolled(current_user.id, classroom.id):
            return redirect(url_for("student_dashboard"))

        announcements = Announcement.query.filter_by(class_id=classroom.id).order_by(Announcement.pinned.desc(), Announcement.created_at.desc()).all()
        assignments_q = Assignment.query.filter_by(class_id=classroom.id)
        if current_user.role == "student" or preview_student:
            assignments_q = assignments_q.filter(Assignment.status == "Published", Assignment.release_date <= date.today())
        if request.args.get("category") in ["Projects", "Classwork"]:
            assignments_q = assignments_q.filter_by(category=request.args.get("category"))
        assignments = assignments_q.order_by(Assignment.due_date).all()
        resources = Resource.query.filter_by(class_id=classroom.id).order_by(Resource.pinned.desc(), Resource.unit, Resource.title).all()
        roster = User.query.join(Enrollment).filter(Enrollment.class_id == classroom.id, User.role == "student").order_by(User.full_name).all()
        gradebook_rows = []
        if current_user.role == "teacher" and not preview_student:
            for s in roster:
                if request.args.get("student") and request.args.get("student") != str(s.id):
                    continue
                breakdown = weighted_breakdown(s.id, classroom)
                if request.args.get("grade_status") == "failing" and breakdown["weighted"] >= 70:
                    continue
                gradebook_rows.append((s, breakdown))

        student_grades = []
        if current_user.role == "student" or preview_student:
            for a in assignments:
                g = Grade.query.filter_by(assignment_id=a.id, student_id=acting_student.id).first()
                student_grades.append((a, g))

        return render_template("class_portal.html", classroom=classroom, announcements=announcements, assignments=assignments, resources=resources, roster=roster, gradebook_rows=gradebook_rows, student_grades=student_grades, grading_setting=classroom.grading_setting, preview_mode=bool(preview_student), preview_student=preview_student, all_students=User.query.filter_by(role="student").order_by(User.full_name).all())

    @app.route("/class/<slug>/announcement", methods=["POST"])
    @login_required
    @role_required("teacher")
    def add_announcement(slug: str):
        c = ClassRoom.query.filter_by(slug=slug).first_or_404()
        sch = request.form.get("scheduled_for")
        scheduled = datetime.strptime(sch, "%Y-%m-%dT%H:%M") if sch else None
        db.session.add(Announcement(class_id=c.id, teacher_id=current_user.id, title=request.form.get("title", "").strip()[:150], message=request.form.get("message", "").strip(), pinned=bool(request.form.get("pinned")), scheduled_for=scheduled, created_at=scheduled or datetime.utcnow()))
        db.session.commit()
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/assignment", methods=["POST"])
    @login_required
    @role_required("teacher")
    def add_assignment(slug: str):
        c = ClassRoom.query.filter_by(slug=slug).first_or_404()
        category = request.form.get("category", "Classwork")
        if category not in ["Projects", "Classwork"]:
            category = "Classwork"
        a = Assignment(
            class_id=c.id,
            title=request.form.get("title", "").strip()[:150],
            description=request.form.get("description", "").strip(),
            instructions=request.form.get("instructions", "").strip(),
            rubric_notes=request.form.get("rubric_notes", "").strip(),
            assigned_date=datetime.strptime(request.form.get("assigned_date"), "%Y-%m-%d").date(),
            due_date=datetime.strptime(request.form.get("due_date"), "%Y-%m-%d").date(),
            release_date=datetime.strptime(request.form.get("release_date"), "%Y-%m-%d").date(),
            points_possible=float(request.form.get("points_possible", 100)),
            category=category,
            status=request.form.get("status", "Draft"),
            submission_type=request.form.get("submission_type", "LMS Upload"),
            late_allowed=bool(request.form.get("late_allowed")),
            pinned=bool(request.form.get("pinned")),
            resource_link=request.form.get("resource_link", ""),
        )
        db.session.add(a)
        db.session.commit()
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/assignment/<int:assignment_id>/edit", methods=["POST"])
    @login_required
    @role_required("teacher")
    def edit_assignment(slug: str, assignment_id: int):
        a = Assignment.query.get_or_404(assignment_id)
        action = request.form.get("action", "edit")
        if action == "delete":
            db.session.delete(a)
        elif action == "unpublish":
            a.status = "Draft"
        elif action == "duplicate":
            src = ClassRoom.query.get_or_404(a.class_id)
            targets = ClassRoom.query.filter(and_(ClassRoom.course_name == src.course_name, ClassRoom.id != src.id)).all()
            for t in targets:
                db.session.add(Assignment(class_id=t.id, title=a.title, description=a.description, instructions=a.instructions, rubric_notes=a.rubric_notes, assigned_date=a.assigned_date, due_date=a.due_date, release_date=a.release_date, points_possible=a.points_possible, category=a.category, status=a.status, submission_type=a.submission_type, late_allowed=a.late_allowed, resource_link=a.resource_link))
        else:
            a.title = request.form.get("title", a.title)
            a.points_possible = float(request.form.get("points_possible", a.points_possible))
            a.category = request.form.get("category", a.category) if request.form.get("category") in ["Projects", "Classwork"] else a.category
        db.session.commit()
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/resource", methods=["POST"])
    @login_required
    @role_required("teacher")
    def add_resource(slug: str):
        c = ClassRoom.query.filter_by(slug=slug).first_or_404()
        db.session.add(Resource(class_id=c.id, title=request.form.get("title", ""), link=request.form.get("link", ""), kind=request.form.get("kind", "notes"), unit=request.form.get("unit", "Unit 1"), pinned=bool(request.form.get("pinned"))))
        db.session.commit()
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/grade", methods=["POST"])
    @login_required
    @role_required("teacher")
    def set_grade(slug: str):
        grade = Grade.query.filter_by(assignment_id=int(request.form.get("assignment_id")), student_id=int(request.form.get("student_id"))).first()
        if not grade:
            grade = Grade(assignment_id=int(request.form.get("assignment_id")), student_id=int(request.form.get("student_id")), score=0, max_score=100)
            db.session.add(grade)
        grade.score = float(request.form.get("score", 0))
        grade.max_score = float(request.form.get("max_score", 100))
        grade.feedback = request.form.get("feedback", "")
        grade.missing = bool(request.form.get("missing"))
        grade.late = bool(request.form.get("late"))
        grade.exempt = bool(request.form.get("exempt"))
        grade.incomplete = bool(request.form.get("incomplete"))
        grade.override = bool(request.form.get("override"))
        db.session.commit()
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/class/<slug>/grading-settings", methods=["POST"])
    @login_required
    @role_required("teacher")
    def update_grading_settings(slug: str):
        c = ClassRoom.query.filter_by(slug=slug).first_or_404()
        setting = c.grading_setting or GradingSetting(class_id=c.id)
        p = float(request.form.get("projects_weight", 70))
        cw = float(request.form.get("classwork_weight", 30))
        if round(p + cw, 2) != 100.0:
            flash("Weights must total 100.", "warning")
            return redirect(url_for("class_portal", slug=slug))
        setting.projects_weight = p
        setting.classwork_weight = cw
        setting.term_label = request.form.get("term_label", setting.term_label)
        db.session.add(setting)
        db.session.commit()
        return redirect(url_for("class_portal", slug=slug))

    @app.route("/admin/classes", methods=["GET", "POST"])
    @login_required
    @role_required("teacher")
    def manage_classes():
        if request.method == "POST":
            action = request.form.get("action", "create")
            if action == "create":
                course_name = request.form.get("course_name", "").strip()
                section = request.form.get("section_label", "").strip()
                slug = request.form.get("slug", "").strip().lower()
                if course_name and section and slug:
                    c = ClassRoom(course_name=course_name, section_label=section, slug=slug, description=request.form.get("description", ""), color=request.form.get("color", "#808b96"))
                    db.session.add(c)
                    db.session.flush()
                    db.session.add(GradingSetting(class_id=c.id, projects_weight=70, classwork_weight=30))
            elif action == "archive":
                c = ClassRoom.query.get_or_404(int(request.form.get("class_id")))
                c.archived = True
            elif action == "duplicate":
                c = ClassRoom.query.get_or_404(int(request.form.get("class_id")))
                copy = ClassRoom(course_name=c.course_name, section_label=f"{c.section_label} Copy", slug=f"{c.slug}-copy", description=c.description, color=c.color)
                db.session.add(copy)
            db.session.commit()
        classes = ClassRoom.query.order_by(ClassRoom.course_name, ClassRoom.section_label).all()
        return render_template("manage_classes.html", classes=classes)

    @app.route("/admin/students", methods=["GET", "POST"])
    @login_required
    @role_required("teacher")
    def manage_students():
        if request.method == "POST":
            action = request.form.get("action", "add")
            if action == "add":
                s = User(username=request.form.get("username", "").lower(), full_name=request.form.get("full_name", ""), role="student", student_code=request.form.get("student_code", ""), status=request.form.get("status", "active"), avatar=initials(request.form.get("full_name", "Student")))
                s.set_password(request.form.get("password", "StudentPass!123"))
                db.session.add(s)
            elif action == "remove":
                db.session.delete(User.query.get_or_404(int(request.form.get("student_id"))))
            elif action == "note":
                db.session.add(TeacherNote(student_id=int(request.form.get("student_id")), note=request.form.get("note", "")))
            elif action == "bulk":
                for row in request.form.get("bulk_data", "").splitlines():
                    parts = [p.strip() for p in row.split(",")]
                    if len(parts) >= 2 and not User.query.filter_by(username=parts[1].lower()).first():
                        s = User(username=parts[1].lower(), full_name=parts[0], role="student", student_code=f"S{random.randint(3000, 9999)}", status=parts[2] if len(parts) > 2 else "active", avatar=initials(parts[0]))
                        s.set_password("StudentPass!123")
                        db.session.add(s)
            db.session.commit()

        query = User.query.filter_by(role="student")
        q = request.args.get("q", "").strip()
        if q:
            query = query.filter(or_(User.full_name.ilike(f"%{q}%"), User.student_code.ilike(f"%{q}%"), User.username.ilike(f"%{q}%")))
        status = request.args.get("status", "")
        if status:
            query = query.filter_by(status=status)
        students = query.order_by(User.full_name).all()
        classes = ClassRoom.query.filter_by(archived=False).all()
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
        old_id = int(request.form.get("from_class"))
        new_id = int(request.form.get("to_class"))
        old_en = Enrollment.query.filter_by(student_id=student_id, class_id=old_id).first()
        if old_en:
            db.session.delete(old_en)
        if not Enrollment.query.filter_by(student_id=student_id, class_id=new_id).first():
            db.session.add(Enrollment(student_id=student_id, class_id=new_id))
        db.session.commit()
        return redirect(url_for("manage_students"))

    return app


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


def seed_data(app: Flask) -> None:
    with app.app_context():
        db.drop_all()
        db.create_all()

        teacher = User(username="teacher", full_name="Ms. Carter", role="teacher", avatar="MC", status="active")
        teacher.set_password("TeachSecure!2026")
        db.session.add(teacher)

        base_courses = [
            "Intro to Networking and Cybersecurity",
            "IT 1",
            "IT 2",
            "Data Science",
            "Intro to Computer Science",
        ]
        sections = ["Period 1", "Period 2"]
        classes: list[ClassRoom] = []
        for idx, course in enumerate(base_courses):
            for sidx, section in enumerate(sections):
                c = ClassRoom(course_name=course, section_label=section, slug=f"{course.lower().replace(' ', '-')}-p{sidx+1}", description=f"{course} ({section}) modern engineering-lab section.", color=["#98a2ad", "#6f7d8c"][sidx])
                db.session.add(c)
                db.session.flush()
                db.session.add(GradingSetting(class_id=c.id, projects_weight=70, classwork_weight=30, term_label="Marking Period 1"))
                classes.append(c)

        first = ["Aiden", "Maya", "Jordan", "Leah", "Ethan", "Nora", "Lucas", "Ava", "Daniel", "Zoe", "Isaac", "Jasmine", "Caleb", "Laila", "Owen", "Sofia", "Henry", "Mila", "Noah", "Elena", "Wyatt", "Aria", "Mateo", "Hazel", "Dylan", "Ivy", "Sebastian", "Naomi", "Adrian", "Riley"]
        last = ["Nguyen", "Patel", "Johnson", "Martinez", "Kim", "Lopez", "Rivera", "Cooper", "Diaz", "Shah", "Hernandez", "Brooks", "Flores", "Carter", "Russell", "Moore"]
        statuses = ["active", "active", "active", "missing work", "at risk", "excused"]
        students: list[User] = []
        rng = random.Random(8)
        for i in range(120):
            name = f"{first[i % len(first)]} {last[(i * 3) % len(last)]}"
            user = User(username=f"{name.split()[0].lower()}.{name.split()[1].lower()}{i+1}", full_name=name, role="student", student_code=f"S{2000+i}", status=rng.choice(statuses), avatar=initials(name))
            user.set_password("StudentPass!123")
            db.session.add(user)
            students.append(user)

        db.session.commit()

        for class_idx, c in enumerate(classes):
            pool = students[class_idx * 8 : class_idx * 8 + 22] + students[(class_idx * 5) % 60 : (class_idx * 5) % 60 + 6]
            used = set()
            for s in pool:
                if s.id in used:
                    continue
                used.add(s.id)
                db.session.add(Enrollment(student_id=s.id, class_id=c.id))
                if len(used) >= 28:
                    break

        templates = {
            "Intro to Networking and Cybersecurity": ["Password Security Notes Check", "Client vs Server Practice", "Network Diagram Mini Project", "Cyber Hygiene Reflection", "Encryption Basics Activity"],
            "IT 1": ["Computer Hardware Notes", "Troubleshooting Practice", "Digital Citizenship Questions", "File Management Classwork", "Device Identification Project"],
            "IT 2": ["System Utility Practice", "Troubleshooting Flowchart Project", "Networking Terms Review", "Basic Security Concepts Classwork", "Collaborative Troubleshooting Task"],
            "Data Science": ["Spreadsheet Basics", "Data Visualization Practice", "Mean Median Mode Classwork", "Survey Analysis Project", "Chart Interpretation Assignment"],
            "Intro to Computer Science": ["Variables Practice", "User Input Program", "Conditional Logic Classwork", "Pseudocode Exercise", "Creative Coding Project"],
        }

        month_start = date.today() - timedelta(days=28)
        for c in classes:
            for week in range(4):
                d = month_start + timedelta(days=week * 7 + 1)
                db.session.add(Announcement(class_id=c.id, teacher_id=teacher.id, title=f"Week {week+1} Agenda - {c.section_label}", message=f"{c.course_name}: weekly agenda, lab reminder, and support times posted.", pinned=week == 3, created_at=datetime.combine(d, datetime.min.time()) + timedelta(hours=8)))
                db.session.add(Announcement(class_id=c.id, teacher_id=teacher.id, title=f"Checkpoint Reminder - Week {week+1}", message="Review posted resources, complete missing work, and prep for checkpoint.", created_at=datetime.combine(d, datetime.min.time()) + timedelta(hours=13)))

            names = templates[c.course_name]
            for day_idx in range(20):
                assigned = month_start + timedelta(days=day_idx)
                due = assigned + timedelta(days=2 + day_idx % 2)
                title = f"{names[day_idx % len(names)]} #{day_idx+1}"
                category = "Projects" if day_idx % 4 == 0 else "Classwork"
                db.session.add(Assignment(class_id=c.id, title=title, description=f"{title} aligned to {c.course_name} outcomes.", instructions="Follow posted steps and submit evidence in portal.", rubric_notes="Use rubric focus: clarity, completion, and technical accuracy.", assigned_date=assigned, due_date=due, release_date=assigned, points_possible=40 if category == "Projects" else 20, category=category, status="Published", submission_type="LMS Upload" if day_idx % 2 == 0 else "In-class Demo", late_allowed=day_idx % 5 != 0, pinned=day_idx in [4, 12], resource_link="https://example.com/material"))

            res = [
                ("Course Syllabus", "https://example.com/syllabus.pdf", "syllabus"),
                ("Unit Slides", "https://example.com/slides", "slides"),
                ("Lab Instructions", "https://example.com/labs", "lab"),
                ("Project Rubric", "https://example.com/rubric", "rubric"),
                ("Study Guide", "https://example.com/study", "guide"),
            ]
            for r in res:
                db.session.add(Resource(class_id=c.id, title=r[0], link=r[1], kind=r[2], unit="Unit 1", pinned=r[0] == "Course Syllabus"))

        db.session.commit()

        for a in Assignment.query.all():
            en = Enrollment.query.filter_by(class_id=a.class_id).all()
            for e in en:
                roll = rng.random()
                missing = roll < 0.08
                late = 0.08 <= roll < 0.2
                exempt = 0.2 <= roll < 0.24
                incomplete = 0.24 <= roll < 0.3
                if missing:
                    score = 0
                elif exempt:
                    score = a.points_possible
                elif roll > 0.8:
                    score = a.points_possible * rng.uniform(0.9, 1.0)
                elif roll > 0.45:
                    score = a.points_possible * rng.uniform(0.75, 0.89)
                else:
                    score = a.points_possible * rng.uniform(0.55, 0.72)
                db.session.add(Grade(assignment_id=a.id, student_id=e.student_id, score=round(score, 1), max_score=a.points_possible, feedback=rng.choice(["Strong technical reasoning.", "Good effort; revise details for full credit.", "Missing sections. Complete and resubmit.", "Clear progress this week."]), missing=missing, late=late, exempt=exempt, incomplete=incomplete, override=False))

        db.session.commit()


if __name__ == "__main__":
    app = create_app()
    seed_data(app)
    app.run(host="0.0.0.0", port=5000, debug=True)
