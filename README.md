# Full Classroom Portal (FutureLab)

Modern Flask classroom portal with realistic one-month demo activity for five high school technology classes.

## Included classes
- Intro to Networking and Cybersecurity
- IT 1
- IT 2
- Data Science
- Intro to Computer Science

## Features
- Role-based login (teacher + student)
- Student dashboards (class cards, announcements, due calendar, grade summary)
- Teacher command center (class metrics, missing work, recent grading activity)
- Class portals with announcements, assignments, grades, resources, roster, and calendar feed
- Teacher controls for:
  - create/archive/duplicate classes
  - add/remove/move students
  - bulk import students
  - add behavior/progress notes
  - create/pin/schedule announcements
  - create assignments with category, points, submission type, late policy
  - duplicate assignments across all classes
  - set grades + mark missing/late/excused/override
- Seeded month-long demo data:
  - ~65 students with status + student IDs
  - 20 assignments per class
  - weekly announcements + reminders per class
  - realistic resources and grade distributions

## Run locally (Linux/macOS Bash)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Run locally (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open: `http://localhost:5000`

## Demo accounts
- Teacher: `teacher` / `TeachSecure!2026`
- Student example username: `aiden.nguyen1` (all students use `StudentPass!123`)

## Notes
- This demo rebuilds and reseeds `portal.db` on startup so each run has a full month of fresh sample content.
