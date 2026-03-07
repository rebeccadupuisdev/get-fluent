# AGENTS.md — Get Fluent

Project-specific context for the **Get Fluent** app.
This file overrides or extends the global `.cursor/rules` where noted.

---

## Project Overview

Card app for language learners: create phrase cards and attach audio.

---

## Stack

This project uses the global preferred stack without modification:

| Layer | Choice |
|---|---|
| Backend | FastAPI + Jinja2Templates |
| Frontend | HTMX + Tailwind CSS |
| Database | MongoDB + Beanie |

Do not suggest alternatives to any of these.

---

## Project Structure

```
/
├── main.py                  # FastAPI app, lifespan startup, static file mounting
├── views/                   # Web route handlers
├── services/                # Business and data logic
├── frontend/
│   ├── static/
│   └── templates/           # Jinja2 templates
│       ├── base.html        # Base layout with Tailwind + HTMX CDN links
│       ├── index.html       # Main page
│       └── partials/        # HTMX HTML fragment templates (one per section)
├── tests/
├── requirements.txt         # fastapi, uvicorn, jinja2
├── pyproject.toml           # Ruff configuration
├── pytest.ini
├── PROMPT_LOG.md            # Developer-maintained AI prompt log
├── AGENTS.md                # This file
└── README.md                # Includes "Development Approach" section
```

---

## Prompt Logging

This project uses `PROMPT_LOG.md` as documented in the global `prompt_logging.mdc` rule.
The log is part of the developer's portfolio documentation and must be kept up to date after every significant generation.
