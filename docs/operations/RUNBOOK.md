# 📖 Placement Intelligence Hub — Operations Runbook

## 1. Quick Start Commands

### 1.1 Local Development Environment (Windows / Linux / macOS)
```bash
# 1. Clone repository & enter directory
cd C:\Users\Rose\.gemini\antigravity\scratch\placement-intelligence-hub

# 2. Activate virtual environment (Python 3.12)
.venv\Scripts\activate   # Windows
# source .venv/bin/activate # Linux / macOS

# 3. Configure environment
copy .env.example .env

# 4. Start entire stack (API, Web Dashboard, Telegram Bot Poller)
python run.py
```
- Web Admin Dashboard: `http://localhost:8000`
- Telegram Mini App view: `http://localhost:8000/miniapp`
- Swagger / OpenAPI Docs: `http://localhost:8000/docs`

---

### 1.2 Docker Container Deployment
```bash
# Build and run with Docker Compose
docker compose up -d --build

# View real-time logs
docker compose logs -f

# Stop containers
docker compose down
```

---

### 1.3 Standalone Scheduled Scraper Execution
```bash
# Run one-off crawler pass across all active career adapters
python scripts/scheduled_scraper.py
```

---

## 2. Daily Operator Workflow

### 2.1 Reviewing & Triaging Opportunities
1. **Via Telegram Admin Group:**
   - Bot automatically posts review cards to the admin chat with buttons:
     * `[✅ Approve]` — Publishes to `@Placements` and appropriate category topic.
     * `[❌ Reject]` — Archives the opportunity.
     * `[📋 Copy WhatsApp Card]` — Copies pre-formatted text to clipboard.
2. **Via Web Admin Dashboard:**
   - Navigate to `http://localhost:8000`.
   - Inspect the **Pending Review Queue**.
   - Review company, role, package, batches, and source URL.
   - Click **Approve** or **Reject**.

---

### 2.2 Adding a New Career Target Adapter
1. Create a new adapter file in `packages/adapters/<company_name>.py` inheriting from `BaseSourceAdapter`.
2. Implement the `fetch_opportunities() -> List[RawOpportunity]` method.
3. Register the adapter in `apps/workers/ingestion_worker.py`:
```python
from packages.adapters.company_name import CompanyAdapter

self.adapters.append(CompanyAdapter())
```
4. Run tests: `python -m pytest tests/`

---

### 2.3 Handling Quota Warnings
If the `QuotaManager` reports an 80% or 95% threshold alert:
1. Check live status via Telegram `/status` or Gradio Lab `http://localhost:7860`.
2. Review `data/quota_state.json`.
3. If Workers AI is nearing 10,000 neurons, verify that deterministic fallback is active (it engages automatically at critical threshold).
4. If Cloudflare Workers requests are abnormally high, check access logs for automated scraping bots and tighten rate limits.

---

## 3. Troubleshooting Matrix

| Symptom | Probable Cause | Remediation |
| :--- | :--- | :--- |
| **Bot not replying to commands** | Invalid `TELEGRAM_BOT_TOKEN` or webhook conflicting with poller | Run `python -c "import httpx; print(httpx.get('https://api.telegram.org/bot<TOKEN>/getMe').json())"` to test token validity. |
| **Opportunities not appearing in DB** | Crawler failing on network timeout | Inspect `logs/` or run `python scripts/scheduled_scraper.py` directly to see stack trace. |
| **RapidFuzz similarity false positive** | Title normalization removing distinct qualifiers | Adjust `similarity_threshold` in `packages/intelligence/deduplicator.py` from 85% to 90%. |
| **Database locked error** | Concurrent write transactions in SQLite | SQLAlchemy session handles retries automatically; ensure transactions are closed via `async with AsyncSessionLocal()`. |
