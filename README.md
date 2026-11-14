# Trailmark

> Turn scattered project activity into a usable, evidence-linked handover for the person taking over when a team member leaves. A human reviews and approves before anything is shared.

Team ERROR404, CodePuneThinkers Hackathon, Round 2.

---

## Architecture & Stack

- **Backend**: Python 3.11+ / FastAPI
- **Frontend**: Jinja2 + HTMX (No Node build step, no SPA)
- **Database**: SQLite
- **Validation**: Pydantic v2
- **Testing**: pytest

---

## Local Setup & Run

### 1. Prerequisites
- Python 3.11+ (Tested on Python 3.12)
- Virtualenv recommended

### 2. Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Run the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

### 4. Run Tests
```bash
pytest
```

---

## Docker Setup

Build and run with Docker:
```bash
docker build -t trailmark .
docker run -p 8000:8000 -e PORT=8000 trailmark
```

---

## Project Structure
```
.
├── app/
│   ├── config.py
│   ├── db.py
│   ├── main.py
│   ├── models.py
│   ├── prompts/
│   ├── routes/
│   │   └── core.py
│   ├── schemas.py
│   ├── services/
│   ├── static/
│   └── templates/
│       ├── base.html
│       └── index.html
├── docs/
│   ├── AI_DISCLOSURE.md
│   └── CHANGELOG.md
├── samples/
├── scripts/
├── tests/
│   └── test_core.py
├── Dockerfile
├── PROJECT_BRIEF.md
├── README.md
└── requirements.txt
```
