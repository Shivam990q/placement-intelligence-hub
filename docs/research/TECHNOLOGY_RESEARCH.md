# 🔬 Placement Intelligence Hub — Technology Research Report

## Executive Summary
This document provides an exhaustive, evidence-based technological investigation supporting the **Placement Intelligence Hub**. It establishes the feasibility, operational ceilings, and mathematical safety margins required to run a 24/7 college placement intelligence and distribution network at **strictly ₹0 monthly expenditure**.

---

## 1. Cloudflare Free Tier Capabilities & Hard Limits

Cloudflare's serverless ecosystem represents the primary production runtime for public edge distribution and database queries without credit card billing traps.

| Service | Free Tier Allocation | Operational Consumption Model | Fail-Closed Safety Margin |
| :--- | :--- | :--- | :--- |
| **Cloudflare Workers** | 100,000 requests / day (burst: 1,000 req/min) | 5,000 active students checking 10 times/day = 50,000 req/day | 50% head-room margin |
| **Cloudflare D1 (SQLite)** | 5,000,000 rows read / day<br>100,000 rows written / day<br>5 GB total storage | ~20 opportunities indexed/day = 200 writes/day<br>Read cache via CDN edge caches = ~25,000 reads/day | >99% read headroom<br>>99% write headroom |
| **Workers AI** | 10,000 Neurons / day free tier (~500–1,000 small inferences) | Reserved strictly for ambiguous unstructured posts; deterministic regex handles 90%+ | Fail-closed quota gate blocks requests at 9,500 Neurons |
| **Cloudflare Pages** | Unlimited static bandwidth & requests | Static Single Page Application (Dashboard + Mini App) hosted globally | 100% free / unlimited |
| **Cloudflare R2** | 10 GB storage / month<br>1M Class A ops (write)<br>10M Class B ops (read) | Resume templates, DSA cheat sheets, full-page HTML snapshots | >95% storage headroom |

### Critical Cloudflare Free Tier Invariants:
1. **Subrequest Limit:** Cloudflare Workers free plan allows up to 50 outgoing `fetch()` subrequests per worker invocation. Web scraping directly inside a Worker can hit this limit quickly; hence, **crawling is decoupled to GitHub Actions / local Python runtimes**.
2. **CPU Time Limit:** 10 ms CPU time limit on the free plan (wall-clock I/O wait is excluded). All CPU-intensive fuzzy text matching (RapidFuzz) and HTML parsing are offloaded from edge workers.

---

## 2. GitHub Actions Free Runner Specifications

GitHub provides 2,000 free runner minutes per month for public repositories on Ubuntu/Windows/macOS standard runners.

| Parameter | Specification | Usage in Placement Hub |
| :--- | :--- | :--- |
| **Virtual Machine Spec** | 2-core CPU (x86_64), 7 GB RAM, 14 GB SSD storage | Python 3.12, Playwright, HTTPX, Scrapy run cleanly with zero memory pressure |
| **Scheduled Interval** | Cron trigger (e.g. `*/30 * * * *` or `0 */2 * * *`) | Scheduled crawler runs 48 times/day; average run duration = 40 seconds = 32 runner minutes/day |
| **Monthly Consumption** | 32 min/day × 30 days = 960 minutes / month | Consumes 48% of the 2,000-minute free quota (52% safety buffer) |
| **Cron Jitter Caveat** | Public GitHub Actions cron executions experience scheduling delays (5–25 minutes during peak UTC hours) | System tolerates ±15 min jitter since placement updates occur over hours/days, not sub-seconds |

---

## 3. Telegram Bot API v10.3 & Distribution Capabilities

Telegram provides an industrial-grade, zero-cost messaging platform with rich interaction primitives:

1. **Bot API Rate Limits:**
   - Global broadcast: 30 messages/second across all chats.
   - Single private chat: 1 message/second.
   - Groups & supergroups: 20 messages/minute.
   - `429 Too Many Requests`: Returns `retry_after` parameter in seconds.
2. **Forum Topics (`message_thread_id`):**
   - Supergroups with Topics enabled permit segmented categorization without spawning multiple separate channels.
   - Supported threads:
     * `Internships (2026/2027)`
     * `Full-Time Roles`
     * `Mass Recruitment Drives`
     * `Hackathons & Competitions`
     * `Resources & Study Material`
3. **Telegram Mini Apps (WebApps):**
   - Renders HTML5/JavaScript interfaces directly inside Telegram without launching an external browser.
   - Cryptographic authentication via `window.Telegram.WebApp.initData` using `HMAC-SHA256` ensures zero credential overhead.

---

## 4. WhatsApp Zero-Ban Architecture Evaluation

### The Account Ban Risk:
Directly connecting headless browsers (Puppeteer, Playwright) or reverse-engineered WebSocket protocols (Baileys, WhatsApp-Web.js) with personal SIM cards triggers WhatsApp's automated anti-abuse heuristics, resulting in permanent phone number bans.

### The Zero-Risk Solution (1-Click Clipboard Card):
- The bot generates standardized, emoji-rich, markdown-formatted text cards optimized for WhatsApp.
- Administrators review submissions in the Telegram Admin Channel or Web Dashboard and tap **[📋 Copy WhatsApp Card]**.
- The pre-formatted text is copied instantly to the clipboard, allowing 1-tap manual pasting into official college placement groups (`2027 Batch Placement 1`, etc.).
- **Account Ban Risk: 0.00%**.

---

## 5. Free-Tier AI & LLM Inference Options

| Provider | Model | Cost | Latency | Role in Platform |
| :--- | :--- | :--- | :--- | :--- |
| **Deterministic Engine** | Regex + RapidFuzz + Heuristics | ₹0.00 | <1 ms | **Primary Engine (90% of tasks)** |
| **Cloudflare Workers AI** | `@cf/meta/llama-3.1-8b-instruct` | ₹0.00 (10k Neurons/day) | ~400 ms | Unstructured WhatsApp text parsing |
| **Hugging Face Serverless**| `Qwen/Qwen2.5-Coder-7B-Instruct` | ₹0.00 (Free tier) | ~1.2 s | Secondary fallback for complex descriptions |
| **Local Ollama** | `Llama 3.2 3B` / `Mistral 7B` | ₹0.00 (Runs on local hardware) | ~600 ms | Offline batch enrichment & evaluation |

---

## 6. Audit of Existing Recruitment Crawlers (FreeHire Benchmark)

An architectural audit of existing open-source recruitment aggregators (such as FreeHire, JobSpy, and open-source ATS scrapers) reveals three major architectural pitfalls:
1. **Direct DOM Scraping Fragility:** Relying on CSS selectors (`div.job-title-header`) breaks when companies update their frontends.
   * *Our Fix:* Query public JSON APIs directly (Greenhouse API `/v1/boards/{token}/jobs`, Lever API `/v1/postings/{token}`, Ashby API `/posting-api/job-board/{name}`).
2. **Naive URL Matching:** Comparing raw URLs leads to duplicate records due to varying UTM tracking parameters (`?utm_source=telegram`).
   * *Our Fix:* Canonical URL normalization stripping query strings, path trailing slashes, and protocol variances.
3. **Autonomous Publishing Hallucination:** Letting an LLM decide whether an internship is genuine often lets scam or referral posts slip through.
   * *Our Fix:* Strict human-in-the-loop approval gate via Telegram inline buttons before any message reaches `@Placements`.
