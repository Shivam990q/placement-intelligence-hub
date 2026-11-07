from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from packages.core.database import get_db
from packages.core.models import Source, AuditLog
from packages.schemas.source import SourceResponse, SourceCreate
from apps.workers.ingestion_worker import IngestionWorker

router = APIRouter(prefix="/api/sources", tags=["Sources & Crawlers"])

@router.get("", response_model=List[SourceResponse])
async def list_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).order_by(desc(Source.last_checked_at)))
    return result.scalars().all()

@router.post("", response_model=SourceResponse)
async def create_source(source_data: SourceCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Source).where(Source.slug == source_data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Source slug already registered")

    source = Source(
        name=source_data.name,
        slug=source_data.slug,
        source_type=source_data.source_type,
        base_url=source_data.base_url,
        is_active=source_data.is_active,
        check_interval_minutes=source_data.check_interval_minutes,
        last_status="pending",
        health_score=1.0,
        total_discovered=0
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source

@router.post("/crawl")
async def trigger_crawl(source_slug: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """
    Triggers an immediate acquisition and deduplication run.
    If source_slug is provided, crawls only that source; otherwise crawls all active sources.
    """
    results = await IngestionWorker.run_acquisition_cycle(source_slug=source_slug)
    return {
        "status": "completed",
        "timestamp": datetime.utcnow(),
        "summary": results
    }

