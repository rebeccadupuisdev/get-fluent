# Get Fluent

Card app for language learners: create phrase cards and attach audio.

## Tech Stack

- **Backend:** FastAPI + Jinja2 templates
- **Frontend:** HTMX + Tailwind CSS
- **Database:** MongoDB + Beanie

## Project Structure

```
/
├── main.py                # Application entry point
├── views/                 # Web route handlers
├── services/              # Business and data logic
├── frontend/
│   ├── static/
│   └── templates/         # Jinja2 templates
│       ├── base.html
│       ├── index.html
│       └── partials/      # HTMX fragment templates
├── tests/
├── requirements.txt
├── pyproject.toml         # Ruff configuration
├── pytest.ini
├── PROMPT_LOG.md
├── AGENTS.md
└── README.md
```

## Getting Started

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Development Approach

This project was built with Cursor as an AI-assisted coding environment. Rather than treating AI output as a black box, every significant generation is logged in `PROMPT_LOG.md` — recording what was prompted, what was produced, what was changed, and what was learned in the process.

The goal is to document genuine human–AI collaboration honestly: the AI handles boilerplate and scaffolding; decisions about feature scope, UI structure, schema design, and architecture stay with the developer.