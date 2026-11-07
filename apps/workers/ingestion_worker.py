import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from packages.core.database import AsyncSessionLocal
from packages.core.models import Source, Opportunity, OpportunityVersion, ApprovalQueue, AuditLog
from packages.intelligence.deduplicator import Deduplicator
from packages.intelligence.eligibility import EligibilityAnalyzer
from packages.intelligence.verifier import SourceVerifier
from packages.publisher.telegram_publisher import TelegramPublisher
from packages.core.config import settings

from packages.adapters.ethara import EtharaCareersAdapter
from packages.adapters.amazon import AmazonJobsAdapter
from packages.adapters.community import CommunitySubmissionAdapter
from packages.adapters.greenhouse import GreenhouseAdapter
from packages.adapters.lever import LeverAdapter
from packages.adapters.ashby import AshbyAdapter

class IngestionWorker:
    """
    Main Acquisition & Ingestion Engine.
    Executes source adapters, applies multi-stage deduplication,
    evaluates student batch eligibility, and queues verified jobs for distribution.
    """

    @classmethod
    def get_registered_adapters(cls) -> List[Any]:
        from packages.adapters.ats_directory import GREENHOUSE_BOARDS, LEVER_BOARDS, ASHBY_BOARDS
        
        adapters: List[Any] = [
            EtharaCareersAdapter(),
            AmazonJobsAdapter(),
            CommunitySubmissionAdapter(),
        ]
        # Register Tier-1 Startups and Tech companies on Greenhouse, Lever, and Ashby
        for gh in GREENHOUSE_BOARDS:
            adapters.append(GreenhouseAdapter(board_token=gh, company_name=gh.capitalize()))
        for lv in LEVER_BOARDS:
            adapters.append(LeverAdapter(company_slug=lv, company_name=lv.capitalize()))
        for ash in ASHBY_BOARDS:
            adapters.append(AshbyAdapter(company_slug=ash, company_name=ash.capitalize()))
            
        return adapters

    @classmethod
    async def process_single_opportunity(
        cls,
        session,
        opp_data,
        source_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Deduplicates, verifies, and stores an opportunity.
        """
        canonical_url = Deduplicator.canonicalize_url(opp_data.apply_url)
        url_hash = Deduplicator.hash_url(canonical_url)
        content_hash = Deduplicator.hash_content(opp_data.company, opp_data.title, opp_data.raw_description)
        norm_title = Deduplicator.normalize_title(opp_data.title)

        # 1. Stage 1 Deduplication: Exact URL Hash
        existing_res = await session.execute(
            select(Opportunity).where(Opportunity.canonical_url_hash == url_hash)
        )
        existing_opp = existing_res.scalar_one_or_none()

        if existing_opp:
            # Check for Reopening / Lifecycle change
            if existing_opp.status in ("closed", "expired", "rejected"):
                existing_opp.status = "pending_approval"
                version_entry = OpportunityVersion(
                    opportunity_id=existing_opp.id,
                    version_num=len(existing_opp.versions or []) + 1,
                    snapshot_data={"status": "reopened", "timestamp": str(datetime.utcnow())},
                    change_summary="Position reopened on career portal"
                )
                session.add(version_entry)
                await session.commit()
                return {"action": "reopened", "id": existing_opp.id, "title": existing_opp.title}
            return {"action": "skipped_duplicate_url", "id": existing_opp.id}

        # 2. Stage 2 Deduplication: Fuzzy Title + Company Match
        company_res = await session.execute(
            select(Opportunity).where(Opportunity.company.ilike(opp_data.company.strip()))
        )
        same_company_opps = company_res.scalars().all()
        for cand in same_company_opps:
            is_dup, reason, conf = Deduplicator.evaluate_duplicate_candidate(
                {"title": opp_data.title, "canonical_url_hash": url_hash, "locations": opp_data.locations, "company": opp_data.company},
                {"title": cand.title, "canonical_url_hash": cand.canonical_url_hash, "locations": cand.locations, "company": cand.company}
            )
            if is_dup:
                return {"action": "skipped_fuzzy_duplicate", "id": cand.id, "reason": reason}

        # 3. Eligibility Verification
        eligibility_meta = EligibilityAnalyzer.evaluate_target_match(
            title=opp_data.title,
            description=opp_data.raw_description or "",
            eligible_batches=opp_data.eligible_batches or []
        )

        # 4. Authority Verification
        ver_status, ver_ev = SourceVerifier.evaluate_url_authority(canonical_url)

        # 5. Insert New Opportunity
        new_opp = Opportunity(
            source_id=source_id,
            external_id=opp_data.external_id,
            company=opp_data.company,
            title=opp_data.title,
            normalized_title=norm_title,
            role_category=opp_data.role_category,
            locations=opp_data.locations or ["India / Remote"],
            eligible_batches=opp_data.eligible_batches or ["2026", "2027"],
            eligible_degrees=opp_data.eligible_degrees or ["B.Tech", "BE"],
            eligible_branches=opp_data.eligible_branches or ["CS", "IT", "All"],
            ctc_min=opp_data.ctc_min,
            ctc_max=opp_data.ctc_max,
            ctc_currency=opp_data.ctc_currency or "INR",
            ctc_text=opp_data.ctc_text or "Best in Industry",
            apply_url=canonical_url,
            canonical_url_hash=url_hash,
            content_hash=content_hash,
            raw_description=opp_data.raw_description,
            summary=opp_data.summary,
            requirements=opp_data.requirements or [],
            deadline=opp_data.deadline,
            status="pending_approval",
            confidence_score=opp_data.confidence_score or 1.0,
            verification_status=ver_status or opp_data.verification_status,
            verification_evidence={**opp_data.verification_evidence, "eligibility": eligibility_meta}
        )
        session.add(new_opp)
        await session.commit()
        await session.refresh(new_opp)

        # Add to Approval Queue
        approval_item = ApprovalQueue(
            opportunity_id=new_opp.id,
            status="pending"
        )
        session.add(approval_item)

        # Record Initial Version
        initial_version = OpportunityVersion(
            opportunity_id=new_opp.id,
            version_num=1,
            snapshot_data={"created": str(datetime.utcnow()), "title": new_opp.title},
            change_summary="Initial discovery and normalization"
        )
        session.add(initial_version)

        # Audit Log
        audit = AuditLog(
            action="OPPORTUNITY_DISCOVERED",
            entity_type="opportunity",
            entity_id=new_opp.id,
            actor="watchdog_worker",
            details={"company": new_opp.company, "title": new_opp.title}
        )
        session.add(audit)
        await session.commit()

        # Proactive Admin Notification if configured
        if settings.TELEGRAM_ADMIN_IDS and settings.TELEGRAM_BOT_TOKEN:
            admin_id = str(settings.TELEGRAM_ADMIN_IDS[0])
            asyncio.create_task(
                TelegramPublisher.send_admin_approval_card(
                    {
                        "id": new_opp.id,
                        "company": new_opp.company,
                        "title": new_opp.title,
                        "ctc_text": new_opp.ctc_text,
                        "apply_url": new_opp.apply_url,
                        "verification_status": new_opp.verification_status
                    },
                    admin_chat_id=admin_id
                )
            )

        return {"action": "created", "id": new_opp.id, "title": new_opp.title}

    @classmethod
    async def run_acquisition_cycle(cls, source_slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs one full scan across registered adapters.
        """
        adapters = cls.get_registered_adapters()
        if source_slug:
            adapters = [a for a in adapters if a.slug == source_slug]

        total_discovered = 0
        total_created = 0
        total_skipped = 0
        details = []

        async with AsyncSessionLocal() as session:
            for adapter in adapters:
                # Ensure Source entry exists in DB
                source_res = await session.execute(
                    select(Source).where(Source.slug == adapter.slug)
                )
                source_obj = source_res.scalar_one_or_none()
                if not source_obj:
                    source_obj = Source(
                        name=adapter.name,
                        slug=adapter.slug,
                        base_url=adapter.base_url,
                        check_interval_minutes=adapter.check_interval_minutes,
                        last_status="active"
                    )
                    session.add(source_obj)
                    await session.commit()
                    await session.refresh(source_obj)

                try:
                    opps = await adapter.fetch_opportunities()
                    adapter_created = 0
                    for opp_data in opps:
                        total_discovered += 1
                        res = await cls.process_single_opportunity(session, opp_data, source_id=source_obj.id)
                        if res.get("action") == "created":
                            total_created += 1
                            adapter_created += 1
                        else:
                            total_skipped += 1

                    source_obj.last_checked_at = datetime.utcnow()
                    source_obj.last_status = "ok"
                    source_obj.total_discovered += adapter_created
                    source_obj.error_message = None
                    await session.commit()

                    details.append({
                        "source": adapter.slug,
                        "status": "success",
                        "discovered": len(opps),
                        "created": adapter_created
                    })
                except Exception as e:
                    source_obj.last_checked_at = datetime.utcnow()
                    source_obj.last_status = "error"
                    source_obj.error_message = str(e)
                    await session.commit()
                    details.append({
                        "source": adapter.slug,
                        "status": "error",
                        "error": str(e)
                    })

        return {
            "total_scanned_sources": len(adapters),
            "total_items_discovered": total_discovered,
            "new_opportunities_created": total_created,
            "duplicates_skipped": total_skipped,
            "details": details
        }

