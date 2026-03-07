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

### Entry 023 — 2026-03-07
**Section:** Frontend / Templates

**Persona:** code.frontend.optimize

**Prompt:** Fix all the bugs that doesn't rely on a change to the backend, give me the updated summary after the changes

**What was generated:** Applied four frontend-only fixes from the prior audit: guarded `card_form.html` reset behind `event.detail.successful`; added `hx-disabled-elt` to submit buttons on both the card form and tag modal form; removed the dead edit button stub and the native `hx-confirm` dialog from `card_item.html`; added an explanatory comment to `tag_tree.html` clarifying the dual-purpose `hx-swap-oob` pattern.

**Modifications I made:**
- Asked to put back the edit button, gonna be implemented next

---

### Entry 022 — 2026-03-07
**Section:** Frontend / Templates

**Persona:** code.frontend.optimize

**Prompt:** Can you check the code?

**What was generated:** Full frontend audit of all HTMX + Tailwind + Jinja2 templates, identifying 7 issues across correctness, UX, and code quality — including a wrong `hx-target` on the delete-empty-tags button, unconditional form reset on failure, a wired-but-empty edit button, missing `hx-indicator` usage, stale card count, native `confirm()` inconsistency, and an `hx-swap-oob` smell on initial render.

---

### Entry 021 — 2026-03-07
**Section:** Tests / Services

**Persona:** test.generate

**Prompt:** Based on the audit, apply fixes to the tests

**What was generated:** Added 13 new tests across test_card_service.py, test_tag_service.py, and test_views.py covering regex metacharacter safety, malformed IDs, audio upload, empty tag names, nested tag counts, empty query behaviour, q/tag_slug precedence, and error paths at the view layer. Fixed card_service.search_cards to escape regex input, card_service.delete_card to catch Pydantic ValidationError on malformed IDs, and tag_service.create_tag to reject empty or whitespace-only names.

---

### Entry 020 — 2026-03-07
**Section:** Tests

**Persona:** test.audit

**Prompt:** Can you check the tests?

**What was generated:** Full audit of all four test files (test_card_service, test_tag_service, test_views, test_audio_service) identifying coverage gaps, brittle assertions, unhandled error paths, and untested route branches — categorised by priority.

---

### Entry 019 — 2026-03-07
**Section:** Tests

**Persona:** test.generate

**Prompt:** Create tests for not yet tested functions

**What was generated:** Added 30 new tests across four files: `test_tag_service.py` (covering `delete_empty_tags`, `get_valid_parent_tags`, `build_tag_tree` with counts, and `create_tag` error paths for nonexistent/too-deep parents), `test_card_service.py` (covering `get_card_counts_by_tag`), a new `test_audio_service.py` (covering `save_audio` and `delete_audio` with filesystem mocking via `monkeypatch`), and `test_views.py` (covering `DELETE /tags/empty` and the `POST /tags` duplicate-tag error response). All 67 tests pass.

---

### Entry 018 — 2026-03-07
**Section:** Tags / tag modal form

**Prompt:** When creating a new tag that already exists, show an error message in the modal, currently we have a 422 Unprocessable Entity error response

**What was generated:** Fixed the duplicate-tag error flow by returning HTTP 200 instead of 422 from the error branch in `create_tag`, added `id="tag-error"` to the error div in `tag_modal_form.html`, and updated the `hx-on::after-request` handler to only close the modal when no error element is present in the DOM.

---

### Entry 017 — 2026-03-07
**Section:** Tags / sidebar filter

**Prompt:** When deleting tags, if a deleted tag was currently selected for filtering, the All cards button should become selected with the main view showing all cards

**What was generated:** Added an `htmx:afterSettle` event listener in `index.html` that checks whether any `.tag-filter-btn` still has the `is-active` class after every HTMX settle. If none do (i.e. the active tag was deleted), it programmatically triggers a click on `#btn-all-cards`, restoring the active highlight and reloading the full card list.

---

### Entry 016 — 2026-03-07
**Section:** Tags / sidebar

**Prompt:** Add a button under the + New tag in the same style, the text for the button is Delete empty tags and it would delete all tags not attached to a card, ask the user if they are sure before deleting the tags, make the button in the amber colorway

**What was generated:** Added a "Delete empty tags" amber-styled sidebar button that fires `hx-delete="/tags/empty"` with `hx-confirm` for a browser confirmation prompt. Added `delete_empty_tags` to `tag_service.py` and a `DELETE /tags/empty` route to `tag_views.py`. Made `hx-swap-oob` conditional in `tag_tree.html` so the delete endpoint can return a plain `outerHTML`-swappable fragment without OOB conflicts.

**Modifications I made:**
- Changed the confirmation for a modal in-app

---

### Entry 015 — 2026-03-07
**Section:** Tags / tag service

**Prompt:** When adding a second level tag we have an 422 Unprocessable Entity error, there's no error when adding a 1st level tag or a root tag

**What was generated:** Fixed the `create_tag` validation in `tag_service.py` — the check `if parent.parent_slug is not None` was incorrectly blocking level-2 tag creation because it fired for level-1 parents (which have a root parent). Now it looks up the grandparent and only raises if the grandparent also has a parent, correctly restricting only depth-3 creation.

---

### Entry 014 — 2026-03-07
**Section:** Tags / modal form

**Prompt:** The dropdown currently shows all levels of tags, it shouldn't show the level 2 tags

**What was generated:** Fixed the `index` route in `card_views.py` to pass `get_valid_parent_tags()` instead of `get_all_tags()` as the `tags` context variable, so the New Tag modal dropdown excludes level-2 tags that cannot be parents.

---

### Entry 013 — 2026-03-07
**Section:** Tags / backend validation

**Prompt:** Change the backend to prevent the creation of a 3rd level tag, we only support root -> level 1 -> level 2

**What was generated:** Added depth validation to `create_tag` in `tag_service.py` — raises `ValueError` if the chosen parent already has a parent of its own. Updated `tag_views.py` to catch `ValueError` and return a 422 with the error message in context. Added an inline error banner to `tag_modal_form.html` and filtered the parent dropdown to show only root tags (preventing the invalid selection at the UI level too).

---

### Entry 012 — 2026-03-07
**Section:** Sidebar / frontend design

**Prompt:** Check the prototype in @prototype/ to replicate the design for the sidebar, but use the mono font for the tags and the serif font for the titles

**What was generated:** Updated `index.html` sidebar to match the prototype's structure — teal icon header, `font-serif` title, `bg-stone-900` sidebar vs `bg-stone-800` main content, updated active state to teal background without border-left, and "New Tag" footer with border-t. Updated `tag_tree.html` to apply `font-mono` to all tag names and count badges, replaced `border-l` child indentation with `pl-8` + `└` connector, and added a `depth` parameter to the macro to differentiate root vs child rendering.

---

### Entry 011 — 2026-03-07
**Section:** Card item partial / frontend design

**Prompt:** Check this code to replicate the design for the cards @phrase-cards.html, I want to play the audio when we click on the card, show an edit and delete button on hover, use the same fonts for the phrase and the tags

**What was generated:** Redesigned `card_item.html` to match the reference SoundCards design — DM Serif Display for the phrase, DM Mono for tags with an SVG tag icon, teal pill styling, and a "no audio attached" note. Added audio-on-click via a `toggleCardAudio` JS function in `index.html` with `playing` CSS class (teal ring). Edit and delete action buttons now appear on hover, positioned absolutely in the top-right corner. Google Fonts and Tailwind `fontFamily` config added to `base.html`.

---

### Entry 010 — 2026-03-07
**Section:** Templates (Phase 5)

**Prompt:** Continue @.cursor/plans/get_fluent_app_build.plan.md with Phase 5, then update the tests if necessary

**What was generated:** Eight Jinja2 templates implementing the full UI: `base.html` (Tailwind + HTMX CDN, stone-800 background, teal accents), `index.html` (two-column layout with tag sidebar and card main area), and six partials — `card_item.html`, `card_list.html`, `card_form.html`, `tag_tree.html` (recursive macro), `tag_form.html` (OOB-swap pattern for sidebar tree refresh), and `search_bar.html` (debounced HTMX input). All 38 tests passed without changes.

**What I learned:**
- The agent must have more guidance for the design, I'll experiment with different workflow for this in the future

---

### Entry 009 — 2026-03-07
**Section:** Views / Tests

**Prompt:** Continue @.cursor/plans/get_fluent_app_build.plan.md with Phase 4, then implement the tests from task 6.4

**What was generated:** Implemented all Phase 4 route handlers — `views/card_views.py` (GET `/`, POST `/cards`, GET `/cards`, DELETE `/cards/{card_id}`) and `views/tag_views.py` (GET `/tags`, POST `/tags`) — with a shared `views/deps.py` holding the `Jinja2Templates` instance. Wired both routers into `main.py`. Created minimal Jinja2 template stubs for the five templates needed by the views. Added `tests/test_views.py` with 11 `httpx.AsyncClient` smoke tests covering all routes; all 38 tests across the suite pass.

---

### Entry 008 — 2026-03-07
**Section:** Infrastructure / Database

**Prompt:** Motor is deprecated as of May 2025 in favour of PyMongo's native async API. Should we change something in the project?

**What was generated:** Updated `infrastructure/mongo_setup.py` to replace `motor_asyncio.AsyncIOMotorClient` with PyMongo's `AsyncMongoClient`, and removed `motor` from `requirements.txt`. Beanie 2.0 (released June 2025) already depends on PyMongo's native async API, making Motor a redundant and deprecated dependency.

---

### Entry 007 — 2026-03-06
**Section:** Tests (Phase 6)

**Prompt:** Can you start the @.cursor/plans/get_fluent_app_build.plan.md Phase 6 — Tests with what is already implemented?

**What was generated:** Created `tests/conftest.py` with a `mongomock_motor`-backed async Beanie fixture, `tests/test_tag_service.py` (11 tests covering `create_tag`, `get_all_tags`, and `build_tag_tree`), and `tests/test_card_service.py` (16 tests covering `create_card` ancestor slug expansion, `get_cards`, `search_cards`, and `delete_card`). Added `mongomock-motor` to `requirements.txt`. All 27 tests pass.

**What I learned:**
- Next time I'll add to my starting prompt to implement relevant tests in each phase

---

### Entry 006 — 2026-03-06
**Section:** Services (Phase 3)

**Prompt:** Continue @.cursor/plans/get_fluent_app_build.plan.md with Phase 3

**What was generated:** Three service modules: `services/tag_service.py` (`_slugify`, `create_tag`, `get_all_tags`, `build_tag_tree`), `services/card_service.py` (`_collect_ancestor_slugs`, `create_card`, `get_cards`, `search_cards`, `delete_card`), and `services/audio_service.py` (`save_audio`, `delete_audio`). All Phase 3 tasks marked complete in the plan file.

**Modifications I made:**
- Changed the _slugify function to use python-slugify

---

### Entry 005 — 2026-03-06
**Section:** Configuration / Project Scaffold

**Prompt:** Can you put these main.py (9-10) in a .env file?

**What was generated:** Created `.env` with `MONGO_URI` and `DB_NAME` values, added `python-dotenv` to `requirements.txt`, and updated `main.py` to call `load_dotenv()` and read both values via `os.getenv` with fallback defaults.

**What I learned:**
- I should add using .env as a preference

---

### Entry 004 — 2026-03-06
**Section:** Data Models (Phase 2)

**Prompt:** Continue @.cursor/plans/get_fluent_app_build.plan.md with Phase 2

**What was generated:** Three model files: `models/tag.py` (Beanie `Tag` document with `name`, `slug`, `parent_slug: str | None`), `models/card.py` (Beanie `Card` document with `phrase`, `audio_filename`, `created_at` via `Field(default_factory=...)`, `tag_slugs: list[str]`), and `models/__init__.py` exporting both documents and `DOCUMENT_MODELS` for Beanie init.

**Modifications I made:**
- Added infrastructure folder and moved the DB connection logic

---

### Entry 003 — 2026-03-06

**Section:** Project Scaffold (Phase 1)

**Prompt:** Start @.cursor/plans/get_fluent_app_build.plan.md with Phase 1

**What was generated:** All five Phase 1 tasks completed: `requirements.txt` with all dependencies, `pyproject.toml` with Ruff config (line-length 88, py311, double quotes, space indent), `pytest.ini` (asyncio_mode=auto, testpaths=tests), the full directory skeleton (`models/`, `views/`, `services/`, `tests/`, `frontend/static/content/`, `frontend/templates/partials/`) with `__init__.py` files, and a `main.py` skeleton with lifespan Beanie init, StaticFiles mount, Jinja2Templates, and commented-out router includes.

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

