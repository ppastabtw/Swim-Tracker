# Swim Tracker — Implementation Plan

## Overview

A full-stack web app for scraping, tracking, and analyzing swim times for North American swimmers (high school through professional/Olympic). The system automatically collects data from multiple sources, stores it in a unified database, and exposes it through a REST API consumed by a React frontend.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Django 5 + Django REST Framework |
| Task queue | Celery 5 + Celery Beat |
| Message broker | Redis 7 |
| Database | PostgreSQL 16 |
| Frontend | React + Vite + TypeScript |
| Server state | TanStack Query (React Query v5) |
| UI state | Zustand |
| Routing | React Router v6 |
| Charts | Recharts |
| Styling | Tailwind CSS |
| Containerization | Docker + Docker Compose |

---

## Data Sources

| Source | Library | Coverage | Notes |
|---|---|---|---|
| SwimCloud | `pip install SwimScraper` | US college/club, rosters, recruiting | Primary source |
| SwimRankings.net | `pip install swimrankingsscraper` | International athletes, meet results | Secondary source |
| FINA / World Aquatics | `swimset` (GitHub: adghayes/swimset) | Olympic + World Championship historical data | Scrapy-based, one-time import |
| USA Swimming SWIMS | `swimulator` (GitHub: alexkgrimes/swimulator) | USA Swimming database | Selenium-based, requires headless Chrome |

---

## Repository Structure

```
swim-tracker/
├── docker-compose.yml
├── docker-compose.override.yml       # dev-only overrides
├── .env.example
├── .env                              # gitignored
├── IMPLEMENTATION_PLAN.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── manage.py
│   │
│   ├── config/                       # Django project package
│   │   ├── __init__.py
│   │   ├── celery.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── settings/
│   │       ├── base.py
│   │       ├── development.py
│   │       └── production.py
│   │
│   ├── apps/
│   │   ├── swimmers/                 # Core domain models
│   │   │   ├── models.py
│   │   │   ├── admin.py
│   │   │   └── migrations/
│   │   ├── scraping/                 # Celery tasks + job tracking
│   │   │   ├── models.py
│   │   │   ├── tasks.py
│   │   │   └── admin.py
│   │   ├── api/                      # DRF viewsets + serializers
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   └── filters.py
│   │   └── analytics/                # Phase 3 — placeholder for now
│   │       └── __init__.py
│   │
│   └── scrapers/                     # Adapter layer (not a Django app)
│       ├── __init__.py
│       ├── base.py
│       ├── swimcloud.py
│       ├── swimrankings.py
│       ├── swimset.py
│       └── usaswimming.py
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api/                      # Axios client + query functions
        │   ├── client.ts
        │   ├── swimmers.ts
        │   ├── meets.ts
        │   ├── rankings.ts
        │   └── scraping.ts
        ├── types/                    # TypeScript interfaces
        │   ├── swimmer.ts
        │   ├── meet.ts
        │   ├── time.ts
        │   └── scraping.ts
        ├── hooks/                    # useQuery wrappers
        │   ├── useSwimmer.ts
        │   ├── useSwimmerTimes.ts
        │   ├── useMeet.ts
        │   └── useRankings.ts
        ├── components/
        │   ├── ui/                   # Reusable primitives
        │   ├── TimeDisplay.tsx
        │   ├── EventBadge.tsx
        │   ├── SwimmerCard.tsx
        │   ├── TimesTable.tsx
        │   ├── ProgressionChart.tsx
        │   └── ScrapeJobStatus.tsx
        ├── pages/
        │   ├── HomePage.tsx
        │   ├── SwimmerSearchPage.tsx
        │   ├── SwimmerProfilePage.tsx
        │   ├── MeetPage.tsx
        │   ├── RankingsPage.tsx
        │   └── AdminToolsPage.tsx
        └── store/
            └── uiStore.ts
```

---

## Docker Services

```yaml
# Six services — all share the same network

db:
  image: postgres:16-alpine
  # stores all application data

redis:
  image: redis:7-alpine
  # Celery broker + result backend

backend:
  build: ./backend
  command: python manage.py runserver 0.0.0.0:8000
  # Django dev server, mounts ./backend as volume for hot reload

celery_worker:
  build: ./backend          # same image as backend
  command: celery -A config worker -l info
  # runs scrape tasks asynchronously

celery_beat:
  build: ./backend          # same image as backend
  command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
  # triggers scheduled tasks (nightly scrapes, etc.)

frontend:
  build: ./frontend
  command: npm run dev
  # Vite dev server on port 5173
```

**Key design decision:** `celery_worker` and `celery_beat` use the exact same Docker image as `backend`. They are the same codebase — only the startup command differs. This prevents environment drift.

---

## Environment Variables (`.env.example`)

```env
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_DB=swimtracker
POSTGRES_USER=swim
POSTGRES_PASSWORD=swim
DATABASE_URL=postgres://swim:swim@db:5432/swimtracker

# Redis / Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

# Frontend
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## Backend Dependencies (`requirements.txt`)

```
Django>=5.0
djangorestframework>=3.15
django-filter
django-cors-headers
drf-spectacular              # OpenAPI schema generation
celery[redis]>=5.3
django-celery-beat           # DB-backed scheduler
django-celery-results        # Stores task results in PostgreSQL
psycopg[binary]>=3.1
redis>=5.0
python-decouple              # .env management
gunicorn

# Scraping
SwimScraper
swimrankingsscraper
scrapy
selenium
webdriver-manager
openpyxl
```

---

## Database Schema

### `swimmers` app

#### `Swimmer`
| Field | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `full_name` | CharField(255) | |
| `birth_year` | IntegerField | nullable |
| `gender` | CharField(10) | `'male'`, `'female'`, `'unknown'` |
| `nationality` | CharField(3) | ISO 3166-1 alpha-3 |
| `created_at` | DateTimeField | auto |
| `updated_at` | DateTimeField | auto |

#### `SwimmerSource`
Links a swimmer to their ID on each external platform. Critical for deduplication.

| Field | Type | Notes |
|---|---|---|
| `swimmer` | FK → Swimmer | |
| `source` | CharField(20) | `'swimcloud'`, `'swimrankings'`, `'usaswimming'`, `'fina'` |
| `external_id` | CharField(255) | The source platform's own ID |
| `profile_url` | URLField | nullable |
| `last_scraped_at` | DateTimeField | nullable |
| `raw_data` | JSONField | Full raw payload — preserved for debugging/reprocessing |

Unique constraint: `(source, external_id)`

#### `Team`
| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | |
| `name` | CharField(255) | |
| `short_name` | CharField(50) | |
| `team_type` | CharField(20) | `'high_school'`, `'club'`, `'college'`, `'national'` |
| `country` | CharField(3) | |
| `state` | CharField(10) | nullable, US state |

#### `SwimmerTeamMembership`
| Field | Type | Notes |
|---|---|---|
| `swimmer` | FK → Swimmer | |
| `team` | FK → Team | |
| `season_year` | IntegerField | e.g. `2024` = 2023-24 season |
| `is_current` | BooleanField | |

Unique constraint: `(swimmer, team, season_year)`

#### `Meet`
| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | |
| `name` | CharField(255) | |
| `start_date` | DateField | |
| `end_date` | DateField | |
| `course` | CharField(3) | `'SCY'`, `'SCM'`, `'LCM'` |
| `meet_type` | CharField(30) | `'dual'`, `'invitational'`, `'conference'`, `'championship'`, `'olympic'` |
| `location_city` | CharField(100) | |
| `location_state` | CharField(10) | nullable |
| `location_country` | CharField(3) | |
| `source` | CharField(20) | which scraper found this meet |
| `external_id` | CharField(255) | nullable |

Unique constraint: `(source, external_id)`

#### `Event`
| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | |
| `distance` | IntegerField | in meters (SCY stored with `course` on Meet) |
| `stroke` | CharField(20) | `'freestyle'`, `'backstroke'`, `'breaststroke'`, `'butterfly'`, `'individual_medley'` |
| `relay` | BooleanField | default False |
| `gender` | CharField(10) | |

Unique constraint: `(distance, stroke, relay, gender)`

#### `SwimTime` ← The central table
| Field | Type | Notes |
|---|---|---|
| `id` | AutoField | |
| `swimmer` | FK → Swimmer | |
| `meet` | FK → Meet | |
| `event` | FK → Event | |
| `time_seconds` | DecimalField(10, 4) | stored as seconds — e.g. `105.2300` for 1:45.23 |
| `time_display` | CharField(20) | original string — e.g. `'1:45.23'` |
| `heat` | IntegerField | nullable |
| `lane` | IntegerField | nullable |
| `place` | IntegerField | nullable, within event |
| `dq` | BooleanField | default False |
| `splits` | JSONField | nullable — `[{distance: 50, time_seconds: 26.45}, ...]` |
| `source` | CharField(20) | |
| `scraped_at` | DateTimeField | auto |

Unique constraint: `(swimmer, meet, event, time_seconds)` — prevents duplicate ingestion
Index: `(swimmer_id, event_id, time_seconds)` — powers best-times queries fast

#### `RecruitingProfile`
| Field | Type | Notes |
|---|---|---|
| `swimmer` | OneToOneField → Swimmer | |
| `graduation_year` | IntegerField | nullable |
| `high_school` | CharField(255) | nullable |
| `home_state` | CharField(10) | nullable |
| `verbal_commit_date` | DateField | nullable |
| `signed_date` | DateField | nullable |
| `committed_to_team` | FK → Team | nullable |
| `power_index` | DecimalField(6, 2) | nullable, from SwimCloud |
| `last_updated` | DateTimeField | |

---

### `scraping` app

#### `ScrapeJob`
Tracks every scrape operation — manually triggered or scheduled.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `job_type` | CharField(50) | `'swimmer_times'`, `'team_roster'`, `'meet_results'`, `'bulk_import'` |
| `source` | CharField(20) | which scraper was used |
| `status` | CharField(20) | `'pending'`, `'running'`, `'success'`, `'failed'`, `'partial'` |
| `parameters` | JSONField | what was passed to the scraper |
| `result_summary` | JSONField | nullable — counts of records created/updated |
| `error_detail` | TextField | nullable |
| `celery_task_id` | CharField(255) | nullable |
| `triggered_by` | CharField(20) | `'schedule'`, `'api'`, `'admin'` |
| `created_at` | DateTimeField | auto |
| `started_at` | DateTimeField | nullable |
| `completed_at` | DateTimeField | nullable |

#### `ScrapeJobLog`
| Field | Type | Notes |
|---|---|---|
| `job` | FK → ScrapeJob | |
| `level` | CharField(10) | `'info'`, `'warning'`, `'error'` |
| `message` | TextField | |
| `timestamp` | DateTimeField | auto |
| `extra` | JSONField | nullable, structured context |

---

## Time Storage Convention

> **Always store times as `DecimalField` in seconds.**

- `1:45.23` → stored as `105.2300`
- `26.45` → stored as `26.4500`

This makes sorting, range queries, and arithmetic trivially correct across courses and events.

Provide utility functions in `backend/utils/time.py`:

```python
def seconds_to_display(t: Decimal) -> str:
    # 105.23 → "1:45.23"

def display_to_seconds(s: str) -> Decimal:
    # "1:45.23" → Decimal("105.2300")
```

---

## Scraper Adapter Architecture

The `scrapers/` directory is **not a Django app** — it has no models, views, or URLs. It's a pure Python adapter layer that wraps each external library behind a common interface.

### `scrapers/base.py`

```python
class BaseSwimScraper:
    source_name: str

    def search_swimmer(self, name: str, **kwargs) -> list[dict]: ...
    def get_swimmer_times(self, external_id: str) -> dict: ...
    def get_team_roster(self, team_id: str) -> list[dict]: ...
    def get_meet_results(self, meet_id: str) -> dict: ...

# Normalized return contract for get_swimmer_times:
# {
#   'swimmer': {'name': str, 'birth_year': int|None, 'gender': str},
#   'meets': [
#     {
#       'name': str, 'date': str, 'course': str,
#       'times': [{'event': str, 'distance': int, 'stroke': str, 'time': str, 'place': int|None}]
#     }
#   ]
# }
```

### `scrapers/swimcloud.py`
Wraps `SwimScraper`. Because its documentation is sparse, inspect its API interactively first:
```bash
python -c "import SwimScraper; help(SwimScraper)"
```
Then fill in the exact method calls in the adapter.

### `scrapers/swimrankings.py`
Wraps `swimrankingsscraper`. API surface is small:
```python
from swimrankingsscraper import SwimrankingsScraper
client = SwimrankingsScraper()
athlete = client.get_athlete(athlete_id)
meets = athlete.list_meets()
```

### `scrapers/swimset.py`
The swimset data is **historical** (FINA/Olympics) — not live. Implementation:
1. Clone the repo and run the Scrapy spider once to get JSON output
2. Write a management command: `python manage.py import_swimset --file results.json`
3. This is a one-time import, not a recurring scrape

### `scrapers/usaswimming.py`
Based on swimulator's approach. Requires headless Chrome in Docker:
- Use `webdriver-manager` to handle driver installation
- The `celery_worker` Dockerfile needs Chromium installed
- Downloads Excel files, parse with `openpyxl`

---

## REST API (`/api/v1/`)

### Swimmers

| Method | Endpoint | Description |
|---|---|---|
| GET | `/swimmers/` | List/search swimmers — filterable by name, gender, nationality, team |
| GET | `/swimmers/:id/` | Swimmer detail |
| GET | `/swimmers/:id/times/` | All times — filterable by event, course, date range |
| GET | `/swimmers/:id/best_times/` | Best time per event + course combination |
| GET | `/swimmers/:id/progression/:event/` | Time series for a single event (for charting) |
| GET | `/swimmers/:id/meets/` | All meets a swimmer competed in |

### Meets

| Method | Endpoint | Description |
|---|---|---|
| GET | `/meets/` | List meets — filterable by name, date range, course, type |
| GET | `/meets/:id/` | Meet detail |
| GET | `/meets/:id/results/` | All results — filterable by event, gender |
| GET | `/meets/:id/events/` | Events held at this meet |

### Teams

| Method | Endpoint | Description |
|---|---|---|
| GET | `/teams/` | List teams |
| GET | `/teams/:id/` | Team detail |
| GET | `/teams/:id/roster/` | Current roster |
| GET | `/teams/:id/recruiting/` | Recruiting profiles |

### Rankings

| Method | Endpoint | Description |
|---|---|---|
| GET | `/rankings/` | Top times — required params: `event`, `course`, `gender`. Optional: `date_after`, `limit` (default 100) |

### Scraping (auth required)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/scrape/swimmer/` | Trigger swimmer scrape by name or external ID |
| POST | `/scrape/team/` | Trigger team roster scrape |
| POST | `/scrape/meet/` | Trigger meet result scrape |
| GET | `/scrape/jobs/` | List recent scrape jobs |
| GET | `/scrape/jobs/:id/` | Job detail + logs |
| POST | `/scrape/jobs/:id/retry/` | Retry a failed job |

### Key Serializers

**`SwimmerListSerializer`** — lightweight, for list views:
```
id, full_name, gender, nationality, current_team_name
```

**`SwimmerDetailSerializer`** — full detail:
```
...all fields... + sources[] + current_team + recruiting_profile
```

**`SwimTimeSerializer`**:
```
id, event{distance, stroke}, meet{name, date, course}, time_display, time_seconds, splits[], place
```

**`ProgressionSerializer`** — chart-ready:
```
event, course, data_points: [{date, time_seconds, time_display, meet_name}]
```

---

## Celery Tasks (`apps/scraping/tasks.py`)

```python
@shared_task
def scrape_swimmer_by_id(source: str, external_id: str, job_id: str)
# Calls adapter → normalizes → ingests to DB → updates ScrapeJob

@shared_task
def scrape_team_roster(source: str, team_id: str, job_id: str)
# Gets roster → fans out to scrape_swimmer_by_id.delay() per swimmer

@shared_task
def scrape_meet_results(source: str, meet_id: str, job_id: str)
# Gets meet results → ingests all times

@shared_task
def nightly_update_active_swimmers()
# Finds swimmers not scraped in 24h → fans out to scrape_swimmer_by_id in batches of 50

@shared_task
def nightly_update_college_teams()
# All college teams → fans out to scrape_team_roster

@shared_task
def weekly_rankings_refresh()
# Fetches fresh top-100 times per major event from SwimCloud

@shared_task
def import_swimset_data()
# One-time or annual — ingests FINA/Olympic historical data
```

### Periodic Schedule (via `django-celery-beat`)

| Task | Schedule | Notes |
|---|---|---|
| `nightly_update_active_swimmers` | Daily 2:00 AM ET | Stagger to spread DB load |
| `nightly_update_college_teams` | Daily 3:00 AM ET | After swimmer update |
| `weekly_rankings_refresh` | Sunday 1:00 AM ET | |
| `import_swimset_data` | Manual / annual | FINA historical data |

### Rate Limiting + Retry Strategy

All scraper tasks must:
- Rate limit: `rate_limit='10/m'` for SwimCloud, `rate_limit='5/m'` for SwimRankings
- Auto-retry: `max_retries=3`, exponential backoff (`countdown = 60 * 2 ** retries`)
- Log all retries to `ScrapeJobLog`
- On final failure: set `ScrapeJob.status = 'failed'`, notify via `mail_admins()`

---

## Frontend Pages

| Route | Page | Key components |
|---|---|---|
| `/` | Home | Featured swimmers, recent meets, stats banner |
| `/swimmers` | Swimmer Search | Search bar, filter panel, `SwimmerCard` grid |
| `/swimmers/:id` | Swimmer Profile | Best times table, `ProgressionChart` per event |
| `/swimmers/:id/times` | Full Time History | `TimesTable` with sort/filter |
| `/meets` | Meet Browser | Date-sorted list, course/type filters |
| `/meets/:id` | Meet Results | Event tabs, results per event |
| `/rankings` | Rankings Explorer | Event + course + gender selectors, top-N table |
| `/admin-tools` | Admin (auth-gated) | Scrape trigger form, `ScrapeJobStatus` polling |

### Frontend Architecture Decisions

- **React Query** for all server state — caching, background refetch, loading/error states
- **Zustand** only for UI state (active filters, selected tabs)
- **Recharts** for progression charts — lightweight and React-native
- **Tailwind CSS** for styling
- Scrape job polling: use `refetchInterval: 2000` on the job status query, stop when status is `'success'` or `'failed'`
- Type safety: generate TypeScript interfaces from DRF's OpenAPI schema using `drf-spectacular` + `openapi-typescript`

---

## Implementation Phases

### Phase 1 — Foundation (Week 1)
**Goal:** All 6 Docker services start and connect. Django admin is accessible. Celery connects to Redis.

Steps:
1. Create `docker-compose.yml` with all 6 services
2. Create `backend/Dockerfile` and `frontend/Dockerfile`
3. Scaffold Django project: `django-admin startproject config backend/`
4. Create `swimmers` and `scraping` apps
5. Define all models in `swimmers/models.py` and `scraping/models.py`
6. Run first migration
7. Install `django-celery-beat` + `django-celery-results`, configure in settings
8. Register all models in Django admin with list filters
9. Verify: Celery worker connects to Redis, Beat starts, admin loads at `localhost:8000/admin`

---

### Phase 2 — Scraper Adapters (Week 2)
**Goal:** Can scrape a swimmer's times from at least one source via a management command.

Steps:
1. Create `scrapers/base.py` with the abstract interface
2. `pip install SwimScraper` → inspect its API interactively → implement `scrapers/swimcloud.py`
3. Write `scrapers/normalizers.py` — pure functions that map raw scraper output to Django model kwargs
4. Write a management command: `python manage.py scrape_swimmer --source swimcloud --id <id>`
   - This calls the adapter, normalizes output, and saves to DB
   - Test this thoroughly before wiring up Celery
5. Repeat for `swimrankings.py` adapter
6. Write `swimset.py` one-time import command

---

### Phase 3 — Celery Tasks + API (Week 3)
**Goal:** Scrapes run as background tasks. API serves swimmer and time data.

Steps:
1. Move management command logic into `apps/scraping/tasks.py` Celery tasks
2. Add `ScrapeJob` lifecycle tracking inside tasks (pending → running → success/failed)
3. Test tasks directly: `celery -A config call scraping.tasks.scrape_swimmer_by_id`
4. Implement DRF viewsets: `SwimmerViewSet`, `MeetViewSet`, `SwimTimeViewSet`
5. Write serializers for list + detail views
6. Add scrape trigger endpoints (`POST /scrape/swimmer/`)
7. Add `django-filter` filterset classes
8. Test all endpoints with curl or Insomnia

---

### Phase 4 — Frontend (Week 4)
**Goal:** Working UI for browsing swimmers and their times.

Steps:
1. Scaffold with `npm create vite@latest frontend -- --template react-ts`
2. Install dependencies: `axios @tanstack/react-query zustand react-router-dom recharts`
3. Install Tailwind CSS
4. Set up Axios client pointing at `VITE_API_BASE_URL`
5. Implement `SwimmerSearchPage` with search bar + results
6. Implement `SwimmerProfilePage` with best times table
7. Implement `TimesTable` component (sortable, filterable)
8. Implement `ProgressionChart` component using Recharts
9. Implement `AdminToolsPage` with scrape trigger + job status polling

---

### Phase 5 — Scheduling + Polish (Week 5)
**Goal:** Scrapes run automatically. Types are in sync. System is end-to-end tested.

Steps:
1. Define Celery Beat periodic schedule via `django-celery-beat` admin
2. Add rate limiting (`rate_limit` on tasks) and retry logic
3. Set up `drf-spectacular` for OpenAPI schema generation
4. Add `openapi-typescript` npm script to generate frontend types from schema
5. End-to-end test: Beat fires → `ScrapeJob` created → adapter runs → data ingested → API returns it → frontend shows it
6. Add error monitoring to Django admin (failed jobs dashboard)

---

### Phase 6 — Analytics (Future)
**Goal:** Surface meaningful analysis on top of the collected data.

Planned features:
- **Swimmer trends** — rolling best-time improvement rate, season-over-season progression
- **Event correlations** — how strongly does 100 Free predict 200 Free performance?
- **Age/grade-adjusted percentiles** — where does a swimmer rank for their age group?
- **Recruiting fit score** — how do a swimmer's times compare to a target college program's roster?
- **Taper detection** — identify significant time drops across meets (split analysis)
- **Team aggregates** — average times, depth charts, season comparisons

Infrastructure already designed for this:
- Separate `analytics` Celery queue
- `analytics/` Django app (placeholder exists)
- `/api/v1/analytics/` URL namespace reserved
- Store pre-computed stats as `JSONField` on `Swimmer` or in a `SwimmerStats` model to avoid real-time aggregation
- Consider swapping `postgres:16` for `timescale/timescaledb:latest-pg16` (zero app code changes, major time-series query performance gain) when `SwimTime` table exceeds a few million rows

---

## Critical Files Reference

| File | Why it matters |
|---|---|
| `docker-compose.yml` | Foundation — all local dev depends on this being right |
| `backend/apps/swimmers/models.py` | Central schema — every other component depends on this |
| `backend/scrapers/base.py` | The contract that decouples Django tasks from scraping libraries |
| `backend/scrapers/normalizers.py` | The seam where raw data becomes structured records — test heavily |
| `backend/apps/scraping/tasks.py` | Where adapters, ORM ingestion, and job lifecycle all meet |
| `backend/config/celery.py` | Celery app config — wires Django settings, broker, Beat scheduler |
| `frontend/src/api/client.ts` | Single Axios instance — base URL, auth headers, interceptors |

---

## Deduplication Strategy

Getting duplicates wrong means corrupted data that's hard to clean up. Follow this logic:

**For Swimmers:**
1. Query `SwimmerSource` by `(source, external_id)` — exact match, already in DB
2. If not found: check for `full_name + birth_year` match as fuzzy fallback
3. If still no match: create new `Swimmer` + new `SwimmerSource`

**For SwimTimes:**
- The unique constraint `(swimmer, meet, event, time_seconds)` handles exact dedup automatically
- DQ times are stored as separate records with `dq=True`

**For Meets:**
- Deduplicate by `(source, external_id)`
- Cross-source meets (same championship appearing in SwimCloud + FINA data) — handle with a `MeetAlias` table in Phase 6

---

## Notes on Scraping Library Quirks

- **SwimScraper**: Poorly documented. Always `help(SwimScraper)` first before building the adapter.
- **swimrankingsscraper**: Alpha quality (v0.1.6). Small API surface, mostly stable. International data only.
- **swimset**: An R + Scrapy project. The Scrapy spider outputs JSON. Treat as a one-time data import, not a live scraper.
- **swimulator**: Abandoned reference code. Adapt its Selenium approach rather than importing it directly. The `celery_worker` Docker container needs Chromium + Chromedriver — add to its Dockerfile.
