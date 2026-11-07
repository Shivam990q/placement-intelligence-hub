import json
from typing import Dict, Any, Optional, Tuple
import httpx
from packages.core.config import settings
from packages.intelligence.formatter import ContentFormatter

class TelegramPublisher:
    """
    Direct Telegram Bot API Publisher.
    Publishes to:
    1. Telegram Broadcast Channel (@Placements)
    2. Forum Supergroup with specific message_thread_id per category
    3. Admin review chat with interactive Inline Keyboard [Approve] / [Reject]
    """
    BASE_URL = "https://api.telegram.org/bot{token}"

    @classmethod
    def get_api_url(cls, method: str) -> str:
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            return ""
        return f"https://api.telegram.org/bot{token}/{method}"

    @classmethod
    def resolve_topic_id(cls, role_category: str) -> Optional[int]:
        cat = role_category.lower()
        if "intern" in cat:
            return settings.TELEGRAM_TOPIC_INTERNSHIPS
        elif "full" in cat:
            return settings.TELEGRAM_TOPIC_FULLTIME
        elif "mass" in cat:
            return settings.TELEGRAM_TOPIC_MASSHIRING
        elif "genai" in cat or "llm" in cat:
            return settings.TELEGRAM_TOPIC_GENAI_OPS
        elif "resource" in cat:
            return settings.TELEGRAM_TOPIC_RESOURCES
        return settings.TELEGRAM_TOPIC_DISCUSSIONS

    @classmethod
    async def send_message(
        cls,
        chat_id: str,
        text: str,
        message_thread_id: Optional[int] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = "Markdown"
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Sends message to Telegram via official Bot API.
        Returns: (success: bool, message_id: Optional[str], error: Optional[str])
        """
        url = cls.get_api_url("sendMessage")
        if not url:
            return False, None, "TELEGRAM_BOT_TOKEN not configured"

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }
        if message_thread_id:
            payload["message_thread_id"] = message_thread_id
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
                if resp.status_code == 200 and data.get("ok"):
                    msg_id = str(data["result"]["message_id"])
                    return True, msg_id, None
                else:
                    return False, None, data.get("description", resp.text)
        except Exception as e:
            return False, None, str(e)

    @classmethod
    async def publish_opportunity(
        cls,
        opp: Dict[str, Any],
        target_destination: str = "both"
    ) -> Dict[str, Any]:
        """
        Publishes verified opportunity to:
        - Telegram Channel (Broadcast)
        - Telegram Forum Topic (Categorized Discussion)
        """
        formatted_text = ContentFormatter.format_telegram_markdown(opp)
        role_category = opp.get("role_category", "full_time")
        results = {}

        # 1. Publish to Channel if configured
        if target_destination in ("channel", "both") and settings.TELEGRAM_CHANNEL_ID:
            ok, msg_id, err = await cls.send_message(
                chat_id=settings.TELEGRAM_CHANNEL_ID,
                text=formatted_text
            )
            results["channel"] = {"success": ok, "message_id": msg_id, "error": err}

        # 2. Publish to Forum Topic if configured
        if target_destination in ("topic", "both") and settings.TELEGRAM_FORUM_GROUP_ID:
            topic_id = cls.resolve_topic_id(role_category)
            ok, msg_id, err = await cls.send_message(
                chat_id=settings.TELEGRAM_FORUM_GROUP_ID,
                text=formatted_text,
                message_thread_id=topic_id
            )
            results["forum_topic"] = {"success": ok, "message_id": msg_id, "topic_id": topic_id, "error": err}

        return results

    @classmethod
    async def send_admin_approval_card(
        cls,
        opp: Dict[str, Any],
        admin_chat_id: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Sends an approval card to Admin with inline buttons:
        [✅ Approve & Publish] [❌ Reject] [📋 Get WhatsApp Text]
        """
        opp_id = opp.get("id")
        company = opp.get("company", "Company")
        title = opp.get("title", "Role")
        ctc = opp.get("ctc_text", "Not disclosed")
        status = opp.get("verification_status", "unverified")

        text = (
            f"🔔 *[NEW PENDING APPROVAL]*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 *Company:* {company}\n"
            f"💼 *Role:* {title}\n"
            f"💰 *Package:* {ctc}\n"
            f"🛡️ *Verification:* `{status}`\n"
            f"🔗 *Apply:* {opp.get('apply_url')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Select an action to distribute:"
        )

        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve & Broadcast", "callback_data": f"approve_{opp_id}"},
                    {"text": "❌ Reject", "callback_data": f"reject_{opp_id}"}
                ],
                [
                    {"text": "📋 Preview WhatsApp Card", "callback_data": f"preview_wa_{opp_id}"}
                ]
            ]
        }

        return await cls.send_message(
            chat_id=admin_chat_id,
            text=text,
            reply_markup=inline_keyboard
        )

