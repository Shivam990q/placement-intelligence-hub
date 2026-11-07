from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc
from packages.core.database import get_db
from packages.core.models import Opportunity, AuditLog
from packages.schemas.opportunity import OpportunityResponse, OpportunityCreate, OpportunityUpdate
from packages.intelligence.deduplicator import Deduplicator
from packages.intelligence.formatter import ContentFormatter

router = APIRouter(prefix="/api/opportunities", tags=["Opportunities"])

@router.get("", response_model=List[OpportunityResponse])
async def list_opportunities(
    search: Optional[str] = Query(None, description="Search company, title, or keywords"),
    batch: Optional[str] = Query(None, description="Filter by batch (e.g. 2026, 2027)"),
    role_category: Optional[str] = Query(None, description="internship, full_time, genai_ops, mass_hiring, resource"),
    status: Optional[str] = Query(None, description="discovered, pending_approval, approved, published, rejected"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(Opportunity).order_by(desc(Opportunity.created_at))

    conditions = []
    if search:
        s_term = f"%{search.strip().lower()}%"
        conditions.append(or_(
            Opportunity.company.ilike(s_term),
            Opportunity.title.ilike(s_term),
            Opportunity.summary.ilike(s_term)
        ))
    if role_category:
        conditions.append(Opportunity.role_category == role_category)
    if status:
        conditions.append(Opportunity.status == status)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    opportunities = result.scalars().all()

    # In-memory batch filtering if batch specified
    if batch:
        opportunities = [
            opp for opp in opportunities 
            if batch in (opp.eligible_batches or []) or "Freshers" in (opp.eligible_batches or [])
        ]

    return opportunities

@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(opportunity_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp

@router.get("/{opportunity_id}/formats")
async def get_opportunity_formatted_cards(opportunity_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opp_dict = {
        "id": opp.id,
        "company": opp.company,
        "title": opp.title,
        "role_category": opp.role_category,
        "locations": opp.locations,
        "eligible_batches": opp.eligible_batches,
        "ctc_text": opp.ctc_text,
        "ctc_min": opp.ctc_min,
        "ctc_max": opp.ctc_max,
        "apply_url": opp.apply_url,
        "requirements": opp.requirements,
        "summary": opp.summary,
        "deadline": opp.deadline
    }

    return {
        "opportunity_id": opp.id,
        "company": opp.company,
        "title": opp.title,
        "telegram_markdown": ContentFormatter.format_telegram_markdown(opp_dict),
        "whatsapp_card": ContentFormatter.format_whatsapp_card(opp_dict)
    }

@router.post("", response_model=OpportunityResponse)
async def create_opportunity(data: OpportunityCreate, db: AsyncSession = Depends(get_db)):
    # Calculate hashes
    canonical_url = Deduplicator.canonicalize_url(data.apply_url)
    url_hash = Deduplicator.hash_url(canonical_url)
    content_hash = Deduplicator.hash_content(data.company, data.title, data.raw_description)
    norm_title = Deduplicator.normalize_title(data.title)

    opp = Opportunity(
        source_id=data.source_id,
        external_id=data.external_id,
        company=data.company,
        title=data.title,
        normalized_title=norm_title,
        role_category=data.role_category,
        locations=data.locations,
        eligible_batches=data.eligible_batches,
        eligible_degrees=data.eligible_degrees,
        eligible_branches=data.eligible_branches,
        ctc_min=data.ctc_min,
        ctc_max=data.ctc_max,
        ctc_currency=data.ctc_currency,
        ctc_text=data.ctc_text,
        apply_url=canonical_url or data.apply_url,
        canonical_url_hash=url_hash,
        content_hash=content_hash,
        raw_description=data.raw_description,
        summary=data.summary,
        requirements=data.requirements,
        deadline=data.deadline,
        status=data.status,
        confidence_score=data.confidence_score,
        verification_status=data.verification_status,
        verification_evidence=data.verification_evidence
    )
    db.add(opp)
    await db.commit()
    await db.refresh(opp)

    # Log audit
    audit = AuditLog(
        action="OPPORTUNITY_CREATED",
        entity_type="opportunity",
        entity_id=opp.id,
        actor="system",
        details={"company": opp.company, "title": opp.title}
    )
    db.add(audit)
    await db.commit()

    return opp
