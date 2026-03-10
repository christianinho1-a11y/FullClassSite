# Full Classroom Portal

Production-style Flask classroom portal for teacher and students.

## Features
- Secure login with role-based dashboards (teacher/student)
- Student-specific class enrollment and access controls
- Per-class portals with announcements, assignments, grades, resources, and upcoming work
- Teacher admin controls for classes, students, enrollments, posting, assignment creation, grading
- SQLite database schema for users, roles, classes, enrollments, announcements, assignments, grades, and resources
- Seeded demo data for five classes:
  - Intro to Networking and Cybersecurity
  - IT 1
  - IT 2
  - Data Science
  - Intro to Computer Science
- Responsive UI with sidebar navigation, dashboard cards, polished tables, and light/dark mode toggle

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`.

## Demo accounts
- Teacher: `teacher` / `TeachSecure!2026`
- Student: `alex.j` / `StudentPass!123`

## Security notes
- Passwords are hashed using Werkzeug
- Role-gated and login-protected routes
- Students cannot access teacher/admin pages
- Students can only access enrolled class portals and their own grade view
- Jinja autoescaping protects rendered HTML output by default

## Deployment
Set a production-grade `SECRET_KEY`, run with gunicorn/uwsgi behind nginx, and migrate DB to Postgres when scaling.
