---
name: Get Fluent App Build
overview: "Build the Get Fluent app from a blank slate: phrase cards with audio, nested tags, search, and sorted card display. The stack is FastAPI + Jinja2, HTMX + Tailwind, MongoDB + Beanie."
todos:
  - id: scaffold-requirements
    content: Task 1.1 — requirements.txt with all dependencies
    status: completed
  - id: scaffold-pyproject
    content: Task 1.2 — pyproject.toml with Ruff config
    status: completed
  - id: scaffold-pytest
    content: Task 1.3 — pytest.ini
    status: completed
  - id: scaffold-dirs
    content: Task 1.4 — Create all empty directories and __init__.py files
    status: completed
  - id: scaffold-main
    content: Task 1.5 — main.py skeleton (app, lifespan, static mount, router includes)
    status: completed
  - id: model-tag
    content: Task 2.1 — models/tag.py Beanie Tag document
    status: completed
  - id: model-card
    content: Task 2.2 — models/card.py Beanie Card document
    status: completed
  - id: model-init
    content: Task 2.3 — models/__init__.py with DOCUMENT_MODELS export
    status: completed
  - id: service-tag-create
    content: "Task 3.1 — tag_service.py: create_tag"
    status: completed
  - id: service-tag-read
    content: "Task 3.2 — tag_service.py: get_all_tags, build_tag_tree"
    status: completed
  - id: service-card-create
    content: "Task 3.3 — card_service.py: create_card"
    status: completed
  - id: service-card-list
    content: "Task 3.4 — card_service.py: get_cards with optional tag filter"
    status: completed
  - id: service-card-search
    content: "Task 3.5 — card_service.py: search_cards"
    status: completed
  - id: service-card-delete
    content: "Task 3.6 — card_service.py: delete_card"
    status: completed
  - id: service-audio
    content: "Task 3.7 — audio_service.py: save_audio, delete_audio"
    status: completed
  - id: views-card-index
    content: "Task 4.1 — card_views.py: GET / (index page)"
    status: completed
  - id: views-card-create
    content: "Task 4.2 — card_views.py: POST /cards"
    status: completed
  - id: views-card-list
    content: "Task 4.3 — card_views.py: GET /cards (search + tag filter fragment)"
    status: completed
  - id: views-card-delete
    content: "Task 4.4 — card_views.py: DELETE /cards/{card_id}"
    status: completed
  - id: views-tag-list
    content: "Task 4.5 — tag_views.py: GET /tags"
    status: completed
  - id: views-tag-create
    content: "Task 4.6 — tag_views.py: POST /tags"
    status: completed
  - id: views-wire-routers
    content: Task 4.7 — Wire routers into main.py
    status: completed
  - id: tmpl-base
    content: Task 5.1 — base.html with Tailwind + HTMX CDN, layout slots
    status: completed
  - id: tmpl-index
    content: "Task 5.2 — index.html (two-column: tag sidebar + card main area)"
    status: completed
  - id: tmpl-card-item
    content: Task 5.3 — partials/card_item.html (phrase, tag pills, audio player, delete)
    status: completed
  - id: tmpl-card-list
    content: Task 5.4 — partials/card_list.html (HTMX swap target wrapper)
    status: completed
  - id: tmpl-card-form
    content: Task 5.5 — partials/card_form.html (phrase, tags, audio upload)
    status: completed
  - id: tmpl-tag-tree
    content: Task 5.6 — partials/tag_tree.html (recursive nested tag list with filter links)
    status: completed
  - id: tmpl-tag-form
    content: Task 5.7 — partials/tag_form.html (tag name + parent dropdown)
    status: completed
  - id: tmpl-search-bar
    content: Task 5.8 — partials/search_bar.html (debounced HTMX search input)
    status: completed
  - id: test-conftest
    content: "Task 6.1 — tests/conftest.py: async fixtures with mongomock"
    status: completed
  - id: test-tag-service
    content: Task 6.2 — tests/test_tag_service.py
    status: completed
  - id: test-card-service
    content: Task 6.3 — tests/test_card_service.py
    status: completed
  - id: test-views
    content: Task 6.4 — tests/test_views.py smoke tests
    status: completed
---

# Get Fluent App — Full Build Plan

## Architecture Overview

```mermaid
flowchart TD
    Browser -->|"HTMX requests"| FastAPI
    FastAPI --> Views
    Views --> Services
    Services --> Beanie
    Beanie --> MongoDB
    FastAPI -->|"Jinja2 render"| Templates
    FastAPI -->|"static files"| AudioStorage["frontend/static/content/"]
```

**Data model summary:**

- `Tag`: `name`, `slug`, `parent_slug: str | None = None`
- `Card`: `phrase`, `audio_filename`, `created_at`, `tag_slugs: list[str] = []`

Tags optionally carry a `parent_slug` (plain string reference, no DB link). When a tag is added to a card, the full ancestor chain is resolved and **all** slugs in that chain are stored flat in `tag_slugs`. Filtering by a tag is then a simple `{$in: [slug]}` query — no descendant expansion needed.

---

## Phase 1 — Project Scaffold

- **Task 1.1 — `requirements.txt`**: `fastapi`, `uvicorn[standard]`, `jinja2`, `motor`, `beanie`, `python-multipart`, `aiofiles`, `pytest`, `pytest-asyncio`, `httpx`
- **Task 1.2 — `pyproject.toml`**: Ruff config (line-length 88, target-version py311, formatter: double quotes, space indent, no skip-magic-trailing-comma, auto line-endings)
- **Task 1.3 — `pytest.ini`**: asyncio mode = auto, testpaths = tests
- **Task 1.4 — Directory skeleton**: create `models/`, `views/`, `services/`, `tests/`, `frontend/static/content/`, `frontend/templates/partials/`
- **Task 1.5 — `main.py` skeleton**: FastAPI app with `lifespan` (Beanie init), `StaticFiles` mount at `/static`, `Jinja2Templates`, router includes placeholder

---

## Phase 2 — Data Models

Files: `models/tag.py`, `models/card.py`, `models/__init__.py`

- **Task 2.1 — `models/tag.py`**: Beanie `Tag` document with `name: str`, `slug: str`, `parent_slug: str | None = None`, `Settings.name = "tags"`
- **Task 2.2 — `models/card.py`**: Beanie `Card` document with `phrase: str`, `audio_filename: str | None = None`, `created_at: datetime` (default `utcnow`), `tag_slugs: list[str] = []`, `Settings.name = "cards"`
- **Task 2.3 — `models/__init__.py`**: export `Tag`, `Card`; expose `DOCUMENT_MODELS` list used by Beanie init in `main.py`

---

## Phase 3 — Services

Files: `services/tag_service.py`, `services/card_service.py`, `services/audio_service.py`

- **Task 3.1 — `services/tag_service.py` — create**: `async create_tag(name, parent_slug?)` — slugify name, check uniqueness, insert
- **Task 3.2 — `services/tag_service.py` — read**: `async get_all_tags()` flat list; `async build_tag_tree(tags)` pure function returning nested dict for sidebar display
- **Task 3.3 — `services/card_service.py` — create**: `async create_card(phrase, tag_slugs, audio_filename?)` — for each slug walk the `parent_slug` chain to collect all ancestor slugs, deduplicate, insert Card with full flat `tag_slugs` list
- **Task 3.4 — `services/card_service.py` — list/filter**: `async get_cards(tag_slug?)` — if `tag_slug` given, query `{"tag_slugs": {"$in": [tag_slug]}}`; fetch+sort by `created_at` desc
- **Task 3.5 — `services/card_service.py` — search**: `async search_cards(query)` — case-insensitive regex on `phrase`; sort by `created_at` desc
- **Task 3.6 — `services/card_service.py` — delete**: `async delete_card(card_id)` — delete doc, return deleted audio filename (caller deletes file)
- **Task 3.7 — `services/audio_service.py`**: `async save_audio(file: UploadFile) -> str` — generate UUID filename, write to `frontend/static/content/`; `async delete_audio(filename)`

---

## Phase 4 — Views (Route Handlers)

Files: `views/card_views.py`, `views/tag_views.py`, `views/__init__.py`

- **Task 4.1 — `views/card_views.py` — GET `/`**: fetch all tags + cards (newest first), render `index.html`
- **Task 4.2 — `views/card_views.py` — POST `/cards`**: accept `phrase`, `tag_slugs[]`, optional `audio` file upload; call services; return `partials/card_item.html` fragment (HTMX prepend target)
- **Task 4.3 — `views/card_views.py` — GET `/cards`**: accept optional `?tag_slug=` and `?q=`; return `partials/card_list.html` fragment (HTMX swap target)
- **Task 4.4 — `views/card_views.py` — DELETE `/cards/{card_id}`**: delete card + audio; return 200 empty (HTMX removes element)
- **Task 4.5 — `views/tag_views.py` — GET `/tags`**: return all tags as `partials/tag_tree.html` fragment
- **Task 4.6 — `views/tag_views.py` — POST `/tags`**: create tag; return updated `partials/tag_form.html` (with refreshed parent dropdown) + OOB-swap for tag sidebar
- **Task 4.7 — Wire routers in `main.py`**: include `card_router` and `tag_router`

---

## Phase 5 — Templates

Files in `frontend/templates/`

- **Task 5.1 — `base.html`**: HTML shell with Tailwind CDN, HTMX CDN, `{% block content %}`, `{% block scripts %}`, basic two-column layout slot (use --color-stone-800 for the main background and the teal colors for the accents)
- **Task 5.2 — `index.html`**: extends base; left sidebar (tag tree + tag create form), main area (search bar + card form + card list)
- **Task 5.3 — `partials/card_item.html`**: single card — phrase text, tag pills (render the card's `tag_slugs` directly — no ancestry traversal needed), `<audio>` player if audio present, delete button (`hx-delete`, `hx-target="closest .card-item"`, `hx-swap="outerHTML"`)
- **Task 5.4 — `partials/card_list.html`**: `<div id="card-list">` wrapper containing a for-loop of `card_item.html` includes; this is the HTMX swap target for search/filter
- **Task 5.5 — `partials/card_form.html`**: multi-select tag picker (checkboxes or `<select multiple>`, `name="tag_slugs"`), phrase textarea, audio file input, `hx-post="/cards"`, `hx-target="#card-list"`, `hx-swap="afterbegin"`
- **Task 5.6 — `partials/tag_tree.html`**: recursive nested `<ul>` of tags built from `build_tag_tree`; each item is a plain button/span (no `<a>`) with `hx-get="/cards?tag_slug=..."`, `hx-target="#card-list"`
- **Task 5.7 — `partials/tag_form.html`**: inline form — tag name input, parent dropdown (option values are slugs), `hx-post="/tags"`, `hx-target="#tag-tree"`, `hx-swap="outerHTML"`
- **Task 5.8 — `partials/search_bar.html`**: `<input>` with `hx-get="/cards"`, `hx-trigger="input changed delay:300ms"`, `hx-target="#card-list"`, `name="q"`

---

## Phase 6 — Tests

Files in `tests/`

- **Task 6.1 — `tests/conftest.py`**: async pytest fixtures — spin up `mongomock_motor` (or `mongomock`) test client, initialise Beanie with test documents, yield client, teardown
- **Task 6.2 — `tests/test_tag_service.py`**: test `create_tag` (with and without parent_slug), `get_all_tags`, `build_tag_tree`
- **Task 6.3 — `tests/test_card_service.py`**: test `create_card` (verify ancestor slugs are stored), `get_cards` (date order), `get_cards` with tag_slug filter, `search_cards`, `delete_card`
- **Task 6.4 — `tests/test_views.py`**: `httpx.AsyncClient` smoke tests — GET `/` returns 200, POST `/cards` returns fragment, GET `/cards?q=` returns fragment, DELETE `/cards/{id}` returns 200
