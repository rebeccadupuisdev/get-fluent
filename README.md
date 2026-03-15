# Get Fluent

Card app for language learners: create phrase cards and attach audio.

**[Live app](https://get-fluent-production.up.railway.app/)** — production demo hosted on Railway

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
├── auth/                  # Magic link auth, rate limiting, email
│   ├── views.py
│   ├── deps.py
│   ├── security.py
│   ├── email_service.py
│   └── limiter.py
├── middleware/            # CSRF protection
│   └── csrf.py
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

# Magic link auth (required for create/update/delete)
AUTH_SECRET=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
AUTH_EMAIL_WHITELIST=you@example.com,other@example.com

# Production: base URL for magic links (prevents Host header spoofing)
# APP_BASE_URL=https://yourapp.com

# Email for magic links — choose one:
# Option A: Resend (recommended)
# RESEND_API_KEY=re_...
# RESEND_FROM=Get Fluent <noreply@yourdomain.com>   # or onboarding@resend.dev for testing

# Option B: SMTP
# SMTP_HOST=smtp.example.com
# SMTP_PORT=587
# SMTP_USER=...
# SMTP_PASSWORD=...
# SMTP_FROM=noreply@example.com

# If neither is set, links are printed to console only when DEBUG=true or ENV=development
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