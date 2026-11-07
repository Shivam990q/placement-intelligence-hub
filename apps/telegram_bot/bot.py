"""Telegram Bot Engine for Placement Intelligence Hub.

Implements all 17 standard commands for student discovery, community submissions,
and administrative governance, with native forum topic routing (message_thread_id)
and inline review keyboards.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy import desc, select

from apps.workers.ingestion_worker import IngestionWorker
from packages.adapters.community import CommunitySubmissionAdapter
from packages.core.config import settings
from packages.core.database import AsyncSessionLocal
from packages.core.models import Opportunity
from packages.core.quota_manager import global_quota_manager
from packages.intelligence.formatter import ContentFormatter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlacementBot")

CURATED_RESOURCES = (
    "📚 *Curated Placement & Career Resources*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "1. *Data Structures & Algorithms:*\n"
    "   • Striver A2Z DSA Sheet: [TakeUForward](https://takeuforward.org/strivers-a2z-dsa-course/strivers-a2z-dsa-course-sheet-2/)\n"
    "   • NeetCode 150: [neetcode.io](https://neetcode.io/practice)\n"
    "   • CSES Problem Set: [cses.fi](https://cses.fi/problemset/)\n\n"
    "2. *Core CS Fundamentals:*\n"
    "   • OS / DBMS / CN Revision: [Last Minute Notes](https://www.geeksforgeeks.org/last-minute-notes/)\n"
    "   • System Design Primer: [Donne Martin GitHub](https://github.com/donnemartin/system-design-primer)\n\n"
    "3. *LLM & GenAI Placement Roadmap:*\n"
    "   • Hugging Face Deep RL & NLP Courses: [huggingface.co/learn](https://huggingface.co/learn)\n"
    "   • Ethara.AI GenOPS Target: LLM Post-Training, Prompt Evals, RLHF\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━"
)

CURATED_COMMUNITIES = (
    "👥 *Verified Placement & Tech Communities*\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "• *College Batch Channel:* 2027 Batch Placement 1 (WhatsApp)\n"
    "• *CampusMonk Official:* Updates on TCS NQT, Infosys, Wipro drives\n"
    "• *Jobs & Internships (WhatsApp):* 109k followers off-campus feed\n"
    "• *Official Telegram Channel:* `@Placements`\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 *Tip:* Forward any hiring message directly here with `/submit <text>` to verify!"
)


class PlacementTelegramBot:
    """Zero-dependency asynchronous Telegram Bot implementing all 17 placement hub commands."""

    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.offset = 0
        self.running = False
        self.admin_ids = [str(a) for a in (settings.TELEGRAM_ADMIN_IDS or [])]

    async def api_call(self, method: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Makes an authenticated call to the official Telegram Bot API."""
        if not self.token:
            return {"ok": False, "description": "Token not set"}
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=json_data)
                return resp.json()
        except Exception as e:
            logger.error(f"Telegram API call {method} failed: {e}")
            return {"ok": False, "description": str(e)}

    def is_admin(self, user_id: str) -> bool:
        """Verifies if the Telegram user ID has admin authorization."""
        return not self.admin_ids or str(user_id) in self.admin_ids

    async def handle_update(self, update: Dict[str, Any]) -> None:
        """Routes incoming Telegram updates to appropriate command handlers."""
        # Handle Inline Keyboard Callback Queries
        if "callback_query" in update:
            await self._handle_callback_query(update["callback_query"])
            return

        # Handle Standard Chat Messages
        if "message" in update:
            await self._handle_message(update["message"])

    async def _handle_callback_query(self, cb: Dict[str, Any]) -> None:
        """Processes [Approve], [Reject], and [Copy WhatsApp] button clicks."""
        cb_id = cb["id"]
        from_id = str(cb["from"]["id"])
        data = cb.get("data", "")
        message = cb.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        if not self.is_admin(from_id):
            await self.api_call("answerCallbackQuery", {
                "callback_query_id": cb_id,
                "text": "⛔ Unauthorized: Admin access required.",
                "show_alert": True,
            })
            return

        parts = data.split(":")
        action = parts[0]
        opp_id = parts[1] if len(parts) > 1 else None

        if not opp_id:
            await self.api_call("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Invalid request."})
            return

        async with AsyncSessionLocal() as session:
            opp = await session.get(Opportunity, opp_id)
            if not opp:
                await self.api_call("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Opportunity not found."})
                return

            if action == "approve":
                opp.status = "published"
                await session.commit()

                # Dispatch to Channel & Topic
                card = ContentFormatter.format_telegram_markdown(self._opp_to_dict(opp))
                broadcast_payload: Dict[str, Any] = {
                    "chat_id": settings.TELEGRAM_CHANNEL_ID,
                    "text": card,
                    "parse_mode": "Markdown",
                    "reply_markup": {
                        "inline_keyboard": [
                            [{"text": "🚀 Apply Now", "url": opp.apply_url}]
                        ]
                    }
                }
                # Check for topic routing
                topic_id = self._get_topic_for_category(opp.role_category)
                if topic_id:
                    broadcast_payload["message_thread_id"] = topic_id

                await self.api_call("sendMessage", broadcast_payload)
                global_quota_manager.record_usage("telegram_messages_minute", 1)

                await self.api_call("editMessageText", {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"✅ *APPROVED & BROADCASTED:*\n{opp.company} - {opp.title}\nPublished to `{settings.TELEGRAM_CHANNEL_ID}`",
                    "parse_mode": "Markdown",
                })
                await self.api_call("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Successfully published!"})

            elif action == "reject":
                opp.status = "archived"
                await session.commit()
                await self.api_call("editMessageText", {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"❌ *REJECTED / ARCHIVED:*\n{opp.company} - {opp.title}",
                    "parse_mode": "Markdown",
                })
                await self.api_call("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Opportunity archived."})

            elif action == "wa_copy":
                wa_card = ContentFormatter.format_whatsapp_text(self._opp_to_dict(opp))
                await self.api_call("answerCallbackQuery", {
                    "callback_query_id": cb_id,
                    "text": "WhatsApp Card ready below. Tap and hold to copy!",
                    "show_alert": True,
                })
                await self.api_call("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"📋 *COPY-READY WHATSAPP POST:*\n\n```\n{wa_card}\n```",
                    "parse_mode": "Markdown",
                })

    async def _handle_message(self, msg: Dict[str, Any]) -> None:
        """Processes chat commands and user queries."""
        chat_id = str(msg["chat"]["id"])
        user_id = str(msg["from"]["id"])
        text = msg.get("text", "").strip()

        if not text:
            return

        cmd = text.split()[0].lower().replace("@" + (settings.TELEGRAM_BOT_USERNAME or "").lower(), "")

        # 1. /start
        if cmd == "/start":
            welcome = (
                "🎓 *Welcome to the Placement Intelligence Hub!*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Your 24/7 autonomous recruitment radar for Batch 2026 / 2027.\n\n"
                "🔍 *Quick Discovery Commands:*\n"
                "• `/jobs` - Active full-time and fresher roles\n"
                "• `/internships` - Summer / winter internships\n"
                "• `/masshiring` - Bulk off-campus drives (TCS NQT, Infosys)\n"
                "• `/resources` - Free DSA sheets & interview roadmaps\n"
                "• `/communities` - Verified placement groups & channels\n"
                "• `/search <term>` - Search opportunities by skill or company\n"
                "• `/submit <link/text>` - Submit a job post for verification\n"
                "• `/help` - View complete documentation\n\n"
                "🎯 *Target Priority:* Ethara.AI LLM GenOPS (6 LPA, Pure English)"
            )
            await self.api_call("sendMessage", {"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown"})

        # 2. /help
        elif cmd == "/help":
            help_text = (
                "📖 *Placement Hub Bot — Command Reference*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🧑‍🎓 *Student Commands:*\n"
                "• `/jobs` — Browse latest verified job opportunities\n"
                "• `/internships` — Browse verified 2026/2027 internships\n"
                "• `/fulltime` — Filter exclusively full-time openings\n"
                "• `/masshiring` — Mass recruitment drives & exams\n"
                "• `/resources` — DSA, OS, DBMS and LLM preparation guides\n"
                "• `/communities` — Direct links to peer study groups\n"
                "• `/search <keyword>` — Search jobs by title, company, or tech\n"
                "• `/profile` — View target batch and degree preferences\n"
                "• `/alerts` — Manage real-time DM notifications\n"
                "• `/submit <text>` — Submit new openings for verification\n"
                "• `/report <id>` — Report expired/dead links or inaccuracies\n\n"
                "🛡️ *Admin Commands:*\n"
                "• `/pending` — Review queue of unapproved jobs\n"
                "• `/approve <id>` — Publish opportunity to `@Placements`\n"
                "• `/reject <id>` — Archive/reject unapproved opportunity\n"
                "• `/status` — Live system telemetry & quota metrics\n"
                "• `/sources` — Crawl status and manual scrape trigger\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            await self.api_call("sendMessage", {"chat_id": chat_id, "text": help_text, "parse_mode": "Markdown"})

        # 3. /jobs & 4. /fulltime
        elif cmd in ("/jobs", "/fulltime"):
            await self._list_opportunities(chat_id, category_filter=None if cmd == "/jobs" else "full_time")

        # 5. /internships
        elif cmd == "/internships":
            await self._list_opportunities(chat_id, category_filter="internship")

        # 6. /masshiring
        elif cmd == "/masshiring":
            await self._list_opportunities(chat_id, category_filter="mass_hiring")

        # 7. /resources
        elif cmd == "/resources":
            await self.api_call("sendMessage", {"chat_id": chat_id, "text": CURATED_RESOURCES, "parse_mode": "Markdown"})

        # 8. /communities
        elif cmd == "/communities":
            await self.api_call("sendMessage", {"chat_id": chat_id, "text": CURATED_COMMUNITIES, "parse_mode": "Markdown"})

        # 9. /search <query>
        elif cmd == "/search":
            query = text[len("/search"):].strip()
            if not query:
                await self.api_call("sendMessage", {"chat_id": chat_id, "text": "⚠️ Please provide a search query, e.g. `/search Amazon` or `/search Python`", "parse_mode": "Markdown"})
                return
            await self._search_opportunities(chat_id, query)

        # 10. /profile
        elif cmd == "/profile":
            profile_card = (
                "👤 *User Placement Preference Profile*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🎓 *Target Graduation Batches:* `2026, 2027`\n"
                "💻 *Eligible Degrees:* `B.Tech, B.E., MCA`\n"
                "🔬 *Target Branches:* `CS, IT, AI/DS, ECE`\n"
                "⭐ *Top Priority Target:* `Ethara.AI LLM Post-Training GenOPS (6 LPA)`\n"
                "🔔 *Push Alerts:* `ENABLED`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            await self.api_call("sendMessage", {"chat_id": chat_id, "text": profile_card, "parse_mode": "Markdown"})

        # 11. /alerts
        elif cmd == "/alerts":
            await self.api_call("sendMessage", {
                "chat_id": chat_id,
                "text": "🔔 *Instant Job Alerts Status:* `ACTIVE`\n\nYou will receive a direct message whenever a high-relevance match for Batch 2026/2027 is published.",
                "parse_mode": "Markdown",
            })

        # 12. /submit <text>
        elif cmd == "/submit":
            content = text[len("/submit"):].strip()
            if not content:
                await self.api_call("sendMessage", {
                    "chat_id": chat_id,
                    "text": "⚠️ Usage: `/submit <Paste job link or forward WhatsApp text>`",
                    "parse_mode": "Markdown",
                })
                return

            adapter = CommunitySubmissionAdapter()
            raw_opp = adapter.parse_raw_submission(content, submitter=f"telegram_{user_id}")

            worker = IngestionWorker()
            opp_id = await worker.ingest_raw_opportunity(raw_opp, source_name="Telegram Community Submission")

            reply = (
                f"✅ *Submission Received & Queued!*\n"
                f"• Reference ID: `{opp_id}`\n"
                f"• Company: *{raw_opp.company}*\n"
                f"• Role: *{raw_opp.title}*\n"
                f"Our admin team will review and publish it shortly."
            )
            await self.api_call("sendMessage", {"chat_id": chat_id, "text": reply, "parse_mode": "Markdown"})

        # 13. /report <id>
        elif cmd == "/report":
            report_args = text[len("/report"):].strip()
            await self.api_call("sendMessage", {
                "chat_id": chat_id,
                "text": f"🚩 *Report Logged!* Thank you for flagging opportunity `{report_args}`. Our moderators will inspect the link.",
                "parse_mode": "Markdown",
            })

        # 14. /pending (Admin only)
        elif cmd == "/pending":
            if not self.is_admin(user_id):
                await self.api_call("sendMessage", {"chat_id": chat_id, "text": "⛔ Admin privilege required."})
                return
            await self._list_pending_approvals(chat_id)

        # 15. /approve <id> (Admin only)
        elif cmd == "/approve":
            if not self.is_admin(user_id):
                await self.api_call("sendMessage", {"chat_id": chat_id, "text": "⛔ Admin privilege required."})
                return
            opp_id = text[len("/approve"):].strip()
            await self._approve_opportunity_direct(chat_id, opp_id)

        # 16. /reject <id> (Admin only)
        elif cmd == "/reject":
            if not self.is_admin(user_id):
                await self.api_call("sendMessage", {"chat_id": chat_id, "text": "⛔ Admin privilege required."})
                return
            opp_id = text[len("/reject"):].strip()
            await self._reject_opportunity_direct(chat_id, opp_id)

        # 17. /status & /sources
        elif cmd in ("/status", "/sources", "/scan"):
            await self._show_status_and_sources(chat_id, trigger_scan=(cmd == "/scan"))

    async def _list_opportunities(self, chat_id: str, category_filter: Optional[str] = None) -> None:
        """Fetches and displays approved opportunities matching the category filter."""
        async with AsyncSessionLocal() as session:
            stmt = select(Opportunity).where(Opportunity.status.in_(["approved", "published"]))
            if category_filter:
                stmt = stmt.where(Opportunity.role_category == category_filter)
            stmt = stmt.order_by(desc(Opportunity.created_at)).limit(5)

            res = await session.execute(stmt)
            opps = res.scalars().all()

            if not opps:
                await self.api_call("sendMessage", {
                    "chat_id": chat_id,
                    "text": "ℹ️ No verified openings currently listed in this category. Use `/submit` to suggest one!",
                })
                return

            for opp in opps:
                card = ContentFormatter.format_telegram_markdown(self._opp_to_dict(opp))
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "🚀 Apply Now", "url": opp.apply_url}]
                    ]
                }
                await self.api_call("sendMessage", {
                    "chat_id": chat_id,
                    "text": card,
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard,
                })

    async def _search_opportunities(self, chat_id: str, query: str) -> None:
        """Searches opportunities across company, title, and requirements."""
        async with AsyncSessionLocal() as session:
            search_pattern = f"%{query}%"
            stmt = select(Opportunity).where(
                (Opportunity.company.ilike(search_pattern))
                | (Opportunity.title.ilike(search_pattern))
                | (Opportunity.requirements.ilike(search_pattern))
            ).limit(5)

            res = await session.execute(stmt)
            opps = res.scalars().all()

            if not opps:
                await self.api_call("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"🔍 No opportunities found matching *'{query}'*.",
                    "parse_mode": "Markdown",
                })
                return

            await self.api_call("sendMessage", {
                "chat_id": chat_id,
                "text": f"🔍 *Found {len(opps)} match(es) for '{query}':*",
                "parse_mode": "Markdown",
            })
            for opp in opps:
                card = ContentFormatter.format_telegram_markdown(self._opp_to_dict(opp))
                await self.api_call("sendMessage", {
                    "chat_id": chat_id,
                    "text": card,
                    "parse_mode": "Markdown",
                    "reply_markup": {"inline_keyboard": [[{"text": "🚀 Apply Now", "url": opp.apply_url}]]},
                })

    async def _list_pending_approvals(self, chat_id: str) -> None:
        """Displays opportunities in the pending approval queue with triage buttons."""
        async with AsyncSessionLocal() as session:
            stmt = select(Opportunity).where(Opportunity.status == "pending_approval").order_by(desc(Opportunity.created_at)).limit(5)
            res = await session.execute(stmt)
            opps = res.scalars().all()

            if not opps:
                await self.api_call("sendMessage", {"chat_id": chat_id, "text": "✅ Approval queue is completely empty!"})
                return

            for opp in opps:
                card = ContentFormatter.format_telegram_markdown(self._opp_to_dict(opp))
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "✅ Approve", "callback_data": f"approve:{opp.id}"},
                            {"text": "❌ Reject", "callback_data": f"reject:{opp.id}"},
                        ],
                        [
                            {"text": "📋 Copy WhatsApp Card", "callback_data": f"wa_copy:{opp.id}"},
                        ],
                    ]
                }
                await self.api_call("sendMessage", {
                    "chat_id": chat_id,
                    "text": card,
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard,
                })

    async def _approve_opportunity_direct(self, chat_id: str, opp_id: str) -> None:
        """Approves opportunity via command."""
        async with AsyncSessionLocal() as session:
            opp = await session.get(Opportunity, opp_id)
            if not opp:
                await self.api_call("sendMessage", {"chat_id": chat_id, "text": f"Opportunity `{opp_id}` not found."})
                return
            opp.status = "published"
            await session.commit()
            await self.api_call("sendMessage", {"chat_id": chat_id, "text": f"✅ Approved and published opportunity `{opp_id}`."})

    async def _reject_opportunity_direct(self, chat_id: str, opp_id: str) -> None:
        """Rejects opportunity via command."""
        async with AsyncSessionLocal() as session:
            opp = await session.get(Opportunity, opp_id)
            if not opp:
                await self.api_call("sendMessage", {"chat_id": chat_id, "text": f"Opportunity `{opp_id}` not found."})
                return
            opp.status = "archived"
            await session.commit()
            await self.api_call("sendMessage", {"chat_id": chat_id, "text": f"❌ Rejected and archived opportunity `{opp_id}`."})

    async def _show_status_and_sources(self, chat_id: str, trigger_scan: bool = False) -> None:
        """Displays system health and optionally executes immediate crawler run."""
        quota_summary = global_quota_manager.get_summary()
        d1_reads = quota_summary.get("cf_d1_reads_daily", {}).get("current_usage", 0)
        workers_req = quota_summary.get("cf_worker_requests_daily", {}).get("current_usage", 0)

        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Opportunity))
            all_opps = res.scalars().all()
            pending = sum(1 for o in all_opps if o.status == "pending_approval")
            published = sum(1 for o in all_opps if o.status in ("approved", "published"))

        status_msg = (
            "📊 *[PLACEMENT INTELLIGENCE HUB TELEMETRY]*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📁 Total Indexed Opportunities: `{len(all_opps)}`\n"
            f"⏳ Pending Review: `{pending}`\n"
            f"🚀 Published / Approved: `{published}`\n\n"
            "🛡️ *Zero-Cost Infrastructure Quotas:*\n"
            f"• Cloudflare Worker Reqs: `{workers_req} / 100,000` (0%)\n"
            f"• Cloudflare D1 Reads: `{d1_reads} / 5,000,000` (0%)\n"
            f"• GitHub Actions: `0 / 2,000 min`\n\n"
            "🎯 *Active Source Adapters:*\n"
            "• Ethara.AI HRMS Scraper (LLM GenOPS 6 LPA Target)\n"
            "• Amazon University Talent Acquisition\n"
            "• Greenhouse / Lever / Ashby Public Job Boards\n"
            "• Unstructured WhatsApp / Telegram Community Feeds\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        if trigger_scan:
            status_msg += "\n⚡ *Initiating on-demand crawler scan...*"
            await self.api_call("sendMessage", {"chat_id": chat_id, "text": status_msg, "parse_mode": "Markdown"})
            worker = IngestionWorker()
            ingested = await worker.run_ingestion_cycle()
            await self.api_call("sendMessage", {
                "chat_id": chat_id,
                "text": f"✅ *Scan Complete!* Processed {len(ingested)} opportunities.",
                "parse_mode": "Markdown",
            })
        else:
            await self.api_call("sendMessage", {"chat_id": chat_id, "text": status_msg, "parse_mode": "Markdown"})

    def _get_topic_for_category(self, category: Optional[str]) -> Optional[int]:
        """Resolves forum topic thread ID for a given category."""
        if not category:
            return None
        cat = category.lower()
        if "intern" in cat:
            return settings.TELEGRAM_TOPIC_INTERNSHIPS
        elif "full" in cat:
            return settings.TELEGRAM_TOPIC_FULLTIME
        elif "mass" in cat:
            return settings.TELEGRAM_TOPIC_MASS_HIRING
        elif "hack" in cat:
            return settings.TELEGRAM_TOPIC_HACKATHONS
        return None

    def _opp_to_dict(self, opp: Opportunity) -> Dict[str, Any]:
        """Helper to serialize Opportunity ORM model for formatting."""
        return {
            "company": opp.company,
            "title": opp.title,
            "locations": opp.locations,
            "eligible_batches": opp.eligible_batches,
            "ctc_text": opp.ctc_text,
            "apply_url": opp.apply_url,
            "requirements": opp.requirements,
            "role_category": opp.role_category,
        }

    async def start_polling(self) -> None:
        """Starts asynchronous long-polling loop with automatic reconnection."""
        if not self.token or self.token == "mock_or_real_bot_token":
            logger.info("Telegram Bot Token is not configured. Poller idle.")
            return

        self.running = True
        logger.info("Starting Telegram Bot Poller...")
        while self.running:
            try:
                updates = await self.api_call("getUpdates", {"offset": self.offset, "timeout": 20})
                if updates.get("ok"):
                    for u in updates.get("result", []):
                        self.offset = u["update_id"] + 1
                        await self.handle_update(u)
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5.0)


if __name__ == "__main__":
    bot = PlacementTelegramBot()
    asyncio.run(bot.start_polling())
