import pytest
import os
from packages.core.database import init_db, AsyncSessionLocal, engine, Base
from packages.core.models import Opportunity, Source, ApprovalQueue, OpportunityVersion, AuditLog
from apps.workers.ingestion_worker import IngestionWorker
from sqlalchemy import select, delete

@pytest.mark.asyncio
async def test_full_acquisition_and_deduplication_cycle():
    # 1. Initialize tables and clean up prior records for isolated test
    await init_db()
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ApprovalQueue))
        await session.execute(delete(OpportunityVersion))
        await session.execute(delete(AuditLog))
        await session.execute(delete(Opportunity))
        await session.commit()

    # 2. First Scan Run
    res1 = await IngestionWorker.run_acquisition_cycle()
    assert res1["total_scanned_sources"] >= 3
    assert res1["new_opportunities_created"] >= 3

    async with AsyncSessionLocal() as session:
        # Check Ethara role is present
        ethara_res = await session.execute(
            select(Opportunity).where(Opportunity.company.ilike("%ethara%"))
        )
        ethara_opp = ethara_res.scalars().first()
        assert ethara_opp is not None
        assert "LLM" in ethara_opp.title or "GenOPS" in ethara_opp.title
        assert ethara_opp.status == "pending_approval"

        # Check Amazon role is present
        amazon_res = await session.execute(
            select(Opportunity).where(Opportunity.company.ilike("%amazon%"))
        )
        amazon_opp = amazon_res.scalars().first()
        assert amazon_opp is not None
        assert "Intern" in amazon_opp.title

    # 3. Second Scan Run (Deduplication Check)
    res2 = await IngestionWorker.run_acquisition_cycle()
    # No new duplicates should be created
    assert res2["new_opportunities_created"] == 0
    assert res2["duplicates_skipped"] >= 3
