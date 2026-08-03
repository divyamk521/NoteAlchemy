# NoteAlchemy — SaaS Product Plan

**Version:** 1.0 · **Date:** 2026-08-03 · **Companion to:** `DIAGNOSIS.md`

This is the complete path from the current prototype to a SaaS product with paying customers.
Read `DIAGNOSIS.md` first for the codebase findings this plan builds on.

---

## 0. The recommendation up front

**Build a self-serve B2C/prosumer product first, on a data model that makes institutional B2B a
later expansion rather than a rewrite.**

Rationale: you're a solo builder with a working pipeline and no customers. B2C gets you revenue
and validation in ~8 weeks. Pure B2B institutional selling means 6–12 month sales cycles, SOC 2,
and procurement — before you know whether anyone wants the output. But B2B is where the real
money is (10–50× ACV), so you pay a small tax now — a `tenant_id` on every row, an audit-log
table, and a retention field — to avoid a migration later.

Three decisions to lock before writing code:

| Decision | Answer | Why |
|---|---|---|
| Who holds the API key? | **You do.** | BYO-key means no usage to meter, nothing to price. Non-negotiable for SaaS. |
| Streamlit's role? | **Demo/internal only.** Product is FastAPI + Next.js. | Streamlit has no multi-user model, no auth hooks, no routing, and re-runs the whole script per interaction. |
| Multi-tenant from day 1? | **Yes**, even for single users. | A solo user is a tenant of one. Retrofitting tenancy touches every query. |

---

## 1. What you are actually selling

### 1.1 Product definition

> **NoteAlchemy turns a lecture recording into exam-ready study notes in under 60 seconds.**

Not a transcriber. Not a summarizer. A **study-artifact generator**. The distinction matters
commercially: transcription is a commodity at $0.04/hour, and summaries are free everywhere. What
people pay for is the artifact they actually study from.

### 1.2 The real differentiator — lean on this hard

Your `NotesGenerator` does something most competitors don't: **structure-first scaffolded
generation.** It builds an outline with a strong model, then writes each section deeply with a
fast model, giving every section full-lecture context.

Nearly every competitor does one-shot summarization, which degrades badly past ~20 minutes of
audio — it compresses uniformly and loses the back half. Your approach produces genuinely
*comprehensive* notes: 3,000+ words with tables, code blocks, and per-section depth, not a
bulleted TL;DR.

**Positioning statement:**

> For students and professionals who learn from long-form lectures, NoteAlchemy produces
> complete, structured study notes — not summaries — from any recording in under a minute.

Three pillars: **Depth** (notes you can study from without rewatching) · **Speed** (Groq,
sub-60s) · **Portability** (PDF, DOCX, Markdown, Notion, **Anki**).

### 1.3 ICP — pick one, ruthlessly

| Segment | Pays? | Reachable? | Verdict |
|---|---|---|---|
| **University STEM undergrads** | $9–15/mo, seasonally | Reddit, TikTok, campus reps | **Primary** |
| Grad students / researchers | $15–25/mo | Twitter, lab word-of-mouth | Secondary |
| Professional upskillers (bootcamp, cert prep) | $20–30/mo | LinkedIn, SEO | Secondary — best LTV |
| Corporate L&D | $10/seat, 50+ seats | Outbound only | Phase 5 |
| Universities / disability services | $8–12/seat, 500+ seats | Procurement, 9-month cycle | Phase 5 — **the prize** |

Start with **STEM undergrads**: they have long technical lectures where summaries fail hardest,
they're concentrated and reachable for free, and they generate the word-of-mouth that funds
everything else. Accept the seasonality (revenue dips May–Aug).

### 1.4 Competitive reality — read this before you build

This is a crowded space and you must be honest about it.

| Competitor | Threat | Your counter |
|---|---|---|
| **Google NotebookLM** | **Severe.** Free, Google-backed, excellent | Depth of output artifact; Anki/PDF export; speed; not tied to Google account |
| Otter.ai | Moderate — transcription-first, weak notes | You produce study artifacts, not transcripts |
| Notion AI | Low — general-purpose, no audio pipeline | Purpose-built for lectures |
| Turbolearn / Coconote / StudyFetch | **High** — same wedge, funded, shipping | Output quality; long-lecture handling; price |
| ChatGPT + manual paste | Moderate — free, requires work | Automation, structure, no 25-min ceiling |

**The honest risk:** NotebookLM is free and very good. You cannot win on "AI notes from audio" as
a feature. You win on **artifact quality for long technical content** plus **export fidelity**,
and eventually on **institutional procurement** — which Google will not chase for accessibility
accommodation budgets.

**Validate before Phase 3.** Generate notes for 10 real 50-minute lectures with the current
pipeline (post-Phase 1). Put them side by side with NotebookLM output in front of 20 actual
students. If they don't clearly prefer yours, **fix the output before building billing.** No
amount of SaaS plumbing saves an undifferentiated artifact.

---

## 2. Unit economics

### 2.1 Cost per generation — 50-minute lecture (~10,000 transcript tokens)

Approximate Groq on-demand rates; **verify at groq.com/pricing before pricing anything.**

| Component | Model | Tokens / duration | Cost |
|---|---|---|---|
| Transcription | whisper-large-v3 | 50 min | **$0.0925** |
| Transcription *(alt)* | whisper-large-v3-**turbo** | 50 min | **$0.0333** |
| Outline | llama-3.3-70b | 10k in / 1.5k out | $0.0071 |
| 6 × sections | llama-3.1-8b | 63k in / 12k out | $0.0041 |
| Glossary | llama-3.1-8b | 10k in / 1.2k out | $0.0006 |
| **LLM subtotal** | | | **$0.0118** |
| **Total (large-v3)** | | | **$0.1043** |
| **Total (turbo)** | | | **$0.0451** |

**Transcription is 89% of COGS.** This is the single most important number in the plan, and it
inverts the intuition that LLM calls dominate.

Consequences:

1. **Evaluate whisper-large-v3-turbo immediately.** It halves total COGS. Run a quality
   comparison on 10 lectures; if acceptable, make it the default and reserve large-v3 for a
   "high accuracy" toggle on paid tiers. **This is worth more than every LLM optimization
   combined.**
2. **Cache transcriptions by audio hash, forever.** Re-generating notes from an
   already-transcribed lecture should cost $0.012, not $0.104. Users re-run constantly.
3. **The transcript-resend bug costs $0.0025 (2.4% of COGS).** Fix it for latency, TPM headroom,
   and context ceiling — *not* for margin. It is not a Phase-2 emergency.
4. **Text-paste input has ~9× better margin** than audio. Surface it prominently; users who paste
   YouTube auto-captions cost you almost nothing.

### 2.2 Margin by tier

Assuming whisper-turbo ($0.045/generation) and mixed usage:

| Tier | Price | Quota | COGS @ full use | GM @ full | GM @ typical (40% of quota) |
|---|---|---|---|---|---|
| Free | $0 | 3/mo, ≤30 min | $0.08 | — | Funnel cost |
| **Student** | **$9/mo** | 25/mo, ≤90 min | $1.13 | **87%** | 95% |
| **Pro** | **$19/mo** | 100/mo, ≤3 hr | $4.51 | **76%** | 90% |
| Team | $12/seat, min 5 | 100/seat pooled | $4.51/seat | 62% | 85% |

Healthy SaaS margins even at full quota. With large-v3 instead: Student GM 71%, Pro 45% — still
viable but that's why turbo evaluation is item #1.

### 2.3 Fixed costs and break-even

| Item | Monthly |
|---|---|
| Postgres (Neon/Supabase) | $25 |
| Redis (Upstash) | $10 |
| App hosting (Railway/Fly, 2 services) | $40 |
| Object storage (R2 — no egress fees) | $5 |
| Sentry + PostHog (free tiers initially) | $0 |
| Domain, email (Resend) | $20 |
| **Total** | **~$100** |

**Break-even: ~12 Student subscribers.** That's the whole hurdle. Pick Cloudflare R2 over S3
specifically for zero egress — you'll serve a lot of PDF downloads.

### 2.4 Abuse ceiling — enforce before launch

Worst case per user per month if unguarded: unlimited 3-hour uploads = **$180/user**. Hard
requirements before you expose your own API key to the internet:

- Hard monthly generation quota, enforced **server-side, pre-flight** (not in the UI)
- Max audio duration per tier
- Concurrent-job limit per user (1 free, 3 paid)
- Per-IP signup throttle + email verification (kills free-tier farming)
- A global daily spend circuit-breaker that halts all jobs and pages you

---

## 3. Pricing and packaging

### 3.1 Tiers

**Free — $0.** 3 lectures/mo · ≤30 min · Markdown + TXT export · notes kept 30 days · watermark
on PDF. Purpose: prove output quality. Generous enough to feel the value, tight enough that a
real student converts within a week.

**Student — $9/mo** ($86/yr, 20% off). 25 lectures/mo · ≤90 min · all exports (PDF, DOCX,
Markdown, **Anki**) · unlimited retention · editing · folders. Requires no .edu verification —
don't add friction; the price *is* the segmentation.

**Pro — $19/mo** ($182/yr). 100 lectures/mo · ≤3 hr · priority queue · high-accuracy
transcription toggle · Notion sync · API access · custom note templates.

**Team — $12/seat/mo**, 5 seat minimum. Pooled quota · shared workspace · admin roles · SSO
(Phase 5) · centralized billing.

**Institution — custom** (Phase 5). Per-seat or site license · SAML/SCIM · retention controls ·
DPA · audit logs · LMS integration.

### 3.2 Packaging rules

- **Quota resets monthly, does not roll over.** Simple to explain, simple to enforce.
- **Overage:** don't meter overage on Student — block with an upgrade prompt (predictable bills
  matter to students). On Pro, allow $0.30/extra lecture.
- **Annual = 20% off**, pushed hard at checkout. Cash up front matters at your scale.
- **Anki export is a paid feature.** It's cheap for you and disproportionately loved by the exact
  users who convert.
- **Never meter by minutes or tokens.** "Lectures per month" is the only unit students
  understand. Internal cost tracking stays internal.

---

## 4. Target architecture

### 4.1 Shape

```
                        ┌──────────────────┐
   Browser ────────────▶│  Next.js (Vercel)│   marketing + app UI
                        └────────┬─────────┘
                                 │ REST / SSE
                        ┌────────▼─────────┐
                        │  FastAPI          │  auth middleware, quota
                        │  (api)            │  enqueue, status, exports
                        └───┬──────────┬────┘
                            │          │
              ┌─────────────▼──┐   ┌───▼────────────┐
              │  Postgres      │   │  Redis         │
              │  (source of    │   │  (queue +      │
              │   truth)       │   │   cache)       │
              └────────────────┘   └───┬────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │  Worker (Arq / Celery)      │
                        │   ├─ transcribe (chunked)   │
                        │   ├─ outline                │
                        │   ├─ sections (parallel)    │──▶ Groq API
                        │   ├─ glossary               │
                        │   └─ export                 │
                        └──────────────┬──────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │  R2 / S3  (audio, exports)  │
                        └─────────────────────────────┘
```

### 4.2 Stack choices and rationale

| Layer | Choice | Why this one |
|---|---|---|
| API | **FastAPI** | Your code is already typed + Pydantic. Zero-friction port. |
| Worker | **Arq** (or Celery) | Arq is async-native and tiny; Celery if you want ecosystem. |
| Queue/cache | **Redis** (Upstash) | Doubles as queue backend and transcript cache. |
| DB | **Postgres** (Neon) | Branching DBs make migrations safe. JSONB for notes structure. |
| Frontend | **Next.js + Tailwind + shadcn/ui** | Fast to build, good SEO for the marketing site you need anyway. |
| Auth | **Clerk** (→ WorkOS at Phase 5) | Do not build auth. Clerk has orgs built in. |
| Billing | **Stripe** + Checkout + Customer Portal | Don't build billing UI. Portal handles upgrades/cancels/dunning. |
| Storage | **Cloudflare R2** | Zero egress fees — you serve many PDFs. |
| Errors | **Sentry** | |
| Analytics | **PostHog** | Product analytics + feature flags + session replay in one. |
| Migrations | **Alembic** | |
| Email | **Resend** | |
| CI | **GitHub Actions** | |
| Hosting | **Railway** or **Fly.io** | Deploy API + worker from one repo trivially. |

**What survives from today's code, essentially unchanged:** `src/notes/`, `src/llm/`,
`src/transcription/`, `src/export/`, `config/`. Your layering earns this — the pipeline has no UI
dependency. `src/ui/` and `main.py` become a dev-only demo surface.

### 4.3 Why not just keep Streamlit

- One process serves all sessions → the `os.getpid()` temp-file collision (`DIAGNOSIS.md` §3.1)
  is a *symptom* of a model that has no per-user isolation
- Full script re-runs on every widget interaction — incompatible with long jobs
- No route-level auth, no middleware, no webhooks (Stripe needs one)
- No way to serve a marketing site, pricing page, or SEO content
- Cannot build a mobile app against it

Keep `main.py` working as an internal demo. Do not sell it.

---

## 5. Data model

Multi-tenant from day one. `tenant_id` on every user-owned row.

```sql
-- Tenancy -------------------------------------------------------------
CREATE TABLE tenants (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  kind            TEXT NOT NULL DEFAULT 'personal',   -- personal | team | institution
  plan            TEXT NOT NULL DEFAULT 'free',       -- free | student | pro | team | institution
  stripe_customer_id      TEXT UNIQUE,
  stripe_subscription_id  TEXT,
  plan_renews_at  TIMESTAMPTZ,
  -- Phase 5 knobs, cheap to add now
  retention_days  INT,                                 -- NULL = keep forever
  sso_connection_id TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  external_id     TEXT UNIQUE NOT NULL,               -- Clerk user id
  email           CITEXT NOT NULL,
  role            TEXT NOT NULL DEFAULT 'member',     -- owner | admin | member
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON users (tenant_id);

-- Source material -----------------------------------------------------
-- Keyed by content hash so transcription is never paid for twice.
CREATE TABLE sources (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  kind            TEXT NOT NULL,                      -- upload | youtube | paste
  content_hash    TEXT NOT NULL,                      -- sha256 of audio bytes or text
  storage_key     TEXT,                               -- R2 object key (audio only)
  original_name   TEXT,
  duration_seconds INT,
  byte_size       BIGINT,
  youtube_url     TEXT,
  transcript      TEXT,                               -- populated once, reused forever
  transcript_model TEXT,
  language        TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ON sources (tenant_id, content_hash);

-- Jobs ----------------------------------------------------------------
CREATE TABLE jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES users(id),
  source_id       UUID REFERENCES sources(id),
  idempotency_key TEXT,                               -- dedupe double-submits
  status          TEXT NOT NULL DEFAULT 'queued',
      -- queued | transcribing | outlining | writing | glossary | exporting | done | failed | cancelled
  stage_progress  JSONB NOT NULL DEFAULT '{}',        -- {"sections_done":4,"sections_total":6}
  options         JSONB NOT NULL DEFAULT '{}',        -- glossary, language, template, accuracy
  error_code      TEXT,
  error_message   TEXT,
  attempt         INT NOT NULL DEFAULT 0,
  queued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at      TIMESTAMPTZ,
  finished_at     TIMESTAMPTZ,
  CONSTRAINT jobs_idem UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX ON jobs (tenant_id, status);
CREATE INDEX ON jobs (status, queued_at);

-- Output --------------------------------------------------------------
CREATE TABLE notes (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  source_id       UUID REFERENCES sources(id),
  title           TEXT NOT NULL,
  structure       JSONB NOT NULL,                     -- NotesStructure.model_dump()
  markdown        TEXT NOT NULL,                      -- assembled; user-editable
  markdown_original TEXT NOT NULL,                    -- pristine model output
  word_count      INT NOT NULL,
  folder_id       UUID,
  is_deleted      BOOLEAN NOT NULL DEFAULT false,     -- soft delete, real purge by retention job
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON notes (tenant_id, is_deleted, created_at DESC);

-- Metering ------------------------------------------------------------
-- One row per billable unit of work. This is your COGS ledger AND your quota source.
CREATE TABLE usage_events (
  id              BIGSERIAL PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id         UUID REFERENCES users(id),
  job_id          UUID REFERENCES jobs(id),
  kind            TEXT NOT NULL,                      -- transcription | llm_call | export
  model           TEXT,
  tokens_in       INT,
  tokens_out      INT,
  audio_seconds   INT,
  cost_usd        NUMERIC(12,6) NOT NULL DEFAULT 0,
  billing_period  DATE NOT NULL,                      -- first of month, for fast quota rollup
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON usage_events (tenant_id, billing_period);

-- Compliance ----------------------------------------------------------
CREATE TABLE audit_log (
  id              BIGSERIAL PRIMARY KEY,
  tenant_id       UUID NOT NULL,
  actor_user_id   UUID,
  action          TEXT NOT NULL,                      -- note.deleted, member.invited, plan.changed
  target_type     TEXT,
  target_id       TEXT,
  metadata        JSONB,
  ip              INET,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON audit_log (tenant_id, created_at DESC);
```

**Design notes.** `sources.content_hash` is the whole cost strategy in one column — re-uploading
the same lecture never re-transcribes. `usage_events` serves double duty as COGS ledger and quota
counter (`SELECT count(*) FROM jobs WHERE tenant_id=? AND billing_period=?`). `markdown` vs
`markdown_original` lets users edit while preserving a reset path. `audit_log` costs nothing now
and is a hard procurement requirement later.

---

## 6. API surface

```
POST   /v1/sources/upload-url        → presigned R2 PUT + source_id  (browser uploads direct)
POST   /v1/sources/youtube           → {url} → source_id
POST   /v1/sources/paste             → {text} → source_id

POST   /v1/jobs                      → {source_id, options, idempotency_key} → job
GET    /v1/jobs/{id}                 → status + stage_progress
GET    /v1/jobs/{id}/events          → SSE progress stream
POST   /v1/jobs/{id}/cancel

GET    /v1/notes                     → paginated list (folders, search)
GET    /v1/notes/{id}
PATCH  /v1/notes/{id}                → edit markdown / title / folder
DELETE /v1/notes/{id}                → soft delete
GET    /v1/notes/{id}/export?format=pdf|docx|md|txt|anki|notion

GET    /v1/me                        → user, tenant, plan, quota remaining
POST   /v1/billing/checkout          → Stripe Checkout session
POST   /v1/billing/portal            → Stripe Customer Portal session
POST   /webhooks/stripe              → subscription lifecycle

GET    /healthz  /readyz             → probes
```

**Non-negotiables.** Presigned direct-to-R2 upload (never proxy 200 MB files through FastAPI).
SSE for progress (polling at 60s job durations is wasteful and feels worse). `idempotency_key` on
job creation (users double-click). Quota checked **before** enqueue, with the remaining count in
the 402 response body.

---

## 7. Pipeline redesign

Keep `NotesGenerator`'s logic; change how it's driven.

### 7.1 Job state machine

```
queued → transcribing → outlining → writing → glossary → exporting → done
                            │                                  ↑
                            └──────── failed ──── retry ────────┘
                                        │
                                     cancelled
```

Persist stage transitions to `jobs.status` and `jobs.stage_progress`. A worker crash at "writing,
4/6 sections" must resume from section 5 — **store completed section content in Redis keyed by
`(job_id, section_index)`** so a retry doesn't re-pay for finished work.

### 7.2 Fixes carried from the diagnosis, in priority order

| Change | Why now | Ref |
|---|---|---|
| **Evaluate whisper-turbo** | Halves COGS — biggest single lever | §2.1 |
| **Cache transcript by `content_hash`** | Turns a $0.10 re-run into $0.012 | §2.1 |
| **Parallel section generation** | 4–6× faster; speed *is* the pitch | DIAG §5.1 |
| **Audio chunking >25 MB** | Unblocks 50-min lectures — the core use case | DIAG §5.3 |
| **Unicode TTF for PDF** | Export currently breaks on an em-dash | DIAG §3.4 |
| **UUID temp filenames** | Cross-user data leak | DIAG §3.1 |
| **Narrow retry to transient** | Stop burning 18 doomed calls on a bad key | DIAG §3.2 |
| **Escape LLM output** | Stored XSS once notes are shareable | DIAG §3.3 |
| Transcript excerpting | Latency + TPM headroom (**not** margin) | §2.1 |

### 7.3 Concurrency and rate limits

Parallel sections + parallel audio chunks will hit Groq's TPM/RPM limits. Required:

- A **global token-bucket limiter in Redis** shared across all workers, per model
- Bounded concurrency per job (semaphore, ~4 sections at once)
- `RateLimitError` → exponential backoff **with jitter**, and honour `Retry-After`
- Two queues: `priority` (Pro) and `standard` (Free/Student) — a cheap, real upsell

### 7.4 Quality — the thing that actually sells

SaaS plumbing doesn't matter if the notes are mediocre. Build this in Phase 1:

- **A golden-set eval.** 10 lectures across physics/CS/biology/humanities with reference notes.
  Score coverage, structure quality, hallucination rate. Run on every prompt change. Without
  this you are guessing, and prompt regressions are invisible.
- **Thumbs up/down per section**, stored. This is your training signal and your roadmap.
- **Note templates:** Exam Prep (Q&A + formulas), Deep Notes (current behaviour), Cheat Sheet
  (one page). Cheap to add — different prompts, same pipeline — and a visible reason to pay.

---

## 8. Build plan

### Phase 0 — Make it run · ½ day

Items 1–9 of the diagnosis backlog. Fix the import, the UTF-16 requirements file, the temp-file
collision, the retry scope. Delete `groq_utils.py`, `export_utils.py`, `test_ui.py`, and the
committed artifacts (`test.mp4`, `notes_output.*`, `generated_notes.md`, `Introduction_to_*`).

**Exit:** `streamlit run main.py` works from a clean clone following the README.

---

### Phase 1 — Make it good, and prove it's differentiated · 1 week

Parallel sections · whisper-turbo evaluation · Unicode PDF · real PDF tables · escape LLM output ·
input caps · reconcile config + the ScribeWizard/NoteAlchemy naming · `pyproject.toml` + locked
deps · ~40 pytest unit tests · GitHub Actions (ruff, mypy, pytest, pip-audit) · golden-set eval
harness.

**Exit:** ≤20s for a 50-min lecture. CI green. **20 students shown your notes vs NotebookLM's
prefer yours.** Do not proceed to Phase 3 until that last one is true.

---

### Phase 2 — Make it scale · 1 week

Audio chunking (>25 MB, parallel chunk transcription, overlap dedup) · transcript excerpting ·
Redis token-bucket limiter · transcript caching by content hash · structured JSON logs + Sentry.

**Exit:** a 2-hour lecture completes end-to-end. Repeat generation on the same audio costs
~$0.012.

---

### Phase 3 — Make it a SaaS · 4 weeks

This is the bulk of the work. Order matters — each week depends on the last.

**Week 1 — Backbone.** Monorepo restructure (§9). FastAPI app with health checks. Postgres +
Alembic, full schema from §5. Arq worker. `NotesGenerator` driven by a job row instead of a
function call. Docker Compose for local dev; Dockerfiles for both services.
*Exit: a job submitted via curl completes and writes a `notes` row.*

**Week 2 — Identity and tenancy.** Clerk integration, JWT verification middleware, `tenant_id`
scoping on every query (enforce with a base repository class, not discipline). Presigned R2
uploads. Audit-log writes on mutations.
*Exit: two users cannot see each other's notes — with a test proving it.*

**Week 3 — Money.** `usage_events` written by the worker for every Groq call, with cost. Quota
middleware rejecting pre-enqueue with a 402. Stripe: products, Checkout, Customer Portal,
webhooks (`subscription.updated`, `deleted`, `invoice.payment_failed`). Plan → entitlement map
in one place.
*Exit: you can subscribe with a test card, hit your quota, get blocked, upgrade, get unblocked.*

**Week 4 — Frontend.** Next.js: marketing/pricing page, upload flow, job progress via SSE, notes
library with folders and search, markdown editor, export buttons, billing settings. Deploy API +
worker to Railway, frontend to Vercel. Staging environment.
*Exit: a stranger can sign up, pay, generate notes, and download a PDF without you touching
anything.*

---

### Phase 4 — Make it retain · 2–3 weeks

Anki export (`.apkg` — high delight, low effort) · DOCX export · Notion sync · note templates
(Exam Prep / Cheat Sheet) · thumbs feedback · onboarding with a pre-loaded sample lecture ·
transactional email (welcome, job done, quota warning, dunning) · PostHog funnels · Chrome
extension for one-click YouTube capture (a genuinely strong acquisition loop).

**Exit:** week-4 retention >25%; free→paid conversion >3%.

---

### Phase 5 — Make it enterprise · demand-led, do not pre-build

Trigger: **a named institution asks.** Then: WorkOS SAML/SCIM · admin console (seats, usage,
retention) · configurable retention + hard purge job · data export/deletion API (GDPR) · DPA +
subprocessor list · SOC 2 Type I (Vanta, ~$15k + 3 months) · LMS/LTI integration ·
accessibility-accommodation positioning and VPAT.

Building this speculatively is how solo products die. Wait for the pull.

---

## 9. Target repository structure

```
notealchemy/
├─ pyproject.toml                 # workspace root
├─ docker-compose.yml             # postgres + redis + api + worker
├─ Makefile                       # dev, test, migrate, lint
│
├─ packages/core/                 # ← today's src/, pure domain logic, zero web deps
│  └─ notealchemy_core/
│     ├─ llm/                     #   unchanged (rename groq_clients→groq_client)
│     ├─ transcription/           #   + chunking
│     ├─ notes/                   #   + parallel generation
│     ├─ export/                  #   + docx, anki; Unicode PDF
│     └─ evals/                   #   golden-set harness  (new)
│
├─ services/api/                  # FastAPI
│  └─ app/
│     ├─ main.py  deps.py  middleware/{auth,quota,tenant}.py
│     ├─ routers/{sources,jobs,notes,billing,webhooks}.py
│     ├─ db/{models.py,repositories/}       # tenant-scoped base repo
│     └─ migrations/                        # alembic
│
├─ services/worker/               # Arq
│  └─ app/{worker.py,tasks/,limiter.py}
│
├─ apps/web/                      # Next.js
│
├─ tools/streamlit_demo/          # today's main.py + src/ui — internal only
│
└─ .github/workflows/{ci.yml,deploy.yml}
```

The key discipline: **`packages/core` never imports FastAPI, Streamlit, or the database.** It's a
pure library the API, worker, demo, and tests all consume. Your current layering already almost
satisfies this — the only violations are the module-level `get_settings()` singletons, which
should become injected parameters.

---

## 10. Security and compliance track

| Requirement | Phase | Notes |
|---|---|---|
| Tenant isolation enforced in a base repository + tested | 3 | The #1 SaaS failure mode |
| Escape all model output; CSP headers | 1 | DIAG §3.3 |
| Secrets in platform secret store, never `.env` in prod | 3 | |
| Validate + allowlist YouTube URLs (SSRF) | 1 | DIAG §6 |
| Rate limits, quotas, global spend circuit-breaker | 3 | Before exposing your key |
| Soft delete + scheduled hard purge honouring `retention_days` | 3 | |
| Privacy Policy, ToS, cookie notice | 3 | **Blocker to charge money** |
| Subprocessor list (Groq, Clerk, Stripe, R2, Sentry) | 3 | Publish it; enterprises ask |
| GDPR data export + deletion endpoints | 4 | Lecture audio = voice = personal data |
| Encryption at rest + in transit | 3 | Managed services give you this |
| SOC 2 Type I | 5 | Only when a deal requires it |
| FERPA posture, VPAT/accessibility statement | 5 | US education buyers |
| DPA template | 5 | |

**Say this plainly in your Privacy Policy:** audio and transcripts are sent to Groq for
processing; state your retention period; state that you do not train models on user content.
Students and especially institutions will ask, and a clear answer is a selling point.

---

## 11. Instrumentation

**North star:** *weekly notes generated per active user.* It captures value delivery better than
signups or MRR, and it moves before churn does.

**Funnel to instrument in PostHog from day one of Phase 3:**
`landing → signup → first upload → first notes viewed → first export → subscribe → 2nd week
return`

Track first-upload→notes-viewed obsessively: it's where a bad first impression kills you, and
it's the one number a pre-PMF product must move.

| Metric | Target at launch |
|---|---|
| Free → paid conversion | >3% |
| Week-4 retention | >25% |
| Job success rate | >97% |
| p95 end-to-end (50-min lecture) | <45 s |
| COGS per generation | <$0.06 |
| Gross margin | >75% |
| Support tickets / 100 jobs | <2 |

**Ops alerts:** job failure rate >5% over 15 min · queue depth >50 · daily Groq spend >2× trailing
average (this one has saved people from five-figure surprises) · Stripe webhook failures.

---

## 12. Go-to-market

### 12.1 Sequence

**Pre-launch (during Phase 1–2).** Generate notes for 20 well-known public lectures (MIT OCW,
3Blue1Brown, CS50) and publish them as free SEO landing pages — "Complete notes for MIT 6.006
Lecture 3." This is your best acquisition channel: it demonstrates output quality, targets exactly
the search intent you want, and compounds. Start it early; SEO has a lag.

**Soft launch (end of Phase 3).** 50 students from your own network and 2–3 subject subreddits.
Free Pro for 3 months in exchange for structured feedback. Goal is qualitative, not revenue.

**Public launch (mid Phase 4).** Product Hunt + Hacker News (`Show HN`) + r/GetStudying,
r/college, r/premed, r/cscareerquestions. Lead with a 30-second video: 50-minute lecture → full
notes. **Show the artifact, not the UI.**

**Scale (post Phase 4).** Double down on the SEO note library. Campus ambassadors (free Pro +
commission). TikTok/Reels of the generation flow — this format converts extremely well for study
tools. Chrome extension listing as a second discovery surface.

### 12.2 Channel priority

1. **SEO note library** — compounding, free, proves quality. *Highest ROI.*
2. **Reddit/Discord** — where students actually are. Participate, don't spam.
3. **TikTok/Reels** — high variance, occasionally enormous.
4. **Chrome Web Store** — passive discovery.
5. Campus ambassadors — Phase 4+.
6. Paid ads — **not until LTV is known.** Students have terrible CAC:LTV.

### 12.3 Seasonality — plan for it

Revenue will spike Sept–Nov and Feb–Apr, and collapse May–Aug. Counters: push annual plans hard
before exams; build the professional-upskiller segment (no summer dip); run summer promos for
certification and bootcamp students.

---

## 13. Risks and kill criteria

| Risk | Severity | Mitigation | Kill signal |
|---|---|---|---|
| NotebookLM is good enough and free | **High** | Depth + export + speed; institutional wedge | Students prefer NotebookLM in blind comparison after Phase 1 → **stop, rethink the wedge** |
| Groq price rise or capacity limits | High | Abstract the provider behind `LLMClient` (already mostly done); keep a fallback | Margin <50% at list price |
| Students won't pay | High | Free tier proving value; annual pricing | <2% conversion after 500 signups + a fixed onboarding |
| Notes quality plateaus | Medium | Golden-set eval, templates, feedback loop | Thumbs-down >25% |
| Solo-founder bandwidth | **High** | Phase gates; ship Phase 1 as OSS for credibility even if you stop | — |
| Seasonality kills cash flow | Medium | Annual plans; professional segment | — |
| Copyright complaints (lecture recordings) | Medium | ToS places responsibility on user; DMCA process | — |

**The most important line in this document:** the kill signal in row 1 is real. Run that
comparison after Phase 1, before you spend four weeks on billing infrastructure. If your output
isn't clearly better for long technical lectures, the differentiator is gone and no amount of SaaS
plumbing rescues it — better to learn that in week 2 than week 10.

---

## 14. Next 7 days

| Day | Do |
|---|---|
| 1 (AM) | Phase 0: fix the import, requirements encoding, temp-file UUID, retry scope. Delete dead code + artifacts. Confirm clean-clone startup. |
| 1 (PM) | Parallelize section generation. Measure before/after on a real lecture. |
| 2 | whisper-large-v3-turbo quality comparison on 5 lectures. **Decide the default.** Unicode TTF in the PDF exporter. |
| 3 | `pyproject.toml`, locked deps, ruff + mypy clean, GitHub Actions CI green. |
| 4 | pytest suite (~40 tests) on the deterministic units listed in DIAG §4.2. |
| 5 | Golden-set eval harness + 10 reference lectures. Baseline your current quality. |
| 6 | Generate notes for 10 public lectures. Same 10 through NotebookLM. Build the comparison. |
| 7 | Show it to 20 students. **Record which they prefer and why.** Decide: proceed to Phase 2/3, or fix the output first. |

Nothing in week 1 is billing, auth, or infrastructure — deliberately. Week 1 answers "is the
artifact worth paying for," and everything after depends on that answer.

---

## Appendix — Cost model assumptions

- 50-minute lecture ≈ 7,500 words ≈ 10,000 tokens
- 6 sections, ~2,000 output tokens each
- Groq rates (verify before pricing): llama-3.3-70b $0.59/$0.79 per 1M in/out ·
  llama-3.1-8b $0.05/$0.08 · whisper-large-v3 $0.111/hr · whisper-large-v3-turbo $0.04/hr
- "Typical usage" = 40% of quota consumed, consistent with observed consumption-SaaS behaviour
- Fixed infra ~$100/mo at <1,000 users

Recompute these against live pricing before you publish a price. The structural conclusion —
**transcription dominates COGS, so transcription model choice and transcript caching are your
margin levers** — holds across any plausible rate change.
