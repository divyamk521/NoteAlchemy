# NoteAlchemy — Enterprise Readiness Diagnosis

**Reviewed:** 2026-08-03 · **Commit:** `e1b2b3f` · **Scope:** full codebase (39 files, ~2,900 LOC)

---

## 1. Verdict

NoteAlchemy is a **well-architected prototype that currently does not run**. The layering
(transcription → LLM → notes → export → UI) is genuinely good — better than most projects at
this stage — and it is the right skeleton to build a product on. But between "this repo" and
"a thing you can charge money for" there are three distinct gaps, and only one of them is code
quality:

| Dimension | State | Gap to sellable |
|---|---|---|
| Architecture / layering | **Strong** | Minor |
| Correctness (does it run?) | **Broken** — app crashes on import | Small, mechanical |
| Engineering discipline (tests, CI, packaging) | **Absent** | Medium |
| Multi-tenancy, auth, metering, billing | **Absent** | **Large — this is the real work** |
| Unit economics / cost control | **Unmodelled** | **Large** |
| Legal (license, terms, data handling) | **Absent** | Medium |

**The honest read:** you have maybe 15% of a sellable product. The 85% remaining is almost
entirely *not* in `src/` — it's identity, billing, quotas, persistence, and a deployment story.
The good news is the domain logic you've written is the part most people get wrong, and you got
it mostly right.

**Biggest strategic issue:** Streamlit + bring-your-own-API-key is an architecture that
*structurally cannot* be sold as SaaS. Streamlit has no multi-user model, and BYO-key means you
have no usage to meter and therefore nothing to price. Section 7 covers the fork in the road.

---

## 2. P0 — Broken right now

### 2.1 The application does not start (blocker)

`src/llm/__init__.py:1` imports a module that does not exist:

```python
from .groq_client import build_client, get_cached_client, GroqClientError
```

The file on disk is `src/llm/groq_clients.py` — **plural**. Verified:

```
ModuleNotFoundError: No module named 'src.llm.groq_client'
```

`main.py:23` does `from src.llm import build_client` at module top level, so Streamlit dies
before rendering a single pixel. This is independent of installed dependencies.

**Fix:** rename `groq_clients.py` → `groq_client.py` (matches the README's documented tree).

### 2.2 `requirements.txt` is UTF-16 encoded — `pip install -r` fails

The file was produced by `pip freeze > requirements.txt` in PowerShell, which writes UTF-16LE
with a BOM. Every line reads as `a l t a i r = = 6 . 1 . 0`. pip cannot parse it, so a fresh
clone cannot be installed — the documented Quickstart (Step 3) fails for every new user.

**Fix:** rewrite as UTF-8, and split direct dependencies from the frozen lock (§4.3).

### 2.3 `test_ui.py` is broken and is not a test

`test_ui.py:105` constructs `GenerationStats(transcription_time=…, generation_time=…,
total_time=…)`. None of those fields exist on the dataclass, and `total_time` is a read-only
`@property` — this raises `TypeError` on execution. It's also not a test: no pytest, no
assertions, it's a manual Streamlit scratch page. It gives a false impression of test coverage.

**Fix:** delete it, or move to `scripts/ui_sandbox.py` and fix the constructor. Real tests
under §4.2.

---

## 3. P1 — Correctness and robustness bugs

### 3.1 Concurrent uploads corrupt each other

`src/utils/file_utils.py:51`:

```python
tmp_path = tmp_dir / f"sw_upload_{os.getpid()}{ext}"
```

The temp filename is keyed on **process ID only**. Streamlit serves all concurrent sessions from
one process, so every simultaneous user gets the *same* path. Two users uploading at once →
one overwrites the other's audio, and whichever finishes first deletes the file the other is
still reading. User A gets User B's transcript, or a `FileNotFoundError`.

This is a data-leakage bug, not just a race: **User A can receive notes generated from User B's
audio.** For a paid multi-tenant product that is disqualifying.

**Fix:** `uuid4().hex` in the filename, or just use `tempfile.NamedTemporaryFile(delete=False)`.

### 3.2 Retry policy retries everything, including permanent failures

`src/utils/retry.py:25` — `retry=retry_if_exception_type(Exception)`.

This retries on **every** exception: a 401 from a bad API key, a 400 from a malformed request,
`CompletionError` from unparseable JSON, even `KeyboardInterrupt`-adjacent errors. With
`wait_exponential(multiplier=2, min=2, max=30)` and 3 attempts, a user who typos their API key
waits ~6 seconds through two pointless retries before seeing an error.

Worse, it's stacked: `@groq_retry` sits on `LLMClient.complete`, which is called once per
section. A systematic failure retries 3× per section across 6 sections = 18 doomed API calls.

**Fix:** retry only transient classes — `RateLimitError`, `APIConnectionError`,
`APITimeoutError`, `InternalServerError` (5xx). Let auth and validation errors fail fast.

### 3.3 LLM output is interpolated into raw HTML (XSS)

`src/ui/components.py:270`:

```python
st.markdown(f"<div class='notes-container'>{notes.markdown}</div>", unsafe_allow_html=True)
```

`notes.markdown` is **model output derived from arbitrary user-supplied transcript text**. A
transcript can steer the model into emitting `<script>`, `<img src=x onerror=…>`, or an
exfiltrating `<a href>`, and this renders it unescaped. Today, with BYO-key and one user per
session, the blast radius is self-inflicted. The moment you add shared notes, org accounts, or
public links, it's a stored-XSS vector against other tenants.

Two problems in one line, incidentally: the raw-`<div>` wrapper also means the first line of the
notes is parsed as an HTML block rather than markdown, so the `# Title` heading and the
`.notes-container h1` CSS rule that targets it don't reliably apply. Worth a visual check.

**Fix:** render with `st.markdown(notes.markdown)` (no raw wrapper, markdown parsed properly,
HTML escaped). Style via `st.container()` + a CSS class on the Streamlit-emitted element.

### 3.4 PDF export breaks on non-ASCII — contradicting the multi-language feature

`src/export/pdf_exporter.py` uses fpdf2 core fonts throughout (`Helvetica`, `Courier`). Core
PDF fonts are **latin-1 only**. fpdf2 ≥2.8 raises `FPDFUnicodeEncodingException` for anything
outside that range.

The README advertises Hindi, Japanese, and Chinese transcription. Notes in any of those
languages will crash PDF export. Even English notes break on curly quotes (`"`), em-dashes
(`—`), or `→` — all of which LLMs emit constantly. Commit `837b3f6` ("fix FPDF unicode bullet
rendering issue") worked around exactly this by replacing `•` with `-`; that treated the symptom.

*(I could not execute this locally — fpdf2 isn't installed in the environment I inspected from —
but it follows directly from the font choice and fpdf2's documented behaviour. Confirm by
exporting notes containing an em-dash.)*

**Fix:** ship a Unicode TTF (DejaVuSans, ~750 KB) and `pdf.add_font(…, uni=True)`. For CJK,
Noto Sans CJK. Alternatively drop fpdf2 for WeasyPrint/Playwright HTML→PDF, which gets you
real tables and proper typography (§3.5) at the cost of a heavier install.

### 3.5 PDF tables are structurally broken

`_table_row` (`pdf_exporter.py:186`) renders each cell with a fixed `col_w` and **truncates to
50 characters** with no wrapping. Any table with real prose — which the CONTENT_SYSTEM prompt
explicitly asks the model to produce — comes out clipped and misaligned. The README sells
"Rich markdown — tables" as a feature.

### 3.6 Upload limit contradiction wastes the user's time

`.streamlit/config.toml` sets `maxUploadSize = 200` (MB). `validate_audio_file` rejects anything
over `max_file_size_mb = 25`. So the UI happily accepts a 180 MB file, uploads all of it, then
rejects it. Set Streamlit's limit to match, and validate before upload where possible.

### 3.7 No guard on pasted transcript length

`render_text_input` accepts unbounded text. A user pasting a 500,000-word document sends it —
in full — to the structure model, then again for every section (§5.2). That's a runaway cost
and a guaranteed context-limit error, with no friendly message.

### 3.8 `logs/` is a hardcoded relative path

`src/utils/logger.py:20` writes to `"logs/notealchemy.log"`, resolved against the **current
working directory**. Run the app from anywhere but the repo root and logs scatter or fail. In a
container with a read-only filesystem it crashes at import time. Make it configurable and default
to stderr-only when unset (§4.5).

### 3.9 Missing `src/__init__.py`

Every subpackage has one; `src/` itself does not. It currently works via PEP 420 implicit
namespace packages, but it's inconsistent, and it will bite you the moment you package the app
(`pip install .` won't pick `src` up the way you expect).

---

## 4. P2 — Engineering discipline gaps

### 4.1 Dead prototype code shipped in the repo

`groq_utils.py` (145 LOC) and `export_utils.py` (145 LOC) are the pre-refactor prototypes, fully
superseded by `src/llm/` and `src/export/`. `export_utils.py` even says so in its docstring. They
are committed, importable, and contain a **second, divergent copy of every prompt** — so a
prompt change in `src/llm/prompts.py` silently leaves a stale duplicate behind. This is the
single most likely source of future "I fixed it but it didn't change" confusion.

Also committed and shouldn't be: `test.mp4` (96 KB), `notes_output.{md,txt,pdf}`,
`generated_notes.md`, `Introduction_to_Neural_Networks_notes.{txt,pdf}`. Build artifacts and test
fixtures in the repo root make the project read as unfinished to anyone evaluating it — including
a buyer doing due diligence.

### 4.2 Zero automated tests

There is no test suite. For a product whose core value is a multi-step LLM pipeline, the pieces
that most need tests are the deterministic ones, and they're all easy to cover:

- `_strip_json_fences` — fence variants, no fences, nested backticks
- `LectureNotes.markdown` — assembly, empty glossary, missing summary
- `_strip_markdown` / `_strip_inline` — the regexes are subtly greedy (`\*{1,3}(.+?)\*{1,3}`
  will happily match across `*a* and *b*`)
- `validate_audio_file` — extension and size boundaries
- `NotesStructure` validation — malformed LLM JSON
- `YouTubeDownloader.is_valid_youtube_url` — it's a naive substring check that accepts
  `evil.com/?x=youtube.com/watch`

Target: pytest, ~40 unit tests, LLM calls mocked at the `LLMClient` boundary (which your
dependency injection already makes trivial — credit where due). Plus one integration test behind
a `--live` flag.

### 4.3 Dependency management is a raw `pip freeze`

`requirements.txt` pins 65 packages with no distinction between what you actually import (10)
and Streamlit's transitive tree (altair, pandas, numpy, pyarrow, GitPython, protobuf…). You
cannot tell what's yours, upgrades are all-or-nothing, and you're carrying `GitPython` and
`numpy` for no reason you chose.

**Fix:** `pyproject.toml` with direct deps and permissive ranges; generate a locked
`requirements.txt` with `uv pip compile` or `pip-tools`. Separate `[dependency-groups] dev`.

### 4.4 No CI, no linting, no type checking

Type hints are used consistently and well throughout — but nothing enforces them, so they will
drift. Missing: GitHub Actions running `ruff check`, `ruff format --check`, `mypy`, `pytest`, and
`pip-audit` on every PR. Zero-cost on a repo this size and it's what makes the codebase legible
to a second engineer.

### 4.5 No observability

`loguru` → local rotating file is a dev setup, not a production one. You have no way to answer:
how many generations ran today, what's the p95 latency, what's the failure rate by stage, which
model call is burning the most tokens, did that user's export actually fail. `GenerationStats`
collects timings and then throws them away after rendering one line of UI.

Missing: structured JSON logs to stdout, error tracking (Sentry), a metrics counter per pipeline
stage, request/trace IDs correlating a user action across all 8 LLM calls, and token/cost
recording per generation (which you need for billing anyway — §5).

### 4.6 Configuration and branding inconsistencies

The model configuration disagrees with itself in three places:

| Source | STRUCTURE_MODEL |
|---|---|
| `config/settings.py:26` | `llama-3.3-70b-versatile` |
| `.env.example:8` | `meta-llama/llama-4-maverick-17b-128e-instruct` |
| `README.md:216` | `llama-3.3-70b-versatile` |

A user who uncomments `.env.example` silently switches models. Similarly, the product is called
**ScribeWizard** in `components.py:42` (sidebar heading) and `components.py:303` (welcome copy),
but **NoteAlchemy** in `main.py`, the README, and the PDF header. Pick one name — you're
selling this.

`README.md:78-80` documents `examples/essence_calculus/` and `examples/transformers_explained/`,
and `examples/README.md` tabulates them. **Neither directory exists.** The README also documents
a `src/ui/utils/` subdirectory that doesn't exist (utils is at `src/utils/`) and an `assets/audio/`
that doesn't exist.

### 4.7 No LICENSE — you legally cannot sell this yet

There is no license file. Absent one, the code is "all rights reserved" by default, which is
fine for a proprietary product but means you must also decide: your dependency tree includes
**yt-dlp (Unlicense — fine)** and **fpdf2 (LGPL-3.0)**. LGPL is generally fine for a hosted
SaaS but has obligations if you ever distribute a bundled desktop build. Run `pip-licenses` and
get a real answer before you take money.

**Also missing and required to sell:** Terms of Service, Privacy Policy, and a data-processing
statement — see §6.

---

## 5. Cost, performance, and scale

This section is the one that decides whether the product has a viable margin.

### 5.1 Sections are generated sequentially when they're embarrassingly parallel

`generator.py:114` — a plain `for` loop over sections, each an independent LLM call that only
depends on `(transcript, structure, section)`. Nothing shares state. Yet they run one at a time.

For 6 sections at ~4 s each, you're paying 24 s of wall-clock for ~4 s of critical path.
Running them concurrently (`ThreadPoolExecutor`, or async with the Groq async client) is a
**4–6× latency reduction for maybe 30 lines of code.** This is the single highest-leverage
change in the repo. Perceived speed is the entire pitch of a Groq-based product; right now you're
throwing it away.

Caveat: you'll want a semaphore to stay inside Groq's rate limits, and ordered result collection.

### 5.2 The full transcript is re-sent on every single call — the cost bug

Look at the call graph. For an N-section lecture, the transcript is sent to the API **N + 2**
times:

- `_build_structure` → full transcript
- `_build_section_content` × N → full transcript each (`prompts.py:83`)
- `_build_glossary` → full transcript again

A 60-minute lecture is ~9,000 words ≈ 12,000 tokens. With 6 sections that's **8 × 12,000 ≈
96,000 input tokens per generation**, to produce maybe 4,000 output tokens. You are paying
~24× more for input than the job requires, and it scales linearly with lecture length — the
worst possible shape.

Consequences beyond cost: you hit Groq's tokens-per-minute limit fast (making §5.1's parallelism
harder), and `llama-3.1-8b-instant`'s context window caps your maximum lecture length far below
what the transcript size alone would allow.

**Fix (in order of effort):**
1. **Section-relevant excerpts.** Chunk the transcript, and during structure generation have the
   model emit approximate start/end markers per section. Send each section only its own slice
   plus a small overlap. Cuts input tokens by ~5×.
2. **Map-reduce for long inputs.** Chunk → summarize chunks → build structure from summaries.
   Removes the length ceiling entirely and is what unlocks the 2-hour lectures your users will
   inevitably upload.
3. **Cache aggressively.** Hash the transcript; identical input should never regenerate. Users
   re-run constantly.

### 5.3 The 25 MB limit caps you at ~25 minutes, not the 60 the README claims

Groq's audio endpoint caps uploads at 25 MB. At a typical 128 kbps that's ~26 minutes of audio.
`README.md:245` says "Very long lectures (>60 min) may need to be split" — but a 60-minute file
was already rejected at 25 MB, long before that. There is no chunking, so **the product silently
cannot handle the most common real use case: a full 50-minute university lecture.**

**Fix:** split audio into <25 MB / <10 min segments client-side, transcribe in parallel, stitch
with overlap-dedup. This needs ffmpeg (or `pydub`), which breaks the "pure Python, no
compilation" promise — an acceptable trade, but make it a deliberate one.

### 5.4 No cancellation, no resumption, no durability

Generation runs synchronously inside the Streamlit script. If the user closes the tab, hits
refresh, or their WiFi blips at section 5 of 6, **all work and all money spent is lost** with no
way to resume. There's no job record, so you can't even tell them what happened.

For a 60-second operation costing real API spend, this needs to be a background job with a
persisted state machine (§7.2), not an inline function call.

### 5.5 No rate limiting or abuse protection

No per-user quota, no per-IP throttle, no CAPTCHA, no upload cap beyond file size. If you ever
host this with *your* API key, a single scripted client can drain your Groq balance in minutes.
This must land before any hosted deployment, not after.

---

## 6. Security, privacy, and compliance

Beyond §3.1 (cross-tenant data leak) and §3.3 (XSS):

**Secrets.** API keys live in `.env` and `st.session_state`. `get_cached_client`
(`groq_clients.py:31`) holds up to 8 keys in a process-global `lru_cache` that is never
invalidated and outlives the session that created it. Acceptable for local single-user; not for
hosted. You need a real secret manager and, if you keep BYO-key, envelope encryption at rest.

**`build_client` validates nothing.** `Groq(api_key=…)` makes no network call, so the
`except AuthenticationError` at `groq_clients.py:25` is unreachable — an invalid key passes
"validation" and surfaces 30 seconds later as a confusing `CompletionError` mid-pipeline. Do a
cheap `models.list()` probe at entry and fail immediately with a clear message.

**Prompt injection.** Transcript text flows unsanitized into system-prompt-adjacent context. A
crafted "lecture" can override instructions and steer output. Low severity for note-taking, but
it becomes real if you add tool use, or if generated notes are shared between users.

**No authentication or authorization at all.** There are no users, no sessions beyond
Streamlit's, no roles. Enterprise buyers will ask for SSO/SAML, RBAC, and an audit log; none of
the primitives exist yet.

**Data handling is undefined.** Audio and transcripts go to a third party (Groq). You have no
Privacy Policy, no DPA, no stated retention period, no deletion path. If you sell to a
university or any EU customer, GDPR applies: lecture recordings contain identifiable voices —
that's personal data, and lecturers/students have rights over it. FERPA is in scope for US
educational institutions. This is not optional paperwork; it's a gating item for exactly the
customers who'd pay most.

**No egress controls on YouTube ingest.** `is_valid_youtube_url` is a substring check. Combined
with yt-dlp's broad protocol support, a hostile URL is a plausible SSRF vector. Validate by
parsing the URL and allowlisting the host.

---

## 7. Making it sellable

### 7.1 The strategic fork

Your current architecture — Streamlit UI, user pastes their own Groq key, no persistence —
maps to exactly one business model, and it's the worst one. Three honest options:

**Option A — Open-source tool + paid hosted tier.** Keep the repo as a great local tool, sell
convenience. Lowest effort, lowest ceiling. Realistic revenue: small, but it builds distribution
and credibility, and it's a legitimate path if this is a portfolio/reputation play.

**Option B — B2C SaaS for students.** You hold the API key, meter usage, charge ~$8–15/mo.
Requires everything in §7.2. Large market, brutal CAC, and you're competing with Notion AI,
NotebookLM (free, Google-backed), and a dozen funded startups. Margin is workable *only* if you
fix §5.2 first — at 96k tokens/generation your COGS eats the subscription.

**Option C — B2B for institutions.** Sell per-seat or per-department to universities and
corporate L&D: lecture capture → structured notes, with SSO, retention controls, and an
accessibility angle (notes as an ADA/disability-services accommodation is a genuinely strong,
budget-unlocking wedge). Highest effort — you need SSO, audit logs, a DPA, and probably SOC 2 —
but 10–50× the ACV, a real moat, and buyers who don't churn. **This is where I'd point you**,
because the compliance work that looks like overhead in Option B *is* the moat in Option C.

Whichever you choose, **decide before writing more code**, because it determines whether you
need billing (B, C), SSO (C), or neither (A).

### 7.2 What Option B or C actually requires

None of this exists yet. This is the 85%.

**Split the monolith.** Streamlit can stay as an internal/demo surface, but it cannot be the
product — it has no multi-user model, no routing, no auth hooks, and re-runs your whole script
on every widget interaction. Extract the pipeline into a **FastAPI service** (your layering
already makes this easy — `NotesGenerator` has no UI dependency) with a real frontend
(Next.js/React) on top. This single move also fixes §5.4, §3.3, and §5.5 by giving you somewhere
to put jobs, escaping, and middleware.

**Then, in dependency order:**

1. **Persistence** — Postgres. Tables: `users`, `organizations`, `jobs`, `notes`,
   `usage_events`. Nothing below works without this.
2. **Job queue** — Celery/RQ/Arq + Redis. Generation becomes an async job with a status
   endpoint. Fixes cancellation, resumption, and progress; lets you retry a failed section
   instead of the whole run.
3. **Identity** — Clerk/Auth0/WorkOS rather than rolling your own. WorkOS if Option C, since it
   gives you SAML/SCIM without building it.
4. **Metering + billing** — record tokens and cost per `usage_event`, enforce plan quotas,
   Stripe for subscriptions. You cannot price what you don't measure, and right now you measure
   nothing.
5. **Object storage** — S3/R2 for audio and exports, with lifecycle rules that implement your
   stated retention policy.
6. **Deployment** — Dockerfile, health checks, IaC, staging environment. There is no Dockerfile
   today.
7. **Product surface** — a notes library (users will expect their history), editing (LLM output
   always needs a human pass), sharing, and DOCX/Notion/Anki export. Anki export in particular
   is a cheap, high-delight differentiator for the student segment.

### 7.3 Sequenced roadmap

**Phase 0 — Make it work (½ day).** Fix the import (§2.1), the encoding (§2.2), the temp-file
collision (§3.1), and the retry scope (§3.2). Delete dead code and artifacts (§4.1). This is
mostly mechanical and unblocks everything.

**Phase 1 — Make it good (1 week).** Parallelize sections (§5.1) — do this first, it's the
biggest visible win. Then Unicode PDF (§3.4), input caps (§3.6, §3.7), fix the XSS/render path
(§3.3), reconcile config and branding (§4.6), `pyproject.toml` (§4.3), pytest suite (§4.2), CI
(§4.4). **After Phase 1 you have a genuinely strong open-source project and a credible demo.**

**Phase 2 — Make it cheap (1 week).** Transcript excerpting and map-reduce (§5.2), audio
chunking to break the 25-minute ceiling (§5.3), result caching. This is the phase that decides
your gross margin — do it before you have customers, not after.

**Phase 3 — Make it a product (4–8 weeks).** FastAPI extraction, Postgres, job queue, auth,
metering, Stripe, Docker, frontend. §7.2 in order.

**Phase 4 — Make it enterprise (ongoing).** SSO/SAML, RBAC, audit logs, retention controls, DPA
and subprocessor list, SOC 2 Type I. Start this only when a named prospect asks — it's demand-led
work, and doing it speculatively is how solo products die.

### 7.4 The one thing to fix first

If you do nothing else this week: **§2.1** (it doesn't run) and **§5.1** (it's 5× slower than it
should be). The first is embarrassing in a demo; the second is the entire product promise —
"powered by Groq" means fast, and you're currently serializing away the only reason to use Groq.

---

## 8. Prioritized backlog

| # | Item | Sev | Effort | Ref |
|---|---|---|---|---|
| 1 | `groq_clients.py` → `groq_client.py` — app won't start | Blocker | 1 min | §2.1 |
| 2 | Rewrite `requirements.txt` as UTF-8 | Blocker | 5 min | §2.2 |
| 3 | UUID in temp filename — cross-user data leak | Critical | 10 min | §3.1 |
| 4 | Narrow retry to transient errors | High | 30 min | §3.2 |
| 5 | Parallelize section generation — 4–6× faster | High | 2 h | §5.1 |
| 6 | Remove raw-HTML interpolation of LLM output | High | 30 min | §3.3 |
| 7 | Unicode TTF for PDF export | High | 1 h | §3.4 |
| 8 | Delete `groq_utils.py`, `export_utils.py`, artifacts | High | 15 min | §4.1 |
| 9 | Delete/relocate broken `test_ui.py` | High | 5 min | §2.3 |
| 10 | Transcript excerpting — ~5× cost cut | High | 1 d | §5.2 |
| 11 | pytest suite (~40 unit tests) | High | 2 d | §4.2 |
| 12 | Reconcile model config + ScribeWizard/NoteAlchemy naming | Med | 30 min | §4.6 |
| 13 | `pyproject.toml` + locked deps | Med | 2 h | §4.3 |
| 14 | CI: ruff + mypy + pytest + pip-audit | Med | 2 h | §4.4 |
| 15 | Align upload limits; cap pasted transcript | Med | 30 min | §3.6, §3.7 |
| 16 | Configurable log path; JSON logs to stdout | Med | 1 h | §3.8, §4.5 |
| 17 | Audio chunking — break the 25-min ceiling | Med | 1 d | §5.3 |
| 18 | Real PDF table rendering | Med | 4 h | §3.5 |
| 19 | Validate API key on entry (`models.list()`) | Med | 20 min | §6 |
| 20 | Parse+allowlist YouTube URLs (SSRF) | Med | 20 min | §6 |
| 21 | Fix README: nonexistent dirs, wrong paths, 60-min claim | Med | 1 h | §4.6 |
| 22 | Add `src/__init__.py` | Low | 1 min | §3.9 |
| 23 | LICENSE + dependency license audit | Blocker *to sell* | 2 h | §4.7 |
| 24 | FastAPI extraction + Postgres + queue | — | 3 w | §7.2 |
| 25 | Auth + metering + Stripe | — | 3 w | §7.2 |
| 26 | Privacy Policy, ToS, DPA, retention policy | Blocker *to sell* | — | §6 |

Items 1–9 are roughly one focused day and take the project from "broken" to "solid demo".
