# NoteAlchemy — Zero-Cost Build & Launch Plan

**Version:** 1.0 · **Date:** 2026-08-03 · **Supersedes the infrastructure sections of `PRODUCT_PLAN.md`**

Constraint: **spend $0.** Everything below is achievable on permanent free tiers that permit
commercial use. Free-tier terms change — every limit here was verified 2026-08-03, and you should
re-check before depending on any of it.

---

## 1. The headline

**You can build, launch, and take your first payments for $0/month.** The product logic, hosting,
database, storage, auth, CI, error tracking, and AI inference all have free tiers that allow
commercial use.

Two things are genuinely not free, and you should know exactly what they are:

| Thing | Cost | Can you avoid it? |
|---|---|---|
| Payment processor cut | ~3–6% of revenue | No — but it's a % of money you've already received, never an upfront bill |
| Domain name | ~$10/year | Yes (use a free subdomain), but I'd make this your one exception — see §6 |

Everything else is $0.

---

## 2. The strategic unlock — and a correction to my earlier advice

In `PRODUCT_PLAN.md` §0 I told you "you must hold the API key; BYO-key is structurally
incompatible with SaaS." **Under a zero-capital constraint that advice is wrong, and I'm
reversing it.**

Here's why. Groq's free tier requires **no credit card** and gives every user 30 requests/minute
and 2,000 Whisper requests/day. So "grab a free Groq key, takes 60 seconds" is a genuinely small
ask — not the friction I assumed.

That means:

> **Keep bring-your-own-key. Charge for the product layer, not the inference.**

Your variable cost becomes **exactly zero**, at any number of users. And there is still plenty to
sell, because the API key was never the valuable part:

| Free (BYO-key) | Paid $5–7/mo (BYO-key) |
|---|---|
| Generate notes | **Notes library** — history, folders, search |
| Markdown + TXT export | **PDF, DOCX, Anki, Notion export** |
| Notes kept 7 days | Unlimited retention |
| One at a time | **Editing**, templates (Exam Prep / Cheat Sheet) |
| | Batch upload, Chrome extension, priority queue |

**100% gross margin. Self-funding from day one.** Later, when revenue exists, add a premium
"we handle the key" tier — paid for out of that revenue, not your pocket.

This also fixes the throughput problem you'd otherwise hit: Groq's limits are **per
organization**, so multiple keys don't multiply your quota. If *you* held one key, all your users
would share 30 req/min — roughly 5 concurrent generations before everyone queues. BYO-key means
each user brings their own 30 req/min. **The constraint that looked like a weakness is actually
what lets you scale for free.**

Your existing sidebar key input already works this way. You were accidentally right.

---

## 3. The zero-cost stack

All of these permit commercial use on the free tier.

| Layer | Choice | Free allowance | Notes |
|---|---|---|---|
| **Compute** | **Oracle Cloud Always Free** ARM VPS | 2 OCPU / 12 GB / 200 GB | Runs *everything* on one box. Card needed for ID check, not charged. See §5 risk. |
| **CDN / DNS / TLS** | **Cloudflare free** | Unlimited | Commercial use explicitly allowed. Put it in front of the VPS. |
| **Marketing site** | **Cloudflare Pages** | Unlimited builds | Commercial allowed — unlike Vercel Hobby |
| **Database** | **Postgres on the VPS** | No limits | Managed alternative: Neon free (0.5 GB) |
| **Queue** | **Postgres `SKIP LOCKED`** | — | **Skip Redis entirely.** ~40 lines. One less service. |
| **Object storage** | **Cloudflare R2** | 10 GB + **zero egress** | Egress-free matters — you serve lots of PDFs |
| **Auth** | FastAPI + JWT + argon2 | — | ~200 LOC. Or Clerk free (10k MAU) to save a day |
| **AI inference** | **Groq free tier (user's key)** | 30 RPM · 2k Whisper req/day | §2 |
| **Payments** | Stripe / Paddle / Razorpay | No monthly fee | % per transaction only. §6 |
| **CI** | GitHub Actions | Unlimited (public repo) | 2,000 min/mo if private |
| **Errors** | Sentry free | 5k events/mo | |
| **Analytics** | PostHog free / self-host Umami | 1M events/mo | Umami on the VPS = truly unlimited |
| **Email** | Brevo free | 300/day | Enough for transactional |
| **Uptime** | UptimeRobot free | 50 monitors | Also keeps the VPS from idling (§5) |

**Total: $0/month.**

### 3.1 What to cut from the original plan

The `PRODUCT_PLAN.md` architecture assumed managed services. Simplify hard:

| Original | Zero-cost version | Why it's fine |
|---|---|---|
| Next.js on Vercel | **FastAPI + Jinja2 + HTMX**, served from the VPS | No separate deploy, no build step, no Node. HTMX + SSE handles job progress beautifully. Saves a week. |
| Redis queue | Postgres `FOR UPDATE SKIP LOCKED` | You'll have <100 jobs/day. Redis is premature. |
| Separate API + worker services | One process, background task thread | Split later when it hurts |
| Clerk | Own JWT auth | One day of work vs. a dependency |
| Managed Postgres | Postgres on the VPS | You control it; no row/storage caps |

**Do not use Cloudflare Workers for the API.** Python support there can't run the `groq` SDK or
`fpdf2`. Cloudflare is for DNS, TLS, caching, R2, and the static marketing site only.

### 3.2 Resulting shape

```
                Cloudflare (DNS, TLS, cache, R2)  — free, commercial OK
                              │
                    ┌─────────▼──────────┐
                    │  Oracle Free VPS   │   2 OCPU / 12 GB
                    │  ┌──────────────┐  │
                    │  │ Caddy (TLS)  │  │
                    │  ├──────────────┤  │
                    │  │ FastAPI      │  │  API + HTMX pages + SSE
                    │  │  + bg worker │  │
                    │  ├──────────────┤  │
                    │  │ Postgres     │  │  data + job queue
                    │  └──────────────┘  │
                    └────────┬───────────┘
                             │ user's own Groq key
                             ▼
                        Groq free tier
```

One VPS. One process. One database. Zero dollars.

---

## 4. Revised build plan

Phases 0–2 from `PRODUCT_PLAN.md` are unchanged — they're pure code, no infrastructure, no money.
Phase 3 is what shrinks.

**Phase 0 — Make it run · ½ day.** Unchanged. Fix the import, the UTF-16 requirements file, the
temp-file collision, the retry scope. Delete dead code and artifacts.

**Phase 1 — Make it good · 1 week.** Unchanged, except **drop the whisper-turbo evaluation from
the critical path** — with BYO-key you aren't paying for transcription, so it's a quality and
speed question, not a margin one. Still do: parallel sections, Unicode PDF, escape LLM output,
tests, CI, golden-set eval, and the NotebookLM comparison.

**Phase 2 — Make it scale · 4 days** (down from 1 week). Audio chunking to break the 25-minute
ceiling, transcript caching by content hash, structured logs. **Skip the Redis rate limiter** —
each user has their own Groq quota now, so you only need a small per-user concurrency semaphore.

**Phase 3 — Make it a SaaS · 2 weeks** (down from 4).

- *Days 1–3* — Oracle VPS provisioned, Caddy + TLS, Postgres, Docker Compose, deploy script.
  FastAPI skeleton with health checks. Alembic + the §5 schema from `PRODUCT_PLAN.md` (keep
  `tenant_id` and `audit_log` — they cost nothing and save a migration later).
- *Days 4–6* — Job table as queue with `SKIP LOCKED`, background worker loop, SSE progress. Your
  `NotesGenerator` driven by a job row.
- *Days 7–9* — JWT auth, email verification, tenant scoping enforced in a base repository class.
  Encrypt each user's stored Groq key at rest.
- *Days 10–12* — HTMX UI: upload, progress, notes library, editor, exports. Cloudflare Pages
  marketing + pricing page.
- *Days 13–14* — Payment processor, webhook, plan → entitlement map, quota enforcement.

**Phase 4 — Retain · 2 weeks.** Unchanged: Anki, DOCX, templates, Chrome extension, onboarding.

**Phase 5 — Enterprise.** **Not reachable for free**, and that's fine. SSO, SOC 2 (~$15k), and a
DPA all cost real money. Revisit only when a customer's cheque covers it.

**Total: ~5 weeks, $0.**

---

## 5. Honest risks of going free

I'd rather you know these upfront than discover them at 2 a.m.

**Oracle can and does change the free tier.** In June 2026 they cut Always Free ARM from 4
OCPU/24 GB to 2 OCPU/12 GB. That's proof the rug can move. Oracle also reclaims persistently idle
Always Free instances — an UptimeRobot ping every 5 minutes mitigates this. **Mitigation that
actually matters: keep everything in Docker Compose with a scripted `pg_dump` to R2 daily, so you
can rebuild on any VPS in under an hour.** Do not hand-configure the box.

**Verify Oracle's commercial-use terms yourself.** I could not find an explicit statement either
way in their Always Free documentation. If it's restricted, fall back to Hugging Face Spaces
(free Docker) or a $4–5/mo Hetzner box — the cheapest real exception you might have to make.

**Single point of failure.** One VPS, no redundancy, no SLA. A reboot is downtime. Acceptable
pre-revenue; not acceptable to an institution — which is why Phase 5 needs money.

**Groq free-tier limits are per organization.** Fine under BYO-key. But it means you can never
quietly absorb a user's inference cost as a courtesy — the architecture depends on their key.

**Free tiers have no support.** When something breaks you are alone with the docs.

**BYO-key adds signup friction.** "Get a free Groq key" will cost you some conversion. Reduce it:
inline 3-step instructions with screenshots, a paste-and-validate field that confirms the key
works immediately (fix the unreachable `AuthenticationError` in `groq_clients.py:25` — do a real
`models.list()` probe), and a demo that runs on a pre-generated sample lecture so people see the
output *before* being asked for anything.

**The real cost is your time.** Five weeks of evenings. That's the actual price, and it's not
small — which is exactly why the NotebookLM comparison in Phase 1 comes before Phase 3.

---

## 6. Getting paid without spending

Payment processors charge a percentage, never a monthly fee — so this is not upfront spend.

| Option | Cut | Setup |
|---|---|---|
| **Stripe** | 2.9% + $0.30 | Cheapest. Needs a business entity/bank account; **not available to individuals in every country** |
| **Paddle / Lemon Squeezy** | ~5% + $0.50 | **Merchant of Record** — they handle VAT/GST and act as the seller. Easiest if you have no company |
| **Razorpay** | ~2% | The India option, since Stripe India is invite-restricted |
| **Gumroad** | ~10% | Highest cut, near-zero setup. Fine for validating willingness to pay |

**Recommendation:** if you can't get Stripe easily, start with **Paddle or Lemon Squeezy** as
Merchant of Record. The extra ~2% is worth not registering a company or filing tax in other
jurisdictions on day one. Move to Stripe when volume justifies it.

**The domain — my one recommended exception.** ~$10/year. People will not put a card into
`notealchemy.onrender.com`. If you truly want $0, launch free-tier-only on a subdomain, validate
demand, then buy the domain out of your first month's revenue. But this is the highest-ROI $10 in
the plan.

---

## 7. Revised pricing

Costs collapse under BYO-key, so price for **value and volume**, not margin recovery.

| Tier | Price | Includes |
|---|---|---|
| **Free** | $0 | Unlimited generations (their key, their quota) · Markdown + TXT · 7-day history |
| **Pro** | **$5/mo** or **$40/yr** | Library + search + folders · PDF, DOCX, **Anki**, Notion · editing · templates · unlimited retention · Chrome extension |
| **Managed** | $15/mo | *Phase 5+, funded by revenue* — we supply the key, no setup |

$5 is a deliberate impulse-buy price. With 100% margin and zero fixed costs, **your break-even is
one subscriber** — not twelve. Every sale is pure profit, which means you can afford to be patient
and to price low enough that students don't think twice.

Push annual hard: $40 up front from 25 users is $1,000, which funds a domain, a real VPS, and the
managed tier.

---

## 8. Next 7 days (unchanged in substance)

| Day | Do |
|---|---|
| 1 | Phase 0 fixes. Parallelize section generation. |
| 2 | Unicode TTF for PDF. Real API-key validation on entry. |
| 3 | `pyproject.toml`, ruff + mypy clean, GitHub Actions green. |
| 4 | pytest suite (~40 tests). |
| 5 | Golden-set eval harness, 10 reference lectures, baseline quality. |
| 6 | Generate notes for 10 public lectures; same 10 through NotebookLM. |
| 7 | Show both to 20 students. Record which they prefer and why. |

Still zero infrastructure in week 1, and now there's a second reason: **none of it costs money, so
there's no excuse to start with the plumbing instead of the product.** Week 1 answers whether the
artifact is worth $5.

---

## Sources (verified 2026-08-03)

- [Groq free tier limits](https://tokenmix.ai/blog/groq-free-tier-limits-2026) — 30 RPM, 6k–30k TPM, 1k–14.4k req/day
- [Groq free tier detail](https://www.grizzlypeaksoftware.com/articles/p/groq-api-free-tier-limits-in-2026-what-you-actually-get-uwysd6mb) — Whisper 2,000 req/day, 7,200 audio sec/hour, org-level limits, no card
- [Vercel Hobby plan terms](https://vercel.com/docs/plans/hobby) — non-commercial only
- [Vercel fair use](https://vercel.com/docs/limits/fair-use-guidelines) — payment processing prohibited; termination without notice
- [Cloudflare free commercial use](https://community.cloudflare.com/t/is-cloudflare-pages-workers-free-plan-free-for-commercial-use/291741) — commercial use permitted
- [Oracle free tier change, June 2026](https://terminalbytes.com/oracle-cloud-free-tier-changes-2026/) — ARM cut to 2 OCPU / 12 GB
- [Oracle Always Free overview](https://cloudpricecheck.com/free-tier/oracle) — 200 GB storage, 10 TB egress
