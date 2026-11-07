from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from packages.core.database import get_db
from packages.core.models import Opportunity, ApprovalQueue, Publication, AuditLog
from packages.schemas.opportunity import OpportunityResponse
from packages.schemas.approval import ApprovalActionRequest
from packages.publisher.telegram_publisher import TelegramPublisher
from packages.publisher.whatsapp_publisher import WhatsAppPublisher

router = APIRouter(prefix="/api/approvals", tags=["Approvals & Moderation"])

@router.get("/pending", response_model=List[OpportunityResponse])
async def list_pending_approvals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Opportunity)
        .where(Opportunity.status == "pending_approval")
        .order_by(desc(Opportunity.created_at))
    )
    return result.scalars().all()

@router.post("/{opportunity_id}/action")
async def process_approval_action(
    opportunity_id: int,
    action_data: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db)
):
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
        "apply_url": opp.apply_url,
        "requirements": opp.requirements,
        "summary": opp.summary,
        "deadline": opp.deadline,
        "verification_status": opp.verification_status
    }

    distribution_results = {}
    whatsapp_payload = None

    if action_data.action == "approve":
        opp.status = "approved"

        # 1. Publish to Telegram if requested
        if action_data.publish_telegram:
            pub_res = await TelegramPublisher.publish_opportunity(opp_dict, target_destination=action_data.telegram_target)
            distribution_results["telegram"] = pub_res
            
            # Record publication entry
            pub_entry = Publication(
                opportunity_id=opp.id,
                platform="telegram",
                destination_id=action_data.telegram_target,
                status="sent" if any(r.get("success") for r in pub_res.values()) else "failed",
                formatted_content=str(pub_res)
            )
            db.add(pub_entry)
            if any(r.get("success") for r in pub_res.values()):
                opp.status = "published"

        # 2. Generate WhatsApp copy-ready payload
        whatsapp_payload = WhatsAppPublisher.generate_copy_ready_payload(opp_dict)
        
        # Record WhatsApp publication staging
        wa_pub = Publication(
            opportunity_id=opp.id,
            platform="whatsapp_clipboard",
            status="pending_copy",
            formatted_content=whatsapp_payload["whatsapp_text"]
        )
        db.add(wa_pub)

    elif action_data.action == "reject":
        opp.status = "rejected"

    elif action_data.action == "edit" and action_data.edited_data:
        # Apply field edits
        for key, val in action_data.edited_data.items():
            if hasattr(opp, key) and val is not None:
                setattr(opp, key, val)
        opp.status = "approved"

    # Update or insert in ApprovalQueue
    approval_res = await db.execute(
        select(ApprovalQueue).where(ApprovalQueue.opportunity_id == opp.id)
    )
    approval_rec = approval_res.scalar_one_or_none()
    if approval_rec:
        approval_rec.status = action_data.action
        approval_rec.reviewed_by = action_data.reviewed_by
        approval_rec.feedback = action_data.feedback
        approval_rec.decided_at = datetime.utcnow()
    else:
        approval_rec = ApprovalQueue(
            opportunity_id=opp.id,
            status=action_data.action,
            reviewed_by=action_data.reviewed_by,
            feedback=action_data.feedback,
            decided_at=datetime.utcnow()
        )
        db.add(approval_rec)

    # Record Audit Log
    audit = AuditLog(
        action=f"OPPORTUNITY_{action_data.action.upper()}",
        entity_type="opportunity",
        entity_id=opp.id,
        actor=action_data.reviewed_by,
        details={"status": opp.status, "feedback": action_data.feedback}
    )
    db.add(audit)

    await db.commit()
    await db.refresh(opp)

    return {
        "status": "success",
        "opportunity_id": opp.id,
        "decision": action_data.action,
        "new_status": opp.status,
        "telegram_distribution": distribution_results,
        "whatsapp_ready": whatsapp_payload
    }
