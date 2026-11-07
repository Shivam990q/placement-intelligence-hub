import asyncio
import os
import sys
import json
import httpx

# Ensure project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from packages.adapters.ethara import EtharaCareersAdapter
from packages.adapters.amazon import AmazonJobsAdapter
from packages.adapters.community import CommunitySubmissionAdapter
from packages.adapters.greenhouse import GreenhouseAdapter
from packages.adapters.lever import LeverAdapter
from packages.adapters.ashby import AshbyAdapter
from packages.intelligence.deduplicator import Deduplicator
from packages.core.database import init_db
from apps.workers.ingestion_worker import IngestionWorker

async def run_standalone_scraper():
    print("=" * 60)
    print("📡 EXECUTING PLACEMENT INTELLIGENCE WATCHDOG SCRAPER")
    print("=" * 60)

    edge_api_url = os.getenv("EDGE_API_URL", "")
    ingest_secret = os.getenv("INGEST_SECRET", "placement_secret_token_2026")

    # 1. Fetch from all adapters
    adapters = [
        EtharaCareersAdapter(),
        AmazonJobsAdapter(),
        CommunitySubmissionAdapter(),
        GreenhouseAdapter(board_token="razorpay", company_name="Razorpay"),
        LeverAdapter(company_slug="postman", company_name="Postman"),
        AshbyAdapter(company_slug="retool", company_name="Retool"),
    ]

    discovered_items = []
    for adapter in adapters:
        try:
            print(f"[*] Crawling {adapter.name} ({adapter.base_url})...")
            opps = await adapter.fetch_opportunities()
            print(f"    -> Found {len(opps)} listings.")
            for opp in opps:
                can_url = Deduplicator.canonicalize_url(opp.apply_url)
                discovered_items.append({
                    "company": opp.company,
                    "title": opp.title,
                    "normalized_title": Deduplicator.normalize_title(opp.title),
                    "role_category": opp.role_category,
                    "locations": opp.locations,
                    "eligible_batches": opp.eligible_batches,
                    "eligible_degrees": opp.eligible_degrees,
                    "eligible_branches": opp.eligible_branches,
                    "ctc_text": opp.ctc_text,
                    "apply_url": can_url,
                    "canonical_url_hash": Deduplicator.hash_url(can_url),
                    "content_hash": Deduplicator.hash_content(opp.company, opp.title, opp.raw_description),
                    "summary": opp.summary,
                    "requirements": opp.requirements,
                    "verification_status": opp.verification_status
                })
        except Exception as e:
            print(f"    [!] Error crawling {adapter.name}: {e}")

    print(f"\n[+] Total items normalized: {len(discovered_items)}")

    # 2. If Edge API URL is configured (GitHub Actions mode), post to Cloudflare Worker
    if edge_api_url:
        ingest_endpoint = f"{edge_api_url.rstrip('/')}/api/ingest"
        print(f"[*] Forwarding candidates to Cloudflare Edge at {ingest_endpoint}...")
        headers = {
            "Authorization": f"Bearer {ingest_secret}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(ingest_endpoint, json=discovered_items, headers=headers)
            print(f"    -> Edge Response: {resp.status_code} {resp.text}")
    else:
        # 3. Local SQLite Mode
        print("[*] Processing into local database...")
        await init_db()
        res = await IngestionWorker.run_acquisition_cycle()
        print(f"    -> Local Ingestion Summary: {res['new_opportunities_created']} new created, {res['duplicates_skipped']} duplicates skipped.")

    print("\n✅ Watchdog acquisition run finished successfully!")

if __name__ == "__main__":
    asyncio.run(run_standalone_scraper())
