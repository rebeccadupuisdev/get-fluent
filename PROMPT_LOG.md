# Prompt Log — Get Fluent

A record of AI-assisted development decisions, prompts used, and what was learned.
This log exists to document the human–AI collaboration process honestly.

---

## How to Use This Log

After significant code generation, the agent will automatically append a prefilled entry below.
Complete the last two fields — **Modifications I made** and **What I learned** — once you've
reviewed the output. You don't need to log every small prompt, the agent will judge what
counts as significant.

Entry template:

```markdown
---

### Entry [number] — YYYY-MM-DD
**Section:** <!-- inferred from context -->

**Persona:** <!-- persona name if active — omitted if none -->

**Prompt:** <!-- the developer's request -->

**What was generated:** <!-- one or two sentence description -->

**Modifications I made:** <!-- your input needed -->

**What I learned:** <!-- your input needed (optional) -->
```

---

## Entries

---

### Entry 003 — 2026-03-06

**Section:** Project Scaffold (Phase 1)

**Prompt:** Start @.cursor/plans/get_fluent_app_build.plan.md with Phase 1

**What was generated:** All five Phase 1 tasks completed: `requirements.txt` with all dependencies, `pyproject.toml` with Ruff config (line-length 88, py311, double quotes, space indent), `pytest.ini` (asyncio_mode=auto, testpaths=tests), the full directory skeleton (`models/`, `views/`, `services/`, `tests/`, `frontend/static/content/`, `frontend/templates/partials/`) with `__init__.py` files, and a `main.py` skeleton with lifespan Beanie init, StaticFiles mount, Jinja2Templates, and commented-out router includes.

**Modifications I made:** 

**What I learned:** 

---

### Entry 002 — 2026-03-06

**Section:** Architecture / Project Planning

**Prompt:** Can you change the tags for a flat list without links? When we add a tag to a card, we add all the ancestors as plain string to simplify filtering cards by tag

**What was generated:** Updated the build plan to replace Beanie `link[Tag]` references with a flat string design: `Tag` now has `parent_slug: str | None` instead of a DB link, and `Card` stores `tag_slugs: list[str]` (all ancestor slugs included at creation time). Removed `get_descendant_ids` from the service layer since filtering becomes a simple `$in` query.

---

### Entry 001 — 2026-03-06

**Section:** Architecture / Project Planning

**Prompt:** Create a plan for the Get Fluent app for language learning: create phrase cards, attach audio files, search cards and categorize them by tags. Display the cards by created_date reversed. We can nest tags, and we show all the tags on each card. Create a granular plan with separation of backend and frontend, keep the tasks small to help with code verification.

**What was generated:** A full 35-task build plan across 6 phases (scaffold, models, services, views, templates, tests), saved to `.plans/get_fluent_app_build.plan.md`. Includes an architecture diagram, data model decisions (nested tags via parent pointer, Beanie `Link` references), and detailed HTMX interaction patterns for each route.

**Modifications I made:**

- Changed `Optional[{type}]` for `{type} | None`
- Changed `List[]` to `list[]`

