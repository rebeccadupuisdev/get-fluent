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
├── models/                # Beanie document models
│   ├── card.py
│   └── tag.py
├── infrastructure/        # DB connection setup
│   └── mongo_setup.py
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

Requires Python 3.11+ and a running MongoDB instance.

1. Create a `.env` file in the project root:

```
MONGO_URI=mongodb://localhost:27017
DB_NAME=get_fluent
```

2. Install dependencies and start the server:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Development Approach

This project was built with Cursor as an AI-assisted coding environment. Rather than treating AI output as a black box, every significant generation is logged in `PROMPT_LOG.md` — recording what was prompted, what was produced, what was changed, and what was learned in the process.

The goal is to document genuine human–AI collaboration honestly: the AI handles boilerplate and scaffolding; decisions about feature scope, UI structure, schema design, and architecture stay with the developer.