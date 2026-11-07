import asyncio
import logging
from typing import Dict, Any, Optional
import httpx
from packages.core.config import settings
from packages.core.database import AsyncSessionLocal
from packages.core.models import Opportunity
from packages.intelligence.formatter import ContentFormatter
from packages.adapters.community import CommunitySubmissionAdapter
from apps.workers.ingestion_worker import IngestionWorker
from sqlalchemy import select, desc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PlacementBot")

class PlacementTelegramBot:
    """
    aiogram-compatible / direct HTTP polling bot for Placement Intelligence Hub.
    """
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.offset = 0
        self.running = False

    async def api_call(self, method: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.token:
            return {"ok": False, "description": "Token not set"}
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=json_data)
                return resp.json()
        except Exception as e:
            return {"ok": False, "description": str(e)}

    async def handle_update(self, update: Dict[str, Any]):
        # Message handling
        if "message" in update:
            msg = update["message"]
            chat_id = str(msg["chat"]["id"])
            text = msg.get("text", "").strip()

            if text.startswith("/start"):
                welcome = (
                    "🎓 *Welcome to the Placement Intelligence Hub Bot!*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Automated multi-source placement radar for batch 2026/2027.\n\n"
                    "📌 *Commands Available:*\n"
                    "• `/status` - Live system statistics & watchdog status\n"
                    "• `/pending` - Review jobs awaiting admin approval\n"
                    "• `/submit <text_or_url>` - Submit any hiring link or message\n"
                    "• `/scan` - Trigger an immediate career portal scan\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Target Track: *Ethara.AI LLM Post-Training GenOPS (6 LPA)*"
                )
                await self.api_call("sendMessage", {"chat_id": chat_id, "text": welcome, "parse_mode": "Markdown"})

            elif text.startswith("/status"):
                async with AsyncSessionLocal() as session:
                    res = await session.execute(select(Opportunity))
                    all_opps = res.scalars().all()
                    pending = sum(1 for o in all_opps if o.status == "pending_approval")
                    published = sum(1 for o in all_opps if o.status in ("approved", "published"))
                    
                    status_text = (
                        "📊 *[PLACEMENT HUB TELEMETRY]*\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📁 Total Opportunities: `{len(all_opps)}`\n"
                        f"⏳ Pending Approvals: `{pending}`\n"
                        f"🚀 Published / Approved: `{published}`\n"
                        "🎯 *Target Watchdog:*\n"
                        "• Ethara.AI GenOPS: `ACTIVE SCANNING`\n"
                        "• Amazon University: `ACTIVE SCANNING`\n"
                        "• College Batch: `2026 & 2027`\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    )
                    await self.api_call("sendMessage", {"chat_id": chat_id, "text": status_text, "parse_mode": "Markdown"})

            elif text.startswith("/pending"):
                async with AsyncSessionLocal() as session:
                    res = await session.execute(
                        select(Opportunity).where(Opportunity.status == "pending_approval").order_by(desc(Opportunity.created_at)).limit(5)
                    )
                    pending_opps = res.scalars().all()
                    if not pending_opps:
                        await self.api_call("sendMessage", {"chat_id": chat_id, "text": "✅ No pending approvals right now!"})
                        return

                    for opp in pending_opps:
                        card = ContentFormatter.format_telegram_markdown({
                            "company": opp.company,
                            "title": opp.title,
                            "locations": opp.locations,
                            "eligible_batches": opp.eligible_batches,
                            "ctc_text": opp.ctc_text,
                            "apply_url": opp.apply_url,
                            "requirements": opp.requirements,
                            "role_category": opp.role_category
                        })
                        keyboard = {
                            "inline_keyboard": [
                                [
                                    {"text": "✅ Approve & Broadcast", "callback_data": f"approve_{opp.id}"},
                                    {"text": "❌ Reject", "callback_data": f"reject_{opp.id}"}
                                ],
                                [
                                    {"text": "📋 Preview WhatsApp Card", "callback_data": f"wa_{opp.id}"}
                                ]
                            ]
                        }
                        await self.api_call("sendMessage", {
                            "chat_id": chat_id,
                            "text": card,
                            "parse_mode": "Markdown",
                            "reply_markup": keyboard
                        })

            elif text.startswith("/submit"):
                content = text.replace("/submit", "").strip()
                if not content:
                    await self.api_call("sendMessage", {"chat_id": chat_id, "text": "⚠️ Usage: `/submit <job link or full message>`", "parse_mode": "Markdown"})
                    return

                opp_data = CommunitySubmissionAdapter.parse_raw_text_submission(content, submitter="Telegram Bot User")
                if opp_data:
                    async with AsyncSessionLocal() as session:
                        result = await IngestionWorker.process_single_opportunity(session, opp_data)
                        msg_reply = f"✅ *Submission Processed!*\n• Action: `{result.get('action')}`\n• Company: *{opp_data.company}*\n• Title: *{opp_data.title}*\n• Batches: `{', '.join(opp_data.eligible_batches)}`"
                        await self.api_call("sendMessage", {"chat_id": chat_id, "text": msg_reply, "parse_mode": "Markdown"})
                else:
                    await self.api_call("sendMessage", {"chat_id": chat_id, "text": "❌ Could not parse submission. Please include a title and apply link."})

            elif text.startswith("/scan"):
                await self.api_call("sendMessage", {"chat_id": chat_id, "text": "🔄 *Starting immediate acquisition cycle across all sources...*", "parse_mode": "Markdown"})
                res = await IngestionWorker.run_acquisition_cycle()
                reply = f"✅ *Scan Complete!*\n• Total Discovered: `{res['total_items_discovered']}`\n• New Created: `{res['new_opportunities_created']}`\n• Duplicates Skipped: `{res['duplicates_skipped']}`"
                await self.api_call("sendMessage", {"chat_id": chat_id, "text": reply, "parse_mode": "Markdown"})

        # Callback query handling (Inline button clicks)
        elif "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb["id"]
            data = cb.get("data", "")
            chat_id = str(cb["message"]["chat"]["id"])

            if data.startswith("approve_"):
                opp_id = int(data.split("_")[1])
                async with AsyncSessionLocal() as session:
                    res = await session.execute(select(Opportunity).where(Opportunity.id == opp_id))
                    opp = res.scalar_one_or_none()
                    if opp:
                        opp.status = "approved"
                        await session.commit()
                        await self.api_call("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Approved and queued for broadcast!"})
                        await self.api_call("sendMessage", {"chat_id": chat_id, "text": f"🎉 *Approved opportunity #{opp_id} ({opp.company} - {opp.title})!*", "parse_mode": "Markdown"})

            elif data.startswith("reject_"):
                opp_id = int(data.split("_")[1])
                async with AsyncSessionLocal() as session:
                    res = await session.execute(select(Opportunity).where(Opportunity.id == opp_id))
                    opp = res.scalar_one_or_none()
                    if opp:
                        opp.status = "rejected"
                        await session.commit()
                        await self.api_call("answerCallbackQuery", {"callback_query_id": cb_id, "text": "Rejected."})
                        await self.api_call("sendMessage", {"chat_id": chat_id, "text": f"❌ Opportunity #{opp_id} rejected."})

            elif data.startswith("wa_"):
                opp_id = int(data.split("_")[1])
                async with AsyncSessionLocal() as session:
                    res = await session.execute(select(Opportunity).where(Opportunity.id == opp_id))
                    opp = res.scalar_one_or_none()
                    if opp:
                        wa_card = ContentFormatter.format_whatsapp_card({
                            "company": opp.company,
                            "title": opp.title,
                            "locations": opp.locations,
                            "eligible_batches": opp.eligible_batches,
                            "ctc_text": opp.ctc_text,
                            "apply_url": opp.apply_url,
                            "requirements": opp.requirements
                        })
                        await self.api_call("answerCallbackQuery", {"callback_query_id": cb_id})
                        await self.api_call("sendMessage", {
                            "chat_id": chat_id,
                            "text": f"📋 *WhatsApp Ready Card (Click to Copy):*\n\n`{wa_card}`",
                            "parse_mode": "Markdown"
                        })

    async def start_polling(self):
        if not self.token:
            logger.warning("Telegram Bot Token is not set. Bot polling will remain idle until token is supplied in .env")
            return
        self.running = True
        logger.info("🤖 Telegram Bot Polling started...")
        while self.running:
            try:
                res = await self.api_call("getUpdates", {"offset": self.offset, "timeout": 10})
                if res.get("ok"):
                    for update in res.get("result", []):
                        self.offset = update["update_id"] + 1
                        await self.handle_update(update)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    bot = PlacementTelegramBot()
    asyncio.run(bot.start_polling())
