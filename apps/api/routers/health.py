from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from packages.core.database import get_db
from packages.core.models import Opportunity, Source, ApprovalQueue, Publication
from packages.core.config import settings

router = APIRouter(prefix="/api", tags=["Health & Analytics"])

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow(),
        "database": "connected",
        "telegram_configured": bool(settings.TELEGRAM_BOT_TOKEN)
    }

@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    # 1. Total Opportunities
    total_res = await db.execute(select(func.count(Opportunity.id)))
    total_count = total_res.scalar() or 0

    # 2. Pending Approvals
    pending_res = await db.execute(
        select(func.count(Opportunity.id)).where(Opportunity.status == "pending_approval")
    )
    pending_count = pending_res.scalar() or 0

    # 3. Approved / Published
    approved_res = await db.execute(
        select(func.count(Opportunity.id)).where(Opportunity.status.in_(["approved", "published"]))
    )
    approved_count = approved_res.scalar() or 0

    # 4. Active Sources
    sources_res = await db.execute(
        select(func.count(Source.id)).where(Source.is_active == True)
    )
    sources_count = sources_res.scalar() or 0

    # 5. Ethara Target Role Watchdog status
    ethara_res = await db.execute(
        select(Opportunity).where(Opportunity.company.ilike("%ethara%"))
    )
    ethara_opp = ethara_res.scalars().first()

    return {
        "total_discovered": total_count,
        "pending_approvals": pending_count,
        "published_approved": approved_count,
        "active_sources": sources_count,
        "ethara_target_status": {
            "tracked": True,
            "target_role": "LLM Post-Training – GenOPS",
            "package_limit": "6 LPA",
            "language_requirement": "Pure English Only",
            "latest_record_id": ethara_opp.id if ethara_opp else None,
            "status": ethara_opp.status if ethara_opp else "awaiting_opening"
        }
    }

