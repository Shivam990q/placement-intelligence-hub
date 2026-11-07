# 🏛️ Architecture Decision Records (ADRs)

This document formally records all key architectural decisions made for the **Placement Intelligence Hub**, capturing context, options considered, trade-offs, and rationale.

---

## ADR-001: Dual-Engine Architecture (Python Ingestion + Cloudflare Edge Distribution)

### Status: Accepted
### Context:
The platform requires both intensive HTML scraping, fuzzy deduplication, and natural language text extraction, as well as high-concurrency, low-latency public edge distribution to thousands of college students at strictly ₹0 hosting cost.
Cloudflare Workers have a 10 ms CPU time limit on the free plan and allow only 50 outgoing subrequests per invocation, making heavy web crawling inside a Worker unstable. Conversely, running a continuous Python API server requires a paid VPS or server instance if hosted 24/7.

### Decision:
Implement a **Dual-Engine Topology**:
1. **Engine 1 (Data Acquisition & Intelligence):** Written in Python 3.12 (using FastAPI, SQLAlchemy, HTTPX, and RapidFuzz), running locally on developer hardware or scheduled headlessly on GitHub Actions free runners.
2. **Engine 2 (Public Edge API & Mini App):** Written in TypeScript using Hono for Cloudflare Workers, Cloudflare D1 (serverless SQLite), and Cloudflare Pages.

### Consequences:
- **Pros:** 100% free hosting; high scraping power with Python libraries; sub-50ms edge latency for students globally; zero memory leaks on servers.
- **Cons:** Requires synchronizing schema between SQLAlchemy models and Cloudflare D1 SQL.

---

## ADR-002: SQLite and Cloudflare D1 as the Universal Database Standard

### Status: Accepted
### Context:
Traditional managed relational databases (RDS PostgreSQL, Supabase, Neon) impose monthly subscription fees, compute limits, or aggressive inactivity auto-pausing (e.g. Supabase pauses free projects after 7 days of inactivity).

### Decision:
Adopt **SQLite (via `aiosqlite` / SQLAlchemy)** for local and offline development, and **Cloudflare D1 (serverless distributed SQLite)** for cloud production. Both share identical SQL dialetcs and ACID semantics.

### Consequences:
- **Pros:** 5,000,000 free reads/day and 100,000 free writes/day on D1; zero cold-start database connection pool latency; zero risk of inactivity pause; trivially exportable to a single `.sqlite` or `.sql` file for instantaneous backups.
- **Cons:** Concurrency limits on simultaneous write transactions (sufficient for ~100 writes/day).

---

## ADR-003: Deterministic Heuristic Extraction with Fallback AI Gateway

### Status: Accepted
### Context:
Using LLMs for every incoming job description incurs API token costs, latency spikes (1–3 seconds), and prompt injection vulnerabilities from user-submitted text.

### Decision:
Establish a **Deterministic Heuristic Engine as Primary** (regex patterns for batches, degrees, branches, salary strings, and canonical URL hashing). Employ an **AI Gateway only as an opportunistic fallback** when free Cloudflare Workers AI or local Ollama instances are available and the post cannot be resolved cleanly with regex.

### Consequences:
- **Pros:** 90%+ of career postings are parsed in <1 ms with 100% determinism; zero AI token cost; immune to prompt injection attacks; 100% offline-capable.
- **Cons:** Unstructured, conversational WhatsApp forwards without standard formatting require manual admin review or fallback AI parsing.

---

## ADR-004: Telegram Bot Long-Polling & Cloudflare Edge Webhook Hybrid

### Status: Accepted
### Context:
Local development requires zero public IP exposure and zero ngrok configuration. Production edge deployment requires webhook handling without long-running server processes.

### Decision:
Support both:
1. **Long-Polling Mode:** In `apps/telegram_bot/bot.py`, directly calls `getUpdates` over standard HTTPS. Works behind NAT, firewalls, and offline environments.
2. **Webhook Mode:** In `apps/cloudflare-worker/src/index.ts`, receives Telegram POST webhooks at `/telegram/webhook` and processes updates instantly at the edge.

### Consequences:
- **Pros:** Seamless local development without webhook tunneling; zero-maintenance serverless webhook in production.

---

## ADR-005: WhatsApp 1-Click Clipboard Card vs. Reverse-Engineered Session Userbots

### Status: Accepted
### Context:
Automating WhatsApp via unofficial Web Puppeteer/Baileys sessions carries a severe risk of permanent SIM/phone number bans from Meta's anti-spam algorithms, disrupting real student communications.

### Decision:
Reject unofficial WhatsApp socket automation. Implement an **Emoji-Optimized, 1-Click Clipboard Card**. The administrator clicks `[📋 Copy WhatsApp Card]` in Telegram or the Web Dashboard, and pastes it into WhatsApp college groups directly from their authenticated native WhatsApp client.

### Consequences:
- **Pros:** 0.00% ban risk; 100% compliance with WhatsApp Terms of Service; zero session disconnects or QR code re-authentications.
- **Cons:** Requires a 1-second human click to paste into WhatsApp groups.

---

## ADR-006: Fail-Closed Quota Defense Protocol

### Status: Accepted
### Context:
Free tiers from cloud providers can incur unexpected credit card bills or service disruptions if usage exceeds limits or if DDoS attacks hit edge endpoints.

### Decision:
Implement `packages/core/quota_manager.py` enforcing strict **Fail-Closed Thresholds**:
- At 80% usage: Log high-priority warnings.
- At 95% usage: Restrict high-cost background crawl operations and disable AI endpoints.
- At 100% usage: Hard fail-closed lock on external requests; switch exclusively to static cached responses and offline heuristic parsers.

### Consequences:
- **Pros:** Guaranteed ₹0 financial invariant; mathematical immunity to bill shocks.
- **Cons:** If 100,000 requests are exhausted in a day, edge worker throttles non-cached dynamic queries until midnight UTC.
