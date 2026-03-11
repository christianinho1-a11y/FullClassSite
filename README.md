# SteelClass Classroom Portal

A polished Flask classroom portal for high school technology courses with weighted gradebooks, section-aware assignment duplication, and teacher preview mode.

## Included courses and sections
- Intro to Networking and Cybersecurity (Period 1 & Period 2)
- IT 1 (Period 1 & Period 2)
- IT 2 (Period 1 & Period 2)
- Data Science (Period 1 & Period 2)
- Intro to Computer Science (Period 1 & Period 2)

## Key capabilities
- Role-based teacher/student login
- Student access limited to enrolled classes
- Class portals with announcements, assignments, weighted grades, resources, and roster/calendar widgets
- **Weighted gradebook** with default categories:
  - Projects = 70%
  - Classwork = 30%
- Teacher-adjustable category weights per section (must total 100)
- Assignment management:
  - create/edit/delete/unpublish
  - schedule release
  - pin assignments
  - late policy, rubric notes, attachments
- **Smart duplication rule:** assignments duplicate only to sections with the same course name
- Teacher preview mode to view portal as a selected student
- Student management tools:
  - add/remove students
  - move students between sections
  - bulk import
  - search/filter
  - teacher notes
- Stainless steel / engineering-lab UI style with dark/light toggle

## Demo data
On startup the app reseeds one month of realistic activity:
- 10 class sections (2 per course)
- 120 students with IDs/statuses
- ~20 assignments per section (Projects/Classwork only)
- Weekly announcements + reminders
- Seeded grades including missing/late/exempt/incomplete
- Resource libraries with syllabus, slides, labs, rubrics, and guides

## Run locally
### Bash (Linux/macOS)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### PowerShell (Windows)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open: `http://localhost:5000`

## Demo accounts
- Teacher: `teacher` / `TeachSecure!2026`
- Student example: `aiden.nguyen1` / `StudentPass!123`
